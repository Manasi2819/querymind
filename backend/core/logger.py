import logging
import json
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from contextvars import ContextVar
import time

# Context variable to hold session_id across the pipeline for a single request
request_session_id: ContextVar[str] = ContextVar('request_session_id', default='unknown_session')
last_log_time: ContextVar[float] = ContextVar('last_log_time', default=0.0)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "session_id": request_session_id.get(),
            "stage": getattr(record, 'stage', 'UNKNOWN_STAGE'),
            "message": record.getMessage()
        }
        
        # Merge extra payload data if passed in the log call
        if hasattr(record, 'payload'):
            log_obj.update(record.payload)
            
        return json.dumps(log_obj)

class ConsoleFormatter(logging.Formatter):
    def format(self, record):
        stage = getattr(record, 'stage', 'UNKNOWN')
        msg = record.getMessage()
        
        # Calculate time taken since last log in this session
        current_time = time.time()
        last_time = last_log_time.get()
        
        # Reset timer on new input
        if last_time == 0.0 or stage == "USER_INPUT":
            time_str = "[0.00s]"
        else:
            time_str = f"[+{current_time - last_time:.2f}s]"
        
        last_log_time.set(current_time)
        
        # Build concise payload string
        payload_str = ""
        if hasattr(record, 'payload'):
            concise_payload = {}
            for k, v in record.payload.items():
                # Skip large text dumps for the console
                if k in ("schema_snippet", "data", "schema"):
                    continue
                if isinstance(v, str) and len(v) > 80:
                    concise_payload[k] = v[:77] + "..."
                else:
                    concise_payload[k] = v
            
            if concise_payload:
                payload_parts = [f"{k}={v}" for k, v in concise_payload.items()]
                payload_str = " | " + ", ".join(payload_parts)
                
        # Use terminal colors: Blue for time, Green for stage
        return f"\033[94m{time_str}\033[0m \033[92m[{stage}]\033[0m {msg}{payload_str}"

def setup_pipeline_logger():
    logger = logging.getLogger("sql_pipeline")
    
    # Avoid adding duplicate handlers if the logger is already initialized
    if logger.handlers:
        return logger

    # Check debug mode toggle
    debug_mode = os.getenv("DEBUG_PIPELINE", "false").lower() == "true"
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file_path = os.path.join(log_dir, "sql_pipeline.log")
    
    # File Handler: Rotates daily
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when="midnight",
        interval=1,
        backupCount=30
    )
    # The suffix isn't strictly needed if we want the current log to be `sql_pipeline.log`
    # and rotated logs to have the date suffix. `TimedRotatingFileHandler` appends %Y-%m-%d by default.
    file_handler.suffix = "%Y_%m_%d.log"
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Console Handler: Outputs to terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)
    
    # Don't propagate to the root logger to prevent duplicate logs in terminal 
    # if uvicorn/fastapi root loggers are also outputting
    logger.propagate = False
    
    return logger

pipeline_logger = setup_pipeline_logger()
