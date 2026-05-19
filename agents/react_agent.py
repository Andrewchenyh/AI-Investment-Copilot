import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai

from agents.schemas import AgentStep, ToolObservation


class ReActAgent:
    def __init__(self, tool_registry, model_id: str = "gemini-2.5-flash", max_steps: int = 6):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    def _build_system_prompt(self, user_query: str, trace: list[dict[str, Any]]) -> str:
        tool_descriptions = self.tool_registry.describe_tools()

        return f"""
                You are an investment copilot that follows a ReAct workflow.

                Your job is to answer the user's question by deciding whether to call tools.
                You must only use the tools provided to you.
                Do not invent market data, prices, volatilities, option premiums, or dates.
                Use only numbers returned by tool observations.

                Available tools:
                {tool_descriptions}

                User query:
                {user_query}

                Previous trace:
                {json.dumps(trace, indent=2)}

                Return JSON matching this structure:
                {{
                "thought": "short explanation of why you chose this step",
                "action_type": "tool_call" or "final_answer",
                "tool_call": {{
                    "tool_name": "name of tool",
                    "tool_args": {{}}
                }},
                "final_answer": "only when action_type is final_answer"
                }}

                Rules:
                - Choose exactly one action per turn.
                - If you need more information, use a tool_call.
                - If you have enough evidence, return final_answer.
                - Final answers must be grounded in tool outputs only.
                """

    def _llm_step(self, user_query: str, trace: list[dict[str, Any]]) -> AgentStep:
        prompt = self._build_system_prompt(user_query, trace)

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AgentStep,
            },
        )

        return AgentStep.model_validate_json(response.text) # type: ignore

    def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> ToolObservation:
        try:
            result = self.tool_registry.execute(tool_name, tool_args)
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

    def ask(self, user_query: str) -> dict[str, Any]:
        trace: list[dict[str, Any]] = []

        for step_number in range(1, self.max_steps + 1):
            agent_step = self._llm_step(user_query=user_query, trace=trace)

            trace.append({
                "step": step_number,
                "thought": agent_step.thought,
                "action_type": agent_step.action_type,
            })

            if agent_step.action_type == "final_answer":
                return {
                    "status": "success",
                    "answer": agent_step.final_answer,
                    "trace": trace,
                }

            if agent_step.action_type == "tool_call":
                if agent_step.tool_call is None:
                    return {
                        "status": "error",
                        "message": "LLM returned tool_call action without tool_call payload.",
                        "trace": trace,
                    }

                observation = self._execute_tool(
                    tool_name=agent_step.tool_call.tool_name,
                    tool_args=agent_step.tool_call.tool_args,
                )

                trace.append({
                    "tool_name": observation.tool_name,
                    "tool_args": observation.tool_args,
                    "observation": observation.result,
                    "success": observation.success,
                    "error": observation.error,
                })

        return {
            "status": "error",
            "message": f"Agent exceeded max_steps={self.max_steps} without reaching a final answer.",
            "trace": trace,
        }