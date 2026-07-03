import os

from dotenv import load_dotenv
from fastapi import Header, HTTPException


load_dotenv()


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    expected_api_key = os.getenv("COPILOT_API_KEY")

    if not expected_api_key:
        raise HTTPException(
            status_code=500,
            detail="Server API key is not configured."
        )

    if x_api_key != expected_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key."
        )

    return x_api_key # type: ignore