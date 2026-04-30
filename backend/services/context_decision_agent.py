import re
import json
import time
from sqlalchemy.orm import Session
from models import db_models as models
from services.pipeline_logger import log_context_decision

# ── REFERENTIAL WORDS ─────────────────────────────────────────────────────────
# Expanded from old PRONOUNS set. Words that ALWAYS refer to something prior.
# If detected with an active session → definitionally a follow-up.
REFERENTIAL_WORDS = {
    # Personal pronouns
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
    "this", "that", "these", "those",
    "he", "him", "his", "she", "her", "hers",
    # Demonstrative / anaphoric references (MISSING from old code)
    "above", "aforementioned", "previous", "prior", "earlier",
    "former", "latter", "same", "said", "such",
    "following", "below",
    # Common chatbot shorthand
    "one", "ones",
}

# ── RESET PHRASES ─────────────────────────────────────────────────────────────
RESET_PHRASES = {
    "forget that", "ignore previous", "new question",
    "start over", "leave it", "different topic", "change topic",
    "new search", "stop",
}

# ── CONTINUATION PHRASES ──────────────────────────────────────────────────────
CONTINUATION_PHRASES = [
    "what about", "how about", "show more", "same for",
    "compare with", "and also", "what else", "tell me more",
    "which of", "how many of", "list those", "filter by",
    "out of these", "out of those", "from these", "from those",
    "from the above", "of the above", "among these", "among those",
    "continue", "details of that", "list them", "filter it",
]

# ── STOP WORDS ────────────────────────────────────────────────────────────────
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need",
    "me", "my", "i", "we", "our", "you", "your", "of", "in",
    "to", "for", "on", "at", "by", "with", "from", "and", "or",
    "find", "get", "fetch", "show", "list", "give", "tell",
}


