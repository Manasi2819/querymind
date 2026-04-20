"""
LLM Service — switches between Ollama (local) and cloud API providers.
The rest of the app never imports langchain LLM classes directly.
It always calls get_llm() from this module.
"""

from langchain_core.language_models import BaseChatModel
from config import get_settings

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

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=base_url or settings.ollama_base_url,
                model=model or settings.ollama_model,
                temperature=0.1,
            )
        except ImportError:
            raise ImportError("Ollama provider requires 'langchain-ollama' package. Run: pip install langchain-ollama")

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


def get_embed_model(base_url: str = None):
    """
    Returns embedding model. Always uses Ollama nomic-embed-text locally
    (free, no API key needed) unless overridden.
    """
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        base_url=base_url or settings.ollama_base_url,
        model=settings.ollama_embed_model,
    )
