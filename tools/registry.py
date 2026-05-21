from typing import Any, Callable
from pydantic import BaseModel


class RegisteredTool:
    def __init__(
        self,
        name: str,
        description: str,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
        func: Callable[[BaseModel], BaseModel],
    ):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.output_model = output_model
        self.func = func

    def describe(self) -> str:
        return (
            f"Tool: {self.name}\n"
            f"Description: {self.description}\n"
            f"Input schema: {self.input_model.model_json_schema()}\n"
            f"Output schema: {self.output_model.model_json_schema()}\n"
        )


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> RegisteredTool:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool '{tool_name}'.")
        return self._tools[tool_name]

    def execute(self, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        tool = self.get_tool(tool_name)

        validated_input = tool.input_model.model_validate(tool_args)
        result = tool.func(validated_input)

        if not isinstance(result, tool.output_model):
            result = tool.output_model.model_validate(result)

        return result.model_dump()

    def describe_tools(self) -> str:
        return "\n\n".join(tool.describe() for tool in self._tools.values())

    def list_tool_names(self) -> list[str]:
        return list(self._tools.keys())