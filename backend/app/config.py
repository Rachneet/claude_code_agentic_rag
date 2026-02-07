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
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
