"""
RAG service — retrieves relevant chunks from ChromaDB and generates an answer.
"""

from langchain_core.prompts import ChatPromptTemplate
from services.embed_service import get_vector_store
from services.llm_service import get_llm

def answer_from_docs(
    question: str,
    tenant_id: str,
    file_type: str = "general_document",
    llm_provider: str = None,
    api_key: str = None,
    history: str = "",
    model: str = None
) -> str:
    """Retrieves context from vector store and answers with LLM, considering chat history."""
    try:
        # We search across all relevant collections to ensure nothing is missed
        collections = [
            f"{tenant_id}_{file_type}",
            f"{tenant_id}_general_document",
            f"{tenant_id}_data_dictionary",
            f"{tenant_id}_document",
            f"{tenant_id}_knowledge_base"
        ]
        
        # Deduplicate names and keep order
        collections = list(dict.fromkeys(collections))
        
        all_docs = []
        for coll_name in collections:
            try:
                store = get_vector_store(coll_name)
                # Small K per collection to stay within token limits
                all_docs.extend(store.as_retriever(search_kwargs={"k": 3}).invoke(question))
            except:
                continue

        if not all_docs:
            return "I don't have enough information to answer that based on the uploaded documents."

        # Rerank/Limit total docs (simple top 6 for now)
        docs = all_docs[:6]
        llm = get_llm(provider=llm_provider, api_key=api_key, model=model)

        template = """You are a helpful enterprise assistant. Use the following retrieved context and conversation history to answer the question.
        CRITICAL: If the answer is NOT in the context, just say you don't know. Do NOT use outside general knowledge.

        CONTEXT:
        {context}

        HISTORY:
        {history}

        QUESTION: {question}
        ANSWER:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # We manually retrieve context to have full control over prompt formatting
        context = "\n\n".join([d.page_content for d in docs])
        
        chain = prompt | llm
        result = chain.invoke({
            "context": context,
            "history": history,
            "question": question
        })
        
        return result.content if hasattr(result, 'content') else str(result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return f"RAG error: {str(e)}"
