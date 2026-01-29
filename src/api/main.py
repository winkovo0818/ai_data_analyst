"""FastAPI 主应用"""

import json
import shutil
from pathlib import Path
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.config import settings
from src.engines.dataset_manager import get_dataset_manager
from src.engines.llm_agent import get_llm_agent, get_streaming_llm_agent
from src.models.response import AnalysisResponse, UploadResponse, AuditInfo
from src.utils.logger import log
from src.utils.rate_limiter import get_rate_limiter


# 创建应用
app = FastAPI(
    title="AI Data Analyst",
    description="通用结构化数据分析与可视化系统",
    version="0.1.0",
    debug=settings.debug
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "openai"  # openai 或 anthropic
    api_key: str
    model: str = "gpt-4-turbo-preview"
    base_url: Optional[str] = None


class AnalysisRequest(BaseModel):
    """分析请求"""
    question: str
    dataset_id: Optional[str] = None
    llm_config: Optional[LLMConfig] = None


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AI Data Analyst",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件

    支持格式：Excel (.xlsx, .xls), CSV (.csv)
    """
    log.info(f"接收文件上传: {file.filename}")

    # 检查文件类型
    file_path = Path(file.filename)
    if file_path.suffix.lower() not in ['.xlsx', '.xls', '.csv']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_path.suffix}"
        )

    # 检查文件大小
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    max_size = settings.max_upload_size_mb * 1024 * 1024
    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制: {size} > {max_size}"
        )

    # 保存文件
    file_id = file.filename
    save_path = settings.upload_dir / file_id

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        log.info(f"文件保存成功: {save_path}")

        # 如果是 Excel，读取 sheet 列表
        sheets = None
        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            import pandas as pd
            excel_file = pd.ExcelFile(save_path)
            sheets = excel_file.sheet_names

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            size_bytes=size,
            sheets=sheets
        )

    except Exception as e:
        log.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest, req: Request):
    """
    分析数据

    Args:
        question: 用户问题
        dataset_id: 数据集ID（可选）
        llm_config: LLM 配置（可选，用于自定义 API Key 和 Model）
    """
    log.info(f"收到分析请求: {request.question}")

    # 速率限制检查
    rate_limiter = get_rate_limiter()
    client_ip = req.client.host if req.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请稍后再试。剩余配额: {rate_limiter.get_remaining(client_ip)}"
        )

    try:
        # 准备 LLM 配置
        llm_config = None
        if request.llm_config:
            llm_config = request.llm_config.model_dump()
            log.info(f"使用自定义 LLM 配置: provider={llm_config['provider']}, model={llm_config['model']}")

        # 获取 LLM Agent
        agent = get_llm_agent(llm_config)

        # 执行分析
        result = agent.run(
            user_query=request.question,
            dataset_id=request.dataset_id
        )

        # 构建响应
        return AnalysisResponse(
            answer=result.get("answer", ""),
            tables=result.get("tables", []),
            charts=result.get("charts", []),
            audit=AuditInfo(**result["trace"]),
            success=True,
            error=result.get("error")
        )

    except Exception as e:
        log.error(f"分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dataset/create")
async def create_dataset(
    file_id: str = Form(...),
    sheet: Optional[str] = Form(None),
    header_row: int = Form(1)
):
    """
    创建数据集

    Args:
        file_id: 文件ID（上传后返回）
        sheet: Excel Sheet 名称
        header_row: 表头行号
    """
    log.info(f"创建数据集: file_id={file_id}")

    try:
        dataset_manager = get_dataset_manager()
        file_path = settings.upload_dir / file_id

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        metadata = dataset_manager.create_dataset(
            file_id=file_id,
            file_path=file_path,
            original_filename=file_id,
            sheet=sheet,
            header_row=header_row
        )

        return {
            "dataset_id": metadata.dataset_id,
            "row_count": metadata.row_count,
            "column_count": metadata.column_count,
            "schema": [col.model_dump() for col in metadata.columns_schema]  # 使用新字段名
        }

    except Exception as e:
        log.error(f"创建数据集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dataset/{dataset_id}/schema")
async def get_dataset_schema(dataset_id: str):
    """获取数据集 Schema"""
    try:
        dataset_manager = get_dataset_manager()
        metadata = dataset_manager.get_schema(dataset_id)

        return {
            "dataset_id": metadata.dataset_id,
            "columns": [col.model_dump() for col in metadata.columns_schema],  # 使用新字段名
            "row_count": metadata.row_count
        }

    except Exception as e:
        log.error(f"获取 Schema 失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/analyze/stream")
async def analyze_stream(request: AnalysisRequest, req: Request):
    """
    流式分析数据 (SSE)

    返回 Server-Sent Events 流，实时推送分析进度和结果
    """
    log.info(f"收到流式分析请求: {request.question}")

    # 速率限制检查
    rate_limiter = get_rate_limiter()
    client_ip = req.client.host if req.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请稍后再试。"
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 准备 LLM 配置
            llm_config = None
            if request.llm_config:
                llm_config = request.llm_config.model_dump()

            # 获取流式 Agent
            agent = get_streaming_llm_agent(llm_config)

            # 执行流式分析
            async for event in agent.run_stream(
                user_query=request.question,
                dataset_id=request.dataset_id
            ):
                # SSE 格式: data: {json}\n\n
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            log.error(f"流式分析失败: {e}")
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    import uvicorn

    log.info(f"启动服务: {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
