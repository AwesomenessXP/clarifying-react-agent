import functools
import inspect
from typing import Any, Callable
from typing import get_type_hints, get_origin, get_args
from typing import Union, Annotated
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.is_async_callable import _is_async_callable

PRIMITIVES = (int, float, str, bool)

class ToolResult:
    """A class representing the result of a tool execution."""
    def __init__(self, content: Any, error: Exception = None):
        self.content = content
        self.error = error

class Tool:
    """A class representing a tool with metadata."""
    def __init__(self, func: Callable, name: str = None, description: str = None, result: ToolResult = None):
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or "No description provided."
        self.result: ToolResult | None = None
        self.is_async = _is_async_callable(func)
        self.args_schema = self._build_args_schema(func)

    def __call__(self, *args, **kwargs):
        # sync tool
        if not self.is_async:
            try:
                value = self.func(*args, **kwargs)
                self.result = ToolResult(content=value)
                return value
            except Exception as e:
                self.result = ToolResult(content=None, error=e)
                raise

        # async tool
        async def runner():
            try:
                value = await self.func(*args, **kwargs)
                self.result = ToolResult(content=value)
                return value
            except Exception as e:
                self.result = ToolResult(content=None, error=e)
                raise

        return runner()

    def _resolve_base_type(self, anno):
        """
        Recursively unwraps typing constructs (Optional, Annotated, etc.)
        until we hit a 'base' type we care about.
        """
        # No annotation
        if anno is inspect._empty:
            return None

        seen = set()

        while True:
            if anno in seen:
                # cycle guard, just bail
                return anno
            seen.add(anno)

            origin = get_origin(anno)
            args = get_args(anno)

            # 1) Simple builtin primitives – stop here
            if anno in PRIMITIVES or anno in (list, dict):
                return anno

            # 2) Optional[T] / Union[T, None]
            if origin is Union and args:
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    anno = non_none[0]
                    continue
                return type(None)

            # 3) Annotated[T, ...]
            if origin is Annotated and args:
                anno = args[0]
                continue

            # 4) list[T] / dict[K, V]
            if origin in (list, dict):
                return anno  # list[int], dict[str, int], etc.

            # Anything else: no more unwrapping possible
            return anno
        
    def _build_args_schema(self,fn):
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)
        properties = {}

        for name, param in sig.parameters.items():
            if name == "self":
                continue

            prop = {}
            anno = hints.get(name, param.annotation)
            anno = self._resolve_base_type(anno)
            origin = get_origin(anno)
            args = get_args(anno)

            # 1. Simple builtins
            if anno in (int, float, str, bool):
                type_map = {int: "integer", float: "number", str: "string", bool: "boolean"}
                prop["type"] = type_map[anno]

            # 2. list[...] → JSON Schema array
            elif origin is list:
                prop["type"] = "array"
                if args:
                    item_type = args[0]
                    if item_type is str:
                        prop["items"] = {"type": "string"}
                    elif item_type is int:
                        prop["items"] = {"type": "integer"}
                    else:
                        prop["items"] = {"type": "string"}
                else:
                    prop["items"] = {"type": "string"}

            # 3. dict[...] → JSON Schema object
            elif origin is dict:
                prop["type"] = "object"
            elif isinstance(anno, type):
                raise TypeError(
                    f"\n❌ Invalid parameter type in tool `{fn.__name__}`\n"
                    f"   → Parameter `{name}` has unsupported type: `{anno.__name__}`\n\n"
                    f"   Currently, tools can only accept JSON-serializable argument types.\n\n"
                    f"   ✅ Supported types:\n\n" 
                    f"     • int\n"
                    f"     • float\n"
                    f"     • str\n"
                    f"     • bool\n"
                    f"     • list[T]\n"
                    f"     • dict[str, T]\n\n"
                    f"   ❌ Unsupported types:\n"
                    f"     • Custom classes (e.g., MyClass)\n"
                    f"     • Dataclasses or Pydantic models\n"
                    f"     • Enum values\n"
                    f"     • tuple[...] or set[...]\n"
                    f"     • Callable or function types\n"
                    f"     • list[MyClass] or dict[str, MyClass]\n\n"
                    f"   💡 Hint: Convert custom objects to JSON-compatible structures, or annotate using\n"
                    f"      supported types like `list[int]` or `dict[str, str]`.\n"
                )

            else:
                prop["type"] = "string"

            # defaults
            if param.default is not inspect._empty:
                prop["default"] = param.default

            # Get the description of the param:
            prop["description"] = self._get_arg_description(self.description, name)

            properties[name] = prop

        required = [
            name
            for name, param in sig.parameters.items()
            if name != "self" and param.default is inspect._empty
        ]

        schema = {
            "type": "function",
            "name": self.name,
            "description": self._get_main_description(self.description),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
        return schema
    
    def _get_arg_description(self, description: str, target_name: str) -> str:
        in_args = False
        for line in description.splitlines():
            stripped = line.strip()

            # Enter Args: section
            if stripped.startswith("Args:"):
                in_args = True
                continue

            if in_args:
                # End of Args section if blank line or no indent
                if not stripped:
                    break

                # Expect lines like: "num_times: The number of times..."
                if ":" in stripped:
                    name, _, rest = stripped.partition(":")
                    name = name.strip()
                    desc = rest.strip()

                    if name == target_name:
                        return desc
                    
        if in_args is False:
            raise ValueError(
                "Error: tool must have an 'Args:' section. Invalid docstring format.\n\n"
                "Expected an 'Args:' section formatted like:\n\n"
                "    This will print Hello, World! num_times times.\n\n"
                "    Args:\n"
                "        num_times: The number of times hello world will run\n"
                "        array: A list of numbers\n\n"
                "Requirements:\n"
                "  • 'Args:' must appear on its own line\n"
                "  • Each argument must be indented and follow the pattern 'name: description'\n"
                "  • No words should follow 'Args:' on the same line\n\n"
                "Please update the docstring to follow this structure."
            )
        
        raise ValueError(
            "Invalid docstring format.\n\n"
            "Expected an 'Args:' section formatted like:\n\n"
            "    This will print Hello, World! num_times times.\n\n"
            "    Args:\n"
            "        num_times: The number of times hello world will run\n"
            "        array: A list of numbers\n\n"
            "Requirements:\n"
            "  • 'Args:' must appear on its own line\n"
            "  • Each argument must be indented and follow the pattern 'name: description'\n"
            "  • No words should follow 'Args:' on the same line\n\n"
            "Please update the docstring to follow this structure."
        )
    
    def _get_main_description(self, description: str) -> str:
        lines = description.splitlines()
        collected = []

        for line in lines:
            stripped = line.strip()

            # Stop when we hit Args:
            if stripped.startswith("Args:"):
                break

            collected.append(line)

        # Join and clean up leading/trailing blank lines
        desc = "\n".join(collected).strip()

        return desc
    
    def __repr__(self):
        return f"Tool(name='{self.name}', description='{self.description}', result={self.result}, is_async={self.is_async}, args_schema={self.args_schema})"

def tool(func):
    tool_obj = Tool(func=func, name=func.__name__, description=func.__doc__)
    return tool_obj