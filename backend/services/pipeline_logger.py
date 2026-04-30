import logging
import logging.handlers
import json
import os
import time
import uuid
import functools
from datetime import datetime
from contextvars import ContextVar
from config import get_settings

settings = get_settings()

# ── CONTEXT VARIABLES ────────────────────────────────────────────────────────
# Used to track a unique request ID across async tasks
request_id_var: ContextVar[str] = ContextVar("request_id", default="system")

# ── DIRECTORY SETUP ──────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ── JSON FORMATTER ───────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "request_id": request_id_var.get(),
            "logger": record.name,
        }
        
        # If the message is already a dict, merge it
        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        else:
            log_record["message"] = record.getMessage()
            
        return json.dumps(log_record)

# ── LOGGER SETUP ─────────────────────────────────────────────────────────────
def setup_logger(name: str, log_file: str, level=logging.INFO):
    """Sets up a logger with both file (JSON) and console (Color/Text) handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup multiple times
    if logger.handlers:
        return logger

    # JSON File Handler
    file_path = os.path.join(LOG_DIR, log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        file_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # Console Handler (Human Readable)
    console_handler = logging.StreamHandler()
    
    # Simple color coding for console
    COLOR_STAGE = "\033[94m" # Blue
    COLOR_RESET = "\033[0m"
    
    class ConsoleFormatter(logging.Formatter):
        def format(self, record):
            ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            rid = request_id_var.get()[:8]
            
            if isinstance(record.msg, dict):
                stage = record.msg.get("stage", "MISC")
                msg = record.msg.get("message", "")
                dur = record.msg.get("duration_ms")
                dur_str = f" ({dur:.2f}ms)" if dur is not None else ""
                return f"[{ts}] [{rid}] {COLOR_STAGE}[{stage}]{COLOR_RESET} {msg}{dur_str}"
            
            return f"[{ts}] [{rid}] {record.levelname}: {record.getMessage()}"

    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)
    
    return logger

# ── LOGGERS ──────────────────────────────────────────────────────────────────
api_log = setup_logger("api", "api.log")
pipeline_log = setup_logger("pipeline", "sql_pipeline.log")
error_log = setup_logger("error", "error.log", level=logging.ERROR)

# ── LOGGING FUNCTIONS ────────────────────────────────────────────────────────

def log_api_request(method: str, path: str, status_code: int, duration_ms: float):
    api_log.info({
        "stage": "HTTP",
        "message": f"{method} {path} - {status_code}",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms
    })

def log_user_input_stage(query: str, session_id: str, user_id: str):
    pipeline_log.info({
        "stage": "USER_INPUT",
        "message": f"Query: \"{query[:50]}...\"",
        "query": query,
        "session_id": session_id,
        "user_id": user_id
    })

def log_intent_classification(intent: str, duration_ms: float):
    pipeline_log.info({
        "stage": "INTENT",
        "message": f"Intent: {intent}",
        "intent": intent,
        "duration_ms": duration_ms
    })

def log_context_decision(classification: str, use_context: bool, confidence: float, duration_ms: float, query: str = None):
    pipeline_log.info({
        "stage": "CONTEXT_AGENT",
        "message": f"Decision: {classification} (Use Context: {use_context})",
        "query": query,
        "classification": classification,
        "confidence": confidence,
        "use_context": use_context,
        "duration_ms": duration_ms
    })

def log_rag_retrieval(num_docs: int, doc_type: str, duration_ms: float):
    pipeline_log.info({
        "stage": "RETRIEVAL",
        "message": f"Found {num_docs} {doc_type} chunks",
        "doc_type": doc_type,
        "num_docs": num_docs,
        "duration_ms": duration_ms
    })

def log_table_selection(selected_tables: list, query: str, duration_ms: float):
    pipeline_log.info({
        "stage": "TABLE_SELECTION",
        "message": f"Selected tables: {', '.join(selected_tables)}",
        "query": query,
        "selected_tables": selected_tables,
        "duration_ms": duration_ms
    })

def log_query_rewrite(original: str, rewritten: str, duration_ms: float):
    pipeline_log.info({
        "stage": "REWRITE",
        "message": "Query rewritten with context",
        "original": original,
        "rewritten": rewritten,
        "duration_ms": duration_ms
    })

def log_sql_generation(sql: str, duration_ms: float):
    pipeline_log.info({
        "stage": "SQL_GEN",
        "message": "SQL query generated",
        "sql": sql,
        "duration_ms": duration_ms
    })

def log_sql_validation(status: str, reason: str = ""):
    pipeline_log.info({
        "stage": "VALIDATION",
        "message": f"Status: {status}",
        "status": status,
        "reason": reason
    })

def log_sql_validation_detailed(sql: str, status: str, errors: list = None, suggestions: dict = None):
    pipeline_log.info({
        "stage": "VALIDATION_DETAILED",
        "message": f"Validation {'PASSED' if status == 'passed' else 'FAILED'}",
        "sql": sql,
        "status": status,
        "errors": errors or [],
        "suggestions": suggestions or {}
    })

def log_sql_execution(status: str, rows_count: int = None, error: str = None, duration_ms: float = None):
    msg = f"Success: {rows_count} rows returned" if status == "success" else f"Error: {error[:100]}"
    data = {
        "stage": "DB_EXEC",
        "message": msg,
        "status": status,
        "rows_count": rows_count,
        "duration_ms": duration_ms
    }
    if error:
        data["error"] = error
        error_log.error(data)
    else:
        pipeline_log.info(data)

def log_retry_logic(attempt: int, reason: str, failed_sql: str):
    pipeline_log.warning({
        "stage": "RETRY",
        "message": f"Attempt {attempt} due to: {reason[:50]}...",
        "attempt": attempt,
        "reason": reason,
        "failed_sql": failed_sql
    })

def log_final_response(status: str, duration_ms: float):
    pipeline_log.info({
        "stage": "RESPONSE",
        "message": f"Final response sent (Status: {status})",
        "status": status,
        "duration_ms": duration_ms
    })

def log_error(event: str, message: str):
    data = {
        "stage": "ERROR",
        "event": event,
        "message": message
    }
    pipeline_log.error(data)
    error_log.error(data)

def log_pipeline_event(stage: str, message: str, **kwargs):
    """Generic pipeline event logger for cache hits, session resets, and custom stages."""
    data = {
        "stage": stage,
        "message": message,
    }
    data.update(kwargs)
    pipeline_log.info(data)

# ── TRACE DECORATOR ──────────────────────────────────────────────────────────

def log_function_trace(func):
    """Decorator to log function entry, exit, and execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        rid = request_id_var.get()
        pipeline_log.info({
            "stage": "TRACE",
            "message": f"ENTER: {func.__name__} ",
            "function": func.__name__,
            "state": "enter",
            "details": ""
        })
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            
            # Extract some result details if possible
            details = ""
            if isinstance(result, tuple) and len(result) > 0:
                if hasattr(result[0], 'shape'): # DataFrame
                    details = f"Rows: {result[0].shape[0]}"
                elif isinstance(result[0], list):
                    details = f"Count: {len(result[0])}"
                elif isinstance(result[0], int):
                    details = f"Val: {result[0]}"
            
            pipeline_log.info({
                "stage": "TRACE",
                "message": f"EXIT: {func.__name__} {details}",
                "function": func.__name__,
                "state": "exit",
                "details": details,
                "duration_ms": duration
            })
            return result
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            pipeline_log.error({
                "stage": "TRACE",
                "message": f"FAIL: {func.__name__} - {str(e)[:50]}",
                "function": func.__name__,
                "state": "fail",
                "error": str(e),
                "duration_ms": duration
            })
            raise
    return wrapper

def log_function_trace_async(func):
    """Async version of the decorator."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        pipeline_log.info({
            "stage": "TRACE",
            "message": f"ENTER: {func.__name__} ",
            "function": func.__name__,
            "state": "enter",
            "details": ""
        })
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            
            details = ""
            pipeline_log.info({
                "stage": "TRACE",
                "message": f"EXIT: {func.__name__} ",
                "function": func.__name__,
                "state": "exit",
                "details": details,
                "duration_ms": duration
            })
            return result
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            pipeline_log.error({
                "stage": "TRACE",
                "message": f"FAIL: {func.__name__} - {str(e)[:50]}",
                "function": func.__name__,
                "state": "fail",
                "error": str(e),
                "duration_ms": duration
            })
            raise
    return wrapper
