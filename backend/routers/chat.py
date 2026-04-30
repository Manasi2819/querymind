from fastapi import APIRouter, HTTPException, Depends
import re
import time
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import ChatRequest, ChatResponse
from services.intent_classifier import classify_intent
from services.rag_service import answer_from_docs
from models import db_models as models
from routers.admin import get_db_url, get_llm_cfg, get_db_type
from services.sql_rag_service import FORBIDDEN_SQL_KEYWORDS
from services.redaction_service import redact_secrets
from services.context_decision_agent import run_context_decision, update_session_topic
from services.pipeline_logger import log_user_input_stage, log_intent_classification, log_final_response, log_error, log_pipeline_event

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    question = request.message
    session_id = request.session_id
    user_id = request.user_id or 1
    
    # ── 1. LOG USER INPUT ───────────────────────────────────────────────────
    log_user_input_stage(question, session_id, str(user_id))
    start_time = time.perf_counter()

    # ── 1. CACHE CHECK ──────────────────────────────────────────────────────
    # Detect if this is the first message of a new conversation.
    # is_new_chat = True means request.history is empty (user just started fresh).
    is_new_chat = not bool(request.history)

    # On a new chat: wipe the old session context and cache to prevent
    # stale data from a previous conversation leaking into the new one.
    if is_new_chat:
        db.query(models.SessionContext).filter(
            models.SessionContext.session_id == session_id
        ).delete()
        db.query(models.QueryCache).filter(
            models.QueryCache.session_id == session_id
        ).delete()
        db.commit()
        log_pipeline_event("SESSION_RESET", f"New chat detected. Wiped context and cache for session {session_id[:8]}...", session_id=session_id)

    # Check cache only for follow-up messages in an active session
    if not is_new_chat:
        cached_turn = db.query(models.QueryCache).filter(
            models.QueryCache.session_id == session_id,
            models.QueryCache.query_text == question
        ).first()

        if cached_turn:
            if (datetime.utcnow() - cached_turn.created_at.replace(tzinfo=None)).total_seconds() < 86400:
                log_pipeline_event("CACHE", f"Cache HIT for query: \"{question[:50]}...\"", session_id=session_id, cache_id=str(cached_turn.id))
                resp_data = cached_turn.response_json
                resp_data["cached"] = True
                return ChatResponse(**resp_data)

    # Pre-emptive SQL injection/modification check
    q_upper = question.upper()
    for kw in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{kw}\b", q_upper):
            answer = "I cannot do that action, I can only fetch data and show it."
            return ChatResponse(answer=answer, source="system", session_id=session_id)

    # Override LLM config if provided in request
    llm_cfg = get_llm_cfg(db_session=db, user_id=user_id)
    if request.llm_config:
        incoming_cfg = request.llm_config.model_dump(exclude_none=True)
        llm_cfg.update(incoming_cfg)

    provider = llm_cfg.get("provider", "ollama")
    api_key = llm_cfg.get("api_key")
    selected_model = llm_cfg.get("model")
    base_url = llm_cfg.get("base_url")

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

    # ── 2. CONTEXT DECISION AGENT ──────────────────────────────────────────
    is_related = run_context_decision(session_id, question, db)

    # Format history from the incoming request (taking last 5 messages for brevity)
    history_str = ""
    if request.history:
        recent_history = request.history[-5:]
        history_str = "Relevant conversation history:\n" + "\n".join(
            f"[{m.role}] {m.content}" for m in recent_history
        ) + "\n"
        
        # Explicit directive for RELATED queries as per CDA design
        if is_related:
            history_str += "\nNOTE: The new user query explicitly depends on the following conversation context. Use this context to fully understand the user's request.\n"

    # Classify intent using LLM or fallback
    intent_start = time.perf_counter()
    intent = classify_intent(
        question, 
        has_db, 
        has_docs, 
        provider=provider, 
        api_key=api_key, 
        model=selected_model, 
        base_url=base_url,
        history=history_str
    )
    log_intent_classification(intent, (time.perf_counter() - intent_start) * 1000)


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
            answer = redact_secrets(answer)
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, None, None, source)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

        elif intent == "sql_with_context":
            from services.sql_rag_service import run_context_aware_sql_pipeline
            
            answer, sql, data, metadata = run_context_aware_sql_pipeline(
                question, 
                tenant_id=tenant_id, 
                db_url=db_url, 
                db_type=db_type, 
                llm_provider=provider,
                api_key=api_key,
                model=selected_model,
                base_url=base_url,
                history=history_str,
                is_related=is_related
            )
            
            # Update Session Context with results
            if metadata:
                update_session_topic(
                    session_id=session_id,
                    db=db,
                    tables=metadata.get("tables"),
                    columns=metadata.get("columns"),
                    topic=metadata.get("topic"),
                    summary=metadata.get("summary"),
                    intent=intent
                )
            source = "sql"
            answer = redact_secrets(answer)
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, sql, data, source)
            
            # Save to cache if data is not too large (e.g., < 500 rows)
            if data and data.get("rows") and len(data["rows"]) < 500:
                resp = ChatResponse(answer=answer, sql=sql, data=data, source=source, session_id=session_id)
                new_cache = models.QueryCache(
                    session_id=session_id,
                    query_text=question,
                    response_json=resp.model_dump()
                )
                db.add(new_cache)
                db.commit()
                
            return ChatResponse(answer=answer, sql=sql, data=data, source=source, session_id=session_id)

        elif intent == "rag":
            answer = answer_from_docs(question, tenant_id, "general_document", provider, api_key, history=history_str, model=selected_model, base_url=base_url)
            source = "rag"
            answer = redact_secrets(answer)
            _save_turn_db("user", question)
            _save_turn_db("assistant", answer, None, None, source)
            return ChatResponse(answer=answer, source=source, session_id=session_id)

        else:
            # chat intent or default fallback
            answer = "I'm sorry, I can only answer questions about your connected database or uploaded documents."
            source = "chat"
            answer = redact_secrets(answer)
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
        elif "illegal header" in error_msg.lower() or "protocolerror" in error_msg.lower():
            friendly_detail = f"LLM Error: Invalid API key format for {provider}. Please ensure the key does not contain illegal characters or extra spaces."
        elif "ImportError" in error_msg or "requires" in error_msg:
            friendly_detail = f"System Error: {error_msg}"
        else:
            friendly_detail = error_msg

        # Redact secrets from error messages before raising
        friendly_detail = redact_secrets(friendly_detail)
        
        raise HTTPException(status_code=500, detail=friendly_detail)

@router.get("/health")
async def health():
    return {"status": "ok"}
