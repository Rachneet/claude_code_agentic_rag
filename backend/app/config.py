from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    hf_token: str
    langsmith_api_key: str = ""
    langsmith_project: str = "rag-masterclass"
    langsmith_tracing: str = "true"

    hf_model: str = "Qwen/Qwen3-32B"

    # Provider abstraction
    llm_provider: str = "huggingface"
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_provider: str = "auto"
    hf_tool_provider: str = "cerebras"

    # Hybrid search & reranking
    reranker_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    hybrid_search_enabled: bool = True

    # Tool settings
    tavily_api_key: str = ""
    tools_web_search_enabled: bool = True
    tools_calculator_enabled: bool = True
    tools_url_fetcher_enabled: bool = True
    tools_datetime_enabled: bool = True
    url_fetcher_max_chars: int = 8000
    url_fetcher_timeout: int = 15

    # Sub-agent settings
    agents_research_enabled: bool = True
    agents_docqa_enabled: bool = True
    agents_planner_enabled: bool = True
    agent_max_iterations: int = 6
    agent_max_tokens: int = 4096

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
