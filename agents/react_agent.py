import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from agents.schemas import AgentStep, ToolObservation


class AgentStepValidationError(RuntimeError):
    """Raised after the model repeatedly returns an invalid AgentStep."""


class ReActAgent:
    def __init__(
        self,
        tool_registry,
        model_id: str = "gemini-3.1-flash-lite",
        max_steps: int = 10,
        max_step_validation_retries: int = 1,
    ):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        if max_step_validation_retries < 0:
            raise ValueError("max_step_validation_retries cannot be negative.")

        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.max_step_validation_retries = max_step_validation_retries

    def _build_prompt(self, user_query: str, trace: list[dict[str, Any]]) -> str:
        tool_descriptions = self.tool_registry.describe_tools()

        return f"""
                You are an investment copilot using a ReAct workflow.

                Your job is to answer the user's question by deciding whether to call tools.
                You must only use the tools provided.
                Do not invent prices, premiums, volatility values, dates, or option details.
                Use only tool observations when giving the final answer.

                Available tools:
                {tool_descriptions}

                User query:
                {user_query}

                Trace so far:
                {json.dumps(trace, indent=2)}

                Return JSON with this structure:
                {{
                "thought": "brief reason for the next step",
                "action_type": "tool_call" or "final_answer",
                "tool_call": {{
                    "tool_name": "tool name here",
                    "tool_args_json": "{{\\"ticker\\": \\"MSFT\\"}}"
                }},
                "final_answer": "only fill this when action_type is final_answer"
                }}

                Rules:
                - Choose exactly one action each turn.
                - If you still need data, choose tool_call.
                - If you have enough evidence, choose final_answer.
                - Final answers must cite the relevant observed numbers.
                - tool_args_json must be a valid JSON object encoded as a string.
                """

    def _llm_step(
        self,
        user_query: str,
        trace: list[dict[str, Any]],
        is_validation_retry: bool = False,
    ) -> AgentStep:
        prompt = self._build_prompt(user_query, trace)
        if is_validation_retry:
            prompt += """
            Your previous response failed AgentStep validation.

            Return exactly one valid action:
            - For action_type "tool_call", populate tool_call and omit final_answer.
            - For action_type "final_answer", provide a non-empty final_answer and omit tool_call.
            """

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AgentStep,
            },
        )

        return AgentStep.model_validate_json(response.text)  # type: ignore

    def _get_validated_llm_step(
        self,
        user_query: str,
        trace: list[dict[str, Any]],
    ) -> AgentStep:
        last_error: ValidationError | None = None
        total_attempts = self.max_step_validation_retries + 1

        for attempt in range(total_attempts):
            try:
                return self._llm_step(
                    user_query=user_query,
                    trace=trace,
                    is_validation_retry=attempt > 0,
                )
            except ValidationError as exc:
                last_error = exc

        raise AgentStepValidationError(
            f"The model returned an invalid AgentStep after {total_attempts} attempts."
        ) from last_error

    def _parse_tool_args(self, tool_args_json: str) -> dict[str, Any]:
        try:
            parsed = json.loads(tool_args_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"tool_args_json is not valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("tool_args_json must decode to a JSON object.")

        return parsed

    def _execute_tool(self, tool_name: str, tool_args: dict[str, Any], trace_id: str) -> ToolObservation:
        try:
            result = self.tool_registry.execute(tool_name, tool_args, trace_id)
            return ToolObservation(
                tool_name=tool_name,
                tool_args=tool_args,
                result=result,
                success=True,
            )
        except Exception as exc:
            return ToolObservation(
                tool_name=tool_name,
                tool_args=tool_args,
                result={},
                success=False,
                error=str(exc),
            )

    def ask(self, user_query: str, trace_id: str) -> dict[str, Any]:
        final_result: dict[str, Any] | None = None

        for event in self.run_with_events(user_query, trace_id=trace_id):
            if event["event"] == "final_answer":
                final_result = event["data"]
            elif event["event"] == "error":
                final_result = event["data"]

        if final_result is None:
            return {
                "status": "error",
                "trace_id": trace_id,
                "message": "Agent terminated without producing a final result.",
                "trace": [],
            }

        return final_result

    def run_with_events(self, user_query: str, trace_id: str):
        trace: list[dict[str, Any]] = []

        yield {
            "event": "start",
            "data": {
                "trace_id": trace_id,
                "query": user_query,
                "max_steps": self.max_steps,
            },
        }

        for step_number in range(1, self.max_steps + 1):
            try:
                agent_step = self._get_validated_llm_step(
                    user_query=user_query,
                    trace=trace,
                )
            except AgentStepValidationError:
                error_payload = {
                    "status": "error",
                    "trace_id": trace_id,
                    "message": (
                        "The model repeatedly returned an invalid action. "
                        "Please retry the request."
                    ),
                    "trace": trace,
                }

                yield {
                    "event": "error",
                    "data": error_payload,
                }
                return

            thought_payload = {
                "trace_id": trace_id,
                "step": step_number,
                "thought": agent_step.thought,
                "action_type": agent_step.action_type,
            }
            trace.append(thought_payload)

            yield {
                "event": "thought",
                "data": thought_payload,
            }

            if agent_step.action_type == "final_answer":
                final_answer = (agent_step.final_answer or "").strip()
                if not final_answer:
                    error_payload = {
                        "status": "error",
                        "trace_id": trace_id,
                        "message": (
                            "The agent selected a final answer but did not provide "
                            "any answer text."
                        ),
                        "trace": trace,
                    }
                    yield {
                        "event": "error",
                        "data": error_payload,
                    }
                    return

                final_payload = {
                    "status": "success",
                    "trace_id": trace_id,
                    "answer": final_answer,
                    "trace": trace,
                }
                yield {
                    "event": "final_answer",
                    "data": final_payload,
                }
                return

            if agent_step.tool_call is None:
                error_payload = {
                    "status": "error",
                    "trace_id": trace_id,
                    "message": (
                        "The agent selected a tool call but did not provide "
                        "the required tool details."
                    ),
                    "trace": trace,
                }
                yield {
                    "event": "error",
                    "data": error_payload,
                }
                return

            yield {
                "event": "tool_call",
                "data": {
                    "trace_id": trace_id,
                    "step": step_number,
                    "tool_name": agent_step.tool_call.tool_name,
                    "tool_args_json": agent_step.tool_call.tool_args_json,
                }
            }

            try:
                tool_args = self._parse_tool_args(agent_step.tool_call.tool_args_json)
            except ValueError as exc:
                error_observation = {
                    "tool_name": agent_step.tool_call.tool_name,
                    "tool_args_json": agent_step.tool_call.tool_args_json,
                    "observation": {},
                    "success": False,
                    "error": str(exc),
                }
                trace.append(error_observation)

                yield {
                    "event": "tool_result",
                    "data": error_observation,
                }
                continue

            observation = self._execute_tool(
                tool_name=agent_step.tool_call.tool_name,
                tool_args=tool_args,
                trace_id=trace_id
            )

            observation_payload = {
                "trace_id": trace_id,
                "tool_name": observation.tool_name,
                "tool_args": observation.tool_args,
                "observation": observation.result,
                "success": observation.success,
                "error": observation.error,
            }
            trace.append(observation_payload)

            yield {
                "event": "tool_result",
                "data": observation_payload,
            }

        error_payload = {
            "status": "error",
            "trace_id": trace_id,
            "message": (
                f"The agent reached the maximum of {self.max_steps} steps "
                "without producing a final answer."
            ),
            "trace": trace,
        }
        yield {
            "event": "error",
            "data": error_payload,
        }
