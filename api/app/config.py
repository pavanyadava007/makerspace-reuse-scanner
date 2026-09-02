from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://mrs:mrs@localhost:5432/mrs"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    embed_model: str = "nomic-embed-text"
    image_dir: str = "images"
    corpus_dir: str = "corpus"
    demo_dir: str = "demo"          # control.json + uploads/ (volume shared with the demo-edge container)
    models_dir: str = "models"      # built-in demo videos + onnx (host ./models, read-only)
    reports_dir: str = "reports"    # training/reports (read-only) - the only accuracy source for /api/model
    dedupe_window_s: int = 20      # same class+location seen within window since last sighting → same item
settings = Settings()
