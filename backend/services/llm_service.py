"""
LLM Service — switches between Ollama (local) and cloud API providers.
The rest of the app never imports langchain LLM classes directly.
It always calls get_llm() from this module.
"""

from langchain_core.language_models import BaseChatModel
from config import get_settings

settings = get_settings()

def get_llm(provider: str = None, api_key: str = None, model: str = None) -> BaseChatModel:
    """
    Returns a LangChain-compatible LLM instance.
    Priority: explicit args > env config.
    """
    provider = provider or settings.llm_provider

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=settings.ollama_base_url,
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


def get_embed_model():
    """
    Returns embedding model. Always uses Ollama nomic-embed-text locally
    (free, no API key needed) unless overridden.
    """
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embed_model,
    )
