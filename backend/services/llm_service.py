"""
LLM Service — switches between Ollama (local) and cloud API providers.
The rest of the app never imports langchain LLM classes directly.
It always calls get_llm() from this module.
"""

from langchain_core.language_models import BaseChatModel
from config import get_settings
import httpx
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Mapping decommissioned or retired models to their modern equivalents
RETIRED_MODELS_MAP = {
    # Groq
    "mixtral-8x7b-32768": "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile": "llama-3.3-70b-versatile",
    "llama3-70b-8192": "llama-3.3-70b-versatile",
    
    # OpenAI
    "gpt-3.5-turbo": "gpt-4o-mini",
    "gpt-3.5-turbo-0125": "gpt-4o-mini",
    
    # Anthropic
    "claude-3-haiku-20240307": "claude-3-5-haiku-20241022",
}

def detect_provider(base_url: str):
    """Auto-detect provider based on URL or response."""
    url = base_url.lower()

    # Ollama default port or no /v1 → assume native
    if "11434" in url and "/v1" not in url:
        return "ollama_native"

    # OpenAI-compatible APIs always use /v1
    if "/v1" in url:
        return "openai_compatible"

    # fallback
    return "openai_compatible"

def normalize_url(base_url: str, provider: str):
    """Ensure URL has correct suffix based on provider."""
    base_url = base_url.rstrip("/")

    if provider == "openai_compatible":
        if not base_url.endswith("/v1"):
            base_url += "/v1"

    return base_url

async def test_endpoint(base_url: str):
    """Test endpoint connectivity and return detected provider."""
    base_url = base_url.rstrip("/")
    try:
        async with httpx.AsyncClient() as client:
            # Try OpenAI-style
            try:
                r = await client.get(f"{base_url}/v1/models", timeout=2.0)
                if r.status_code == 200:
                    return "openai_compatible"
            except Exception:
                pass

            # Try Ollama native
            try:
                r = await client.get(f"{base_url}/api/tags", timeout=2.0)
                if r.status_code == 200:
                    return "ollama_native"
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Error testing endpoint: {e}")
        
    return "unknown"

def get_llm(provider: str = None, api_key: str = None, model: str = None, base_url: str = None, **kwargs) -> BaseChatModel:
    """
    Returns a LangChain-compatible LLM instance.
    Priority: explicit args > env config.
    """
    provider = provider or settings.llm_provider
    model = model or getattr(settings, f"{provider}_model", None)
    
    # Compatibility Layer: Map retired models to working alternatives
    if model in RETIRED_MODELS_MAP:
        model = RETIRED_MODELS_MAP[model]

    if provider == "endpoint" or provider == "ollama" or provider == "ollama_native" or provider == "openai_compatible":
        # Auto-detect and normalize if using custom endpoint
        if provider == "endpoint" or provider == "ollama":
            detected = detect_provider(base_url or settings.endpoint_base_url)
            base_url = normalize_url(base_url or settings.endpoint_base_url, detected)
            provider = detected

        try:
            if provider == "ollama_native":
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(
                    base_url=base_url or settings.endpoint_base_url,
                    model=model or settings.endpoint_model or "llama3.2",
                    temperature=0.1,
                )
            else: # openai_compatible
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    base_url=base_url or settings.endpoint_base_url,
                    model=model or settings.endpoint_model,
                    api_key=api_key or settings.endpoint_api_key or "sk-dummy-key",
                    temperature=0.1,
                )
        except ImportError as e:
            raise ImportError(f"Required package for {provider} not found: {e}")

    elif provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=api_key or settings.openai_api_key,
                model=model or settings.openai_model,
                temperature=0.1,
            )
        except ImportError:
            raise ImportError("OpenAI provider requires 'langchain-openai' package. Run: pip install langchain-openai")

    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                api_key=api_key or settings.anthropic_api_key,
                model_name=model or settings.anthropic_model,
                temperature=0.1,
            )
        except ImportError:
            raise ImportError("Anthropic provider requires 'langchain-anthropic' package. Run: pip install langchain-anthropic")

    elif provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                api_key=api_key or settings.gemini_api_key,
                model=model or settings.gemini_model,
                temperature=0.1,
            )
        except ImportError:
            raise ImportError("Gemini provider requires 'langchain-google-genai' package. Run: pip install langchain-google-genai")

    elif provider == "groq":
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                api_key=api_key or settings.groq_api_key,
                model_name=model or settings.groq_model,
                temperature=0.1,
            )
        except ImportError:
            raise ImportError("Groq provider requires 'langchain-groq' package. Run: pip install langchain-groq")

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ── Embeddings (Singleton) ──────────────────────────────────────────────
_cached_embed_model = None

def get_embed_model(base_url: str = None):
    """
    Returns a singleton instance of the embedding model. 
    Uses HuggingFace embeddings locally (free, no API key needed).
    Caching this prevents the model weights from reloading on every query.
    """
    global _cached_embed_model
    if _cached_embed_model is not None:
        return _cached_embed_model
        
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        import os
        if settings.hf_token:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token
            
        logger.info("Loading embedding model (all-MiniLM-L6-v2) into memory...")
        _cached_embed_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}, # Force CPU to save memory in containers
            encode_kwargs={'normalize_embeddings': True}
        )
        return _cached_embed_model
    except ImportError:
        raise ImportError("Embeddings require 'langchain-huggingface' and 'sentence-transformers'.")
