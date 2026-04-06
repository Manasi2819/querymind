"""
RAG service — retrieves relevant chunks from ChromaDB and generates an answer.
"""

from langchain.chains import RetrievalQA
from services.embed_service import get_vector_store
from services.llm_service import get_llm

def answer_from_docs(
    question: str,
    tenant_id: str,
    file_type: str = "document",
    llm_provider: str = None,
    api_key: str = None,
) -> str:
    """Retrieves context from vector store and answers with LLM."""
    try:
        collection_name = f"{tenant_id}_{file_type}"
        store = get_vector_store(collection_name)
        retriever = store.as_retriever(search_kwargs={"k": 4})
        llm = get_llm(provider=llm_provider, api_key=api_key)

        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=False,
        )
        result = chain.invoke({"query": question})
        return result.get("result", "I couldn't find an answer in the documents.")
    except Exception as e:
        return f"RAG error: {str(e)}"
