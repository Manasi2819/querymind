from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import ChatRequest, ChatResponse
from services.intent_classifier import classify_intent
# from services.sql_agent import run_sql_query  # Not used anymore?
from services.rag_service import answer_from_docs
from services.memory_service import save_turn, get_relevant_history
from services.llm_service import get_llm
from routers.admin import get_db_url, get_llm_cfg, get_db_type
from langchain_core.messages import HumanMessage, SystemMessage

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    question = request.message
    session_id = request.session_id
    user_id = request.user_id or 1

    # Override LLM config if provided in request
    llm_cfg = get_llm_cfg(db_session=db, user_id=user_id)
    if request.llm_config:
        llm_cfg = request.llm_config.model_dump(exclude_none=True)

    provider = llm_cfg.get("provider", "ollama")
    api_key = llm_cfg.get("api_key")

    db_url = get_db_url(db_session=db, user_id=user_id)
    db_type = get_db_type(db_session=db, user_id=user_id)
    has_db = bool(db_url)
    
    # We use f"user_{user_id}" as the tenant_id for RAG lookup
    tenant_id = f"user_{user_id}"
    has_docs = True # Rougly assumed

    # Get relevant past turns
    history = get_relevant_history(session_id, question)

    # Classify intent
    intent = classify_intent(question, has_db, has_docs)

    try:
        if intent == "sql":
            from services.sql_rag_service import run_sql_rag_pipeline
            
            answer, sql, data = run_sql_rag_pipeline(
                question, 
                tenant_id=tenant_id, 
                db_url=db_url, 
                db_type=db_type, 
                llm_provider=provider,
                history=history
            )
            source = "sql"
            save_turn(session_id, "user", question)
            save_turn(session_id, "assistant", answer)
            return ChatResponse(answer=answer, sql=sql, data=data, source=source, session_id=session_id)

        elif intent == "rag":
            answer = answer_from_docs(question, tenant_id, "document", provider, api_key, history=history)
            source = "rag"
            save_turn(session_id, "user", question)
            save_turn(session_id, "assistant", answer)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

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
            save_turn(session_id, "user", question)
            save_turn(session_id, "assistant", answer)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {"status": "ok"}
