from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    database_path: Path
    ollama_num_ctx: int = 4096
    ollama_num_predict: int = 320
    ollama_num_gpu: int = 0
    ollama_keep_alive: str = "2m"
    ai_provider: str = "ollama"
    allow_lan_access: bool = False


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or ROOT_DIR / ".env", override=False)
    try:
        timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
        num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
        num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "320"))
        num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "0"))
    except ValueError as exc:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS debe ser un número entero.") from exc
    if timeout <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS debe ser mayor que cero.")
    if num_ctx <= 0 or num_predict <= 0 or num_gpu < 0:
        raise ValueError("Los límites de Ollama deben ser valores positivos válidos.")
    provider = os.getenv("AI_PROVIDER", "ollama").strip().casefold()
    if provider not in {"ollama", "hosted"}:
        raise ValueError("AI_PROVIDER debe ser ollama o hosted.")
    return Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma4:e2b").strip(),
        ollama_timeout_seconds=timeout,
        database_path=Path(os.getenv("DATABASE_PATH", str(ROOT_DIR / "data" / "triaje360.db"))),
        ollama_num_ctx=num_ctx,
        ollama_num_predict=num_predict,
        ollama_num_gpu=num_gpu,
        ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "2m").strip(),
        ai_provider=provider,
        allow_lan_access=os.getenv("ALLOW_LAN_ACCESS", "false").strip().casefold() == "true",
    )