def _get_list(value) -> list:
    """Safely parse a value that might be a JSON string or already a list."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def run_context_decision(session_id: str, query: str, db: Session) -> bool:
    """
    4-Part Redesigned Context Decision Agent (CDA).
    Returns True if RELATED_QUERY, False if FRESH_QUERY.

    Decision Order:
    1. Hard Reset Check        → always FRESH
    2. Hard Override 1         → Referential word + active context → always RELATED
    3. Hard Override 2         → Continuation phrase + active context → always RELATED
    4. Hard Override 3         → Very short query + active context → always RELATED
    5. Weighted Scoring (L1=30%, L2=45%, L3=25%) with dynamic threshold (55/60)
    """
    start_time = time.time()
    query_lower = query.lower().strip()
    tokens = set(re.findall(r'\w+', query_lower))
    meaningful_tokens = tokens - STOP_WORDS

    # ── HARD RESET ────────────────────────────────────────────────────────────
    if any(phrase in query_lower for phrase in RESET_PHRASES):
        duration_ms = (time.time() - start_time) * 1000
        log_context_decision("explicit_reset", False, 0.0, duration_ms, query)
        return False

    # ── Load session state ────────────────────────────────────────────────────
    session_ctx = db.query(models.SessionContext).filter(
        models.SessionContext.session_id == session_id
    ).first()

    tables_used = _get_list(session_ctx.tables_used if session_ctx else None)
    has_active_context = bool(session_ctx and len(tables_used) > 0)

    # ── HARD OVERRIDE 1: Referential word + active context ────────────────────
    # A user cannot use "them", "those", "above" without referring to something
    # prior. This is deterministic — no scoring needed.
    if has_active_context and (tokens & REFERENTIAL_WORDS):
        duration_ms = (time.time() - start_time) * 1000
        log_context_decision("hard_override_referential", True, 100.0, duration_ms, query)
        return True

    # ── HARD OVERRIDE 2: Continuation phrase + active context ─────────────────
    if has_active_context and any(phrase in query_lower for phrase in CONTINUATION_PHRASES):
        duration_ms = (time.time() - start_time) * 1000
        log_context_decision("hard_override_continuation", True, 100.0, duration_ms, query)
        return True

    # ── HARD OVERRIDE 3: Very short query with active context ─────────────────
    # 1-3 meaningful words + active session = almost always a follow-up
    # (e.g. "names?", "show all", "sort by name")
    if has_active_context and len(meaningful_tokens) <= 3:
        duration_ms = (time.time() - start_time) * 1000
        log_context_decision("hard_override_short_query", True, 100.0, duration_ms, query)
        return True

    # ── WEIGHTED SCORING (for longer, ambiguous queries) ──────────────────────
    l1_score = _score_linguistic(query_lower, tokens)
    l2_score = _score_topic_state(meaningful_tokens, session_ctx)
    l3_score = _score_summary_match(meaningful_tokens, session_ctx)

    # Weights: L1=30%, L2=45%, L3=25%
    final_score = (l1_score * 0.30) + (l2_score * 0.45) + (l3_score * 0.25)

    # Dynamic threshold:
    # Active session = 55 (lenient — we have a topic, follow-ups are likely)
    # No active session = 60 (strict — no context to fall back on)
    threshold = 55 if has_active_context else 60
    use_context = final_score >= threshold

    classification_type = "contextual_scored" if use_context else "fresh_query"
    duration_ms = (time.time() - start_time) * 1000
    log_context_decision(classification_type, use_context, final_score, duration_ms, query)
    return use_context


def _score_linguistic(query_lower: str, tokens: set) -> float:
    """Layer 1 (30%): Detect referential words, continuation phrases, and fragments."""
    if tokens & REFERENTIAL_WORDS:
        return 60.0
    if any(phrase in query_lower for phrase in CONTINUATION_PHRASES):
        return 100.0
    # Incomplete / fragmentary query (no verb — e.g. "names?", "count")
    QUERY_VERBS = {"find", "fetch", "show", "list", "give", "get", "tell", "count", "how"}
    if not (tokens & QUERY_VERBS):
        return 20.0
    return 0.0


def _score_topic_state(meaningful_tokens: set, session_ctx) -> float:
    """Layer 2 (45%): Overlap between query tokens and previous tables/columns/filters."""
    if not session_ctx:
        return 0.0
    prev_tables = set(t.lower() for t in _get_list(session_ctx.tables_used))
    prev_columns = set(c.lower() for c in _get_list(session_ctx.columns_used))
    prev_filters = set(f.lower() for f in _get_list(session_ctx.filters_used))
    all_prev = prev_tables | prev_columns | prev_filters

    if not all_prev:
        return 0.0

    overlap = meaningful_tokens & all_prev
    if not overlap:
        return 0.0

    return min(100.0, (len(overlap) / max(len(all_prev), 1)) * 100 * 3)


def _score_summary_match(meaningful_tokens: set, session_ctx) -> float:
    """Layer 3 (25%): Overlap between query tokens and the session summary."""
    if not session_ctx or not session_ctx.summary:
        return 0.0
    summary_tokens = set(re.findall(r'\w+', session_ctx.summary.lower())) - STOP_WORDS
    overlap = meaningful_tokens & summary_tokens
    if not overlap:
        return 0.0
    return min(100.0, (len(overlap) / max(len(summary_tokens), 1)) * 100 * 2)


def update_session_topic(
    session_id: str,
    db: Session,
    tables: list = None,
    columns: list = None,
    filters: list = None,
    topic: str = None,
    summary: str = None,
    intent: str = None,
):
    """Updates the SessionContext after a successful query execution."""
    context = db.query(models.SessionContext).filter(
        models.SessionContext.session_id == session_id
    ).first()

    if not context:
        context = models.SessionContext(session_id=session_id)
        db.add(context)

    if tables:
        current_tables = _get_list(context.tables_used)
        context.tables_used = list(set(current_tables + tables))[-5:]

    if columns:
        current_cols = _get_list(context.columns_used)
        context.columns_used = list(set(current_cols + columns))[-10:]

    if filters:
        current_filters = _get_list(context.filters_used)
        context.filters_used = list(set(current_filters + filters))[-5:]

    if intent:
        context.intent_type = intent

    if topic:
        context.current_topic = topic

    if summary:
        context.summary = summary

    db.commit()
