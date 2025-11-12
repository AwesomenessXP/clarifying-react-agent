import functools
import inspect
import asyncio
from typing import Any, Callable

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
        self.result = result

    def __call__(self, *args, **kwargs) -> Any:
        return self.func(*args, **kwargs)

def _unwrap(func: Callable) -> Callable:
    """Unwrap the function callable to get to the original function."""
    seen = set()
    if hasattr(func, "__wrapped__") and func not in seen:
        seen.add(func)
        func = func.__wrapped__  # type: ignore[attr-defined]
    return func

def _is_async_callable(func: Callable) -> bool:
    """Check if the original function is asynchronous."""
    f = _unwrap(func)
    if inspect.iscoroutinefunction(f):
        return True
    # Handle objects with async __call__
    call = getattr(f, "__call__", None)
    return inspect.iscoroutinefunction(call)

def tool(func):
    # preserve the original function's metadata
    is_async = _is_async_callable(func)
    if is_async:
        @functools.wraps(func)
        # pass the args to the function
        async def async_wrapper(*args, **kwargs):
            try :
                result = await func(*args, **kwargs)
                return Tool(
                    func=func, 
                    name=func.__name__, 
                    description=func.__doc__, 
                    result=ToolResult(content=result)
                )
            except Exception as e:
                return Tool(
                    func=func, 
                    name=func.__name__, 
                    description=func.__doc__, 
                    result=ToolResult(content=None, error=e)
                )
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return Tool(
                    func=func, 
                    name=func.__name__, 
                    description=func.__doc__, 
                    result=ToolResult(content=result)
                )
            except Exception as e:
                return Tool(
                    func=func, 
                    name=func.__name__, 
                    description=func.__doc__, 
                    result=ToolResult(content=None, error=e)
                )
        return sync_wrapper

@tool
def hello_world(num_times):
    """
    This will print Hello, World! num_times times.
    """
    print("entering sync function")
    print("num times: ", num_times)
    hello_world_list = []
    for i in range(num_times):
        hello_world_list.append("Hello, World!")

    # This will return an error
    hello_world_list.get('hello_world')
    return hello_world_list

@tool
async def async_hello_world(num_times):
    """
    This will asynchronously print Hello, World! num_times times.
    """
    print("entering async function")
    print("num times: ", num_times)
    hello_world_list = []
    for i in range(num_times):
        await asyncio.sleep(0.1)
        hello_world_list.append("Hello, World!")
    return hello_world_list


async def wrapped_async_in_async(num_times):
    """
    This will call an async function from a sync function.
    """
    print("entering async function that calls async function")
    result = await async_hello_world(num_times)
    return result

async def main():
    hello_world_result = hello_world(num_times=2)
    print("docstring for hello_world: ", hello_world.__doc__)
    print("hello_world_result: ", hello_world_result.result.content)
    print("hello_world_result error: ", str(hello_world_result.result.error))

    async_hello_world_result = await async_hello_world(num_times=2)
    print("docstring for async_hello_world: ", async_hello_world.__doc__)
    print("async_hello_world_result: ", async_hello_world_result)

    wrapped_async_result = await wrapped_async_in_async(num_times=2)
    print("wrapped_async_result: ", wrapped_async_result)

asyncio.run(main())