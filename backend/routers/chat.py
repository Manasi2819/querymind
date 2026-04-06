from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.intent_classifier import classify_intent
from services.sql_agent import run_sql_query
from services.rag_service import answer_from_docs
from services.memory_service import save_turn, get_relevant_history
from services.llm_service import get_llm
from routers.admin import get_db_url, get_llm_cfg
from langchain_core.messages import HumanMessage, SystemMessage

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    question = request.message
    session_id = request.session_id

    # Override LLM config if provided in request
    llm_cfg = get_llm_cfg()
    if request.llm_config:
        llm_cfg = request.llm_config.model_dump(exclude_none=True)

    provider = llm_cfg.get("provider", "ollama")
    api_key = llm_cfg.get("api_key")

    db_url = get_db_url()
    has_db = bool(db_url)
    # Check if docs were ingested (rough check — in production, store this in DB)
    has_docs = True

    # Get relevant past turns
    history = get_relevant_history(session_id, question)

    # Classify intent
    intent = classify_intent(question, has_db, has_docs)

    try:
        if intent == "sql":
            answer = run_sql_query(question, db_url, provider, api_key)
            source = "sql"

        elif intent == "rag":
            answer = answer_from_docs(question, "default", "document", provider, api_key)
            source = "rag"

        else:
            llm = get_llm(provider=provider, api_key=api_key)
            context = f"{history}\nUser question: {question}"
            messages = [
                SystemMessage(content="You are a helpful enterprise assistant."),
                HumanMessage(content=context),
            ]
            response = llm.invoke(messages)
            answer = response.content
            source = "general"

        # Save to memory
        save_turn(session_id, "user", question)
        save_turn(session_id, "assistant", answer)

        return ChatResponse(answer=answer, source=source, session_id=session_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {"status": "ok"}
