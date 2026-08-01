import logging
from starlette.concurrency import run_in_threadpool

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from api.auth import require_api_key
from api.rate_limit import enforce_rate_limit
from api.history import get_history_items

from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CompareRequest,
    CompareResponse,
    HistoryResponse,
)
from api.service import (
    run_analysis,
    run_comparison,
    stream_analysis,
    stream_comparison,
)
from observability.logging import configure_json_logging
from observability.metrics import metrics

configure_json_logging()
logger = logging.getLogger(__name__)
app = FastAPI(
    title="AI Investment Copilot API",
    version="0.1.0",
    description="API for running the AI Investment Copilot ReAct agent.",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "AI Investment Copilot API is running."}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_json(
    request: AnalyzeRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
) -> AnalyzeResponse:
    try:
        return await run_analysis(request.query, session_id=request.session_id)
    except Exception as exc:
        logger.exception("Analysis request failed")
        raise HTTPException(
            status_code=500,
            detail="Analysis request failed.",
        ) from exc


@app.post("/analyze/stream")
async def analyze_stream(
    request: AnalyzeRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
) -> StreamingResponse:
    try:
        return StreamingResponse(
            stream_analysis(request.query, session_id=request.session_id),
            media_type="text/event-stream",
        )
    except Exception as exc:
        logger.exception("Analysis stream could not be started")
        raise HTTPException(
            status_code=500,
            detail="Analysis stream could not be started.",
        ) from exc
    

@app.post("/compare", response_model=CompareResponse)
async def compare_json(
    request: CompareRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
) -> CompareResponse:
    try:
        return await run_comparison(
            tickers=request.tickers,
            question=request.question,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.exception("Comparison request failed")
        raise HTTPException(
            status_code=500,
            detail="Comparison request failed.",
        ) from exc


@app.post("/compare/stream")
async def compare_stream(
    request: CompareRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
) -> StreamingResponse:
    try:
        return StreamingResponse(
            stream_comparison(
                tickers=request.tickers,
                question=request.question,
                session_id=request.session_id,
            ),
            media_type="text/event-stream",
        )
    except Exception as exc:
        logger.exception("Comparison stream could not be started")
        raise HTTPException(
            status_code=500,
            detail="Comparison stream could not be started.",
        ) from exc
    

@app.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    _: str = Depends(require_api_key),
) -> HistoryResponse:
    items = await run_in_threadpool(
        get_history_items,
        session_id,
    )
    return HistoryResponse(session_id=session_id, items=items) # type: ignore


@app.get("/metrics")
async def get_metrics(
    _: str = Depends(require_api_key),
) -> dict:
    return metrics.snapshot()
