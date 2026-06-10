from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    factual_grounding: int = Field(
        ...,
        ge=1,
        le=5,
        description="Whether the answer only uses facts and numbers supported by the tool trace.",
    )
    reasoning_quality: int = Field(
        ...,
        ge=1,
        le=5,
        description="Whether the conclusion follows logically from the observed metrics.",
    )
    hallucination_control: int = Field(
        ...,
        ge=1,
        le=5,
        description="Whether the answer avoids invented tickers, dates, prices, metrics, or guarantees.",
    )
    overall: int = Field(
        ...,
        ge=1,
        le=5,
        description="Overall answer quality for this query.",
    )
    rationale: str = Field(
        ...,
        description="Brief explanation of the score.",
    )
    

def build_judge_prompt(
    query: str,
    answer: str,
    trace: list[dict[str, Any]],
) -> str:
    return f"""
                You are an evaluator for an AI investment copilot.

                Your job is to judge the copilot answer using only:
                1. the user query
                2. the tool trace
                3. the final answer

                Do not use external market knowledge.
                Do not penalize the answer for not matching live market prices outside the trace.
                Only evaluate whether the answer is grounded in the provided trace.

                User query:
                {query}

                Tool trace:
                {json.dumps(trace, indent=2)}

                Final answer:
                {answer}

                Score from 1 to 5:
                - factual_grounding: 5 means every number/fact in the answer is supported by the trace; 1 means many unsupported claims.
                - reasoning_quality: 5 means the conclusion follows clearly from the metrics; 1 means the conclusion is unsupported or misleading.
                - hallucination_control: 5 means no invented ticker, date, price, premium, metric, or guarantee; 1 means clear hallucination.
                - overall: 5 means excellent, 1 means poor.

                Return concise JSON matching the requested schema.
            """
            
            
class GeminiJudge:
    def __init__(self, model_id: str = "gemini-3.1-flash-lite"):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    def score(
        self,
        query: str,
        answer: str,
        trace: list[dict[str, Any]],
    ) -> JudgeScore:
        prompt = build_judge_prompt(query=query, answer=answer, trace=trace)

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": JudgeScore,
            },
        )

        return JudgeScore.model_validate_json(response.text)