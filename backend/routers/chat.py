from fastapi import APIRouter, HTTPException, Depends
import re
import traceback
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import ChatRequest, ChatResponse
from services.intent_classifier import classify_intent
from services.rag_service import answer_from_docs
from models import db_models as models
from routers.admin import get_db_url, get_llm_cfg, get_db_type
from services.sql_rag_service import FORBIDDEN_SQL_KEYWORDS

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    question = request.message
    session_id = request.session_id
    user_id = request.user_id or 1

    # Pre-emptive SQL injection/modification check
    q_upper = question.upper()
    for kw in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{kw}\b", q_upper):
            answer = "I cannot do that action, I can only fetch data and show it NA."
            return ChatResponse(answer=answer, source="system", session_id=session_id)

    # Override LLM config if provided in request
    llm_cfg = get_llm_cfg(db_session=db, user_id=user_id)
    if request.llm_config:
        incoming_cfg = request.llm_config.model_dump(exclude_none=True)
        llm_cfg.update(incoming_cfg)

    provider = llm_cfg.get("provider", "ollama")
    api_key = llm_cfg.get("api_key")
    selected_model = llm_cfg.get("model")

    db_url = get_db_url(db_session=db, user_id=user_id)
    db_type = get_db_type(db_session=db, user_id=user_id)
    has_db = bool(db_url)
    
    # We use f"user_{user_id}" as the tenant_id for RAG lookup
    tenant_id = f"user_{user_id}"
    has_docs = True  # TODO: check actual ChromaDB collection presence for accuracy

    # Ensure session exists or create it
    session_title = request.session_title or "New chat"
    chat_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not chat_session:
        chat_session = models.ChatSession(id=session_id, user_id=user_id, title=session_title)
        db.add(chat_session)
        db.commit()
    elif not request.history: # If history is empty, it's a first message, update title
        chat_session.title = session_title
        db.commit()

    # Format history from the incoming request (taking last 5 messages for brevity)
    history_str = ""
    if request.history:
        recent_history = request.history[-5:]
        history_str = "Relevant conversation history:\n" + "\n".join(
            f"[{m.role}] {m.content}" for m in recent_history
        ) + "\n"

    # Classify intent using LLM or fallback
    intent = classify_intent(
        question, 
        has_db, 
        has_docs, 
        provider=provider, 
        api_key=api_key, 
        model=selected_model, 
        history=history_str
    )

    def _save_turn_db(role: str, content: str, sql: str = None, data: list = None, source: str = None):
        msg = models.ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sql=sql,
            data=data,
            source=source
        )
        db.add(msg)
        db.commit()

    try:
        if intent == "unauthorized":
            answer = "I cannot do that action, I can only fetch data and show it."
            source = "system"
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, None, None, source)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

        elif intent == "sql_with_context":
            from services.sql_rag_service import run_context_aware_sql_pipeline
            
            answer, sql, data = run_context_aware_sql_pipeline(
                question, 
                tenant_id=tenant_id, 
                db_url=db_url, 
                db_type=db_type, 
                llm_provider=provider,
                api_key=api_key,
                model=selected_model,
                history=history_str
            )
            source = "sql"
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, sql, data, source)
            return ChatResponse(answer=answer, sql=sql, data=data, source=source, session_id=session_id)

        elif intent == "rag":
            answer = answer_from_docs(question, tenant_id, "general_document", provider, api_key, history=history_str, model=selected_model)
            source = "rag"
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, None, None, source)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

        else:
            # chat intent or default fallback
            answer = "I don't have answer to that."
            source = "chat"
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, None, None, source)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

    except Exception as e:
        error_msg = str(e)
        print(traceback.format_exc())

        # User-friendly hints for common LLM errors
        if "not found" in error_msg.lower() and "model" in error_msg.lower():
            friendly_detail = f"LLM Error: The model '{selected_model}' was not found by {provider}. Please check your configuration or pull the model if using Ollama."
        elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            friendly_detail = f"LLM Error: Authentication failed for {provider}. Please check your API key."
        elif "ImportError" in error_msg or "requires" in error_msg:
            friendly_detail = f"System Error: {error_msg}"
        else:
            friendly_detail = error_msg

        raise HTTPException(status_code=500, detail=friendly_detail)

@router.get("/health")
async def health():
    return {"status": "ok"}
