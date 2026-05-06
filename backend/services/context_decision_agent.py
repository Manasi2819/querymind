import re
import logging
from typing import List, Dict, Any, Tuple
from services.llm_service import get_llm
from core.logger import pipeline_logger

class ContextDecisionAgent:
    def __init__(self, provider: str = None, api_key: str = None, model: str = None, base_url: str = None):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        
        # Weights as requested: Layer1 (50%), Layer2 (35%), Layer3 (15%)
        self.weights = {
            "layer1": 0.50,
            "layer2": 0.35,
            "layer3": 0.15
        }
        self.threshold = 50

    def decide(self, current_query: str, history: List[Any], session_summary: str = "") -> Tuple[bool, float, Dict[str, float]]:
        """
        Returns (is_related, final_score, scores_per_layer)
        - is_related: True for RELATED_QUERY, False for FRESH_QUERY
        - final_score: Weighted total score
        - scores_per_layer: Breakdown for logging/debugging
        """
        if not history:
            return False, 0.0, {"layer1": 0.0, "layer2": 0.0, "layer3": 0.0}

        l1_score = self._calculate_layer1(current_query)
        l2_score = self._calculate_layer2(current_query, history)
        l3_score = self._calculate_layer3(current_query, session_summary)

        final_score = (l1_score * self.weights["layer1"]) + \
                      (l2_score * self.weights["layer2"]) + \
                      (l3_score * self.weights["layer3"])

        # Layer 1 override: If a reset phrase is detected, it MUST be a fresh query
        # regardless of other layers.
        if l1_score < 0:
            final_score = 0
            is_related = False
        else:
            is_related = final_score >= self.threshold
        
        # Logging for tracking decisions (Terminal and File)
        log_payload = {
            "query": current_query,
            "final_score": round(final_score, 2),
            "decision": "RELATED_QUERY" if is_related else "FRESH_QUERY",
            "layer_scores": {
                "l1_linguistic": l1_score,
                "l2_topic": l2_score,
                "l3_summary": l3_score
            }
        }
        
        # Concise Terminal Log via pipeline_logger
        pipeline_logger.info(
            f"Context Decision: {'[RELATED]' if is_related else '[FRESH]'} (Score: {final_score:.1f})", 
            extra={
                "stage": "CONTEXT_DECISION", 
                "payload": log_payload
            }
        )
        
        return is_related, final_score, log_payload["layer_scores"]

    def _calculate_layer1(self, query: str) -> float:
        """
        Layer 1: Linguistic Signals (Pronouns, continuation/reset phrases).
        """
        q = query.lower()
        
        # Reset phrases: These immediately force a FRESH_QUERY (indicated by negative score)
        reset_patterns = [r"\bforget that\b", r"\bnew question\b", r"\bstart over\b", r"\bclear context\b", r"\breset\b"]
        if any(re.search(p, q) for p in reset_patterns):
            return -100.0

        score = 0.0
        
        # Pronouns (Strong signal)
        pronouns = [r"\bit\b", r"\bthat\b", r"\btheir\b", r"\bhis\b", r"\bher\b", r"\bthem\b", r"\bthese\b", r"\bthose\b", r"\bits\b"]
        if any(re.search(p, q) for p in pronouns):
            score += 100.0
            
        # Continuation phrases
        continuation = [r"\bwhat about\b", r"\bhow about\b", r"\band\b", r"\balso\b", r"\bthen\b", r"\btell me more\b", r"\bnext\b"]
        if any(re.search(p, q) for p in continuation):
            score += 100.0

        # Incomplete references
        references = [r"\bthe first one\b", r"\bthe last one\b", r"\bthe previous\b", r"\babove\b", r"\bthat one\b"]
        if any(re.search(p, q) for p in references):
            score += 100.0

        return min(score, 100.0)

    def _calculate_layer2(self, query: str, history: List[Any]) -> float:
        """
        Layer 2: Topic State Tracking (Table/Column overlap).
        """
        q = query.lower()
        score = 0.0
        
        # Extract last successful SQL query to check for schema overlap
        last_sql = ""
        for msg in reversed(history):
            # Check both object attributes and dict keys for flexibility
            msg_sql = getattr(msg, 'sql', None) or (msg.get('sql') if isinstance(msg, dict) else None)
            if msg_sql:
                last_sql = msg_sql.lower()
                break
        
        if not last_sql:
            return 0.0

        # Basic regex to extract potential table and column names
        tables = re.findall(r"from\s+([\w\.]+)|join\s+([\w\.]+)", last_sql)
        tables = [t[0] or t[1] for t in tables]
        tables = [t.split('.')[-1] for t in tables] # Clean schema prefixes
        
        # Look for keywords in the query that match the previous SQL structure
        for table in tables:
            if len(table) > 3 and table in q:
                score += 50.0
        
        # Intent similarity: If user asks "any more?", "show others", etc.
        similarity_phrases = ["more", "other", "else", "difference", "compare"]
        if any(w in q for w in similarity_phrases):
            score += 30.0

        return min(score, 100.0)

    def _calculate_layer3(self, query: str, summary: str) -> float:
        """
        Layer 3: Session Summary Matching (Fallback).
        """
        if not summary:
            return 0.0
            
        q_words = set(re.findall(r"\w+", query.lower()))
        s_words = set(re.findall(r"\w+", summary.lower()))
        
        overlap = q_words.intersection(s_words)
        # Exclude common stop words
        stop_words = {"the", "a", "is", "in", "it", "of", "and", "to", "for", "with", "show", "me", "find"}
        meaningful_overlap = overlap - stop_words
        
        if len(meaningful_overlap) >= 2:
            return 70.0
        elif len(meaningful_overlap) == 1:
            return 40.0
            
        return 0.0

    def update_summary(self, history: List[Any], current_summary: str = "") -> str:
        """
        Updates the session summary based on latest turns.
        """
        if not history:
            return current_summary

        try:
            llm = get_llm(provider=self.provider, api_key=self.api_key, model=self.model, base_url=self.base_url)
            
            # Format last 2 turns for context
            hist_text = ""
            for msg in history[-4:]:
                role = getattr(msg, 'role', None) or (msg.get('role') if isinstance(msg, dict) else "unknown")
                content = getattr(msg, 'content', None) or (msg.get('content') if isinstance(msg, dict) else "")
                hist_text += f"{role.upper()}: {content}\n"

            prompt = f"""Update the conversation summary based on the new messages.
Keep it under 15 words. Focus on the core entity or topic being analyzed.

Previous Summary: {current_summary or 'None'}

Latest Messages:
{hist_text}

New Summary:"""
            
            response = llm.invoke(prompt)
            new_summary = response.content.strip().replace('"', '')
            
            pipeline_logger.info(f"Summary Updated: {new_summary}", extra={"stage": "SUMMARY_UPDATE", "payload": {"old": current_summary, "new": new_summary}})
            return new_summary
        except Exception as e:
            pipeline_logger.warning(f"Failed to update summary: {e}")
            return current_summary
