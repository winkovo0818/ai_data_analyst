"""启动脚本"""

import uvicorn
from src.core.config import settings
from src.utils.logger import log


if __name__ == "__main__":
    log.info("="*60)
    log.info("AI Data Analyst - 启动中")
    log.info("="*60)
    log.info(f"服务地址: http://{settings.api_host}:{settings.api_port}")
    log.info(f"API 文档: http://{settings.api_host}:{settings.api_port}/docs")
    log.info(f"调试模式: {settings.debug}")
    log.info(f"LLM 提供商: {settings.default_llm_provider}")
    log.info(f"最大步数: {settings.max_tool_steps}")
    log.info("="*60)

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
