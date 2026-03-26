# Plugin directory for custom tools.
#
# To add a custom tool, create a .py file in this directory that exports:
#   TOOL_DEF: dict — Anthropic tool schema (name, description, input_schema)
#   tool_func: callable — the function that implements the tool
#
# Example (plugins/hello.py):
#
#   TOOL_DEF = {
#       "name": "hello",
#       "description": "Say hello to someone.",
#       "input_schema": {
#           "type": "object",
#           "properties": {"name": {"type": "string"}},
#           "required": ["name"],
#       },
#   }
#
#   def tool_func(name: str) -> str:
#       return f"Hello, {name}!"
