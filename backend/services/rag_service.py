"""
RAG service — retrieves relevant chunks from ChromaDB and generates an answer.
"""

from langchain_core.prompts import ChatPromptTemplate
from services.embed_service import get_vector_store
from services.llm_service import get_llm

def answer_from_docs(
    question: str,
    tenant_id: str,
    file_type: str = "document",
    llm_provider: str = None,
    api_key: str = None,
    history: str = "",
    model: str = None
) -> str:
    """Retrieves context from vector store and answers with LLM, considering chat history."""
    try:
        collection_name = f"{tenant_id}_{file_type}"
        store = get_vector_store(collection_name)
        retriever = store.as_retriever(search_kwargs={"k": 4})
        llm = get_llm(provider=llm_provider, api_key=api_key, model=model)

        template = """You are a helpful assistant. Use the following context and conversation history to answer the question.
        If you don't know the answer, just say you don't know. Do not make up facts.

        CONTEXT:
        {context}

        HISTORY:
        {history}

        QUESTION: {question}
        ANSWER:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # We manually retrieve context to have full control over prompt formatting
        docs = retriever.invoke(question)
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
