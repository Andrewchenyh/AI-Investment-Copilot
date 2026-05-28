from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from api.auth import require_api_key
from api.schemas import AnalyzeRequest, AnalyzeResponse
from api.service import run_analysis, stream_analysis
from api.rate_limit import enforce_rate_limit

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
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
        raise HTTPException(status_code=500, detail=str(exc)) from exc