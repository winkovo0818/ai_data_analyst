"""系统配置管理"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # LLM 配置
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_llm_provider: str = "openai"
    default_model: str = "gpt-4-turbo-preview"

    # 系统限制
    max_tool_steps: int = 8
    max_query_rows: int = 10000
    max_upload_size_mb: int = 50
    query_timeout_seconds: int = 30

    # 服务器配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # 存储路径
    upload_dir: Path = Path("./data/uploads")
    duckdb_dir: Path = Path("./data/duckdb")

    # 日志配置
    log_level: str = "INFO"
    log_file: Path = Path("./logs/app.log")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.duckdb_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
