import functools
import inspect
import asyncio
from typing import Any, Callable

def _unwrap(func: Callable) -> Callable:
    """Unwrap the function callable to get to the original function."""
    seen = set()
    while hasattr(func, "__wrapped__") and func not in seen:
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
            print("Before async function")
            result = await func(*args, **kwargs)
            try :
                return result
            finally:
                print("After async function")
        return async_wrapper
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("Before function")
        try:
            return func(*args, **kwargs)
        finally:
            print("After function")
    return wrapper

@tool
def hello_world(num_times):
    """
    This will print Hello, World! num_times times.
    """
    print("entering sync function")
    print("num times: ", num_times)
    for i in range(num_times):
        print("Hello, World!")

@tool
async def async_hello_world(num_times):
    """
    This will asynchronously print Hello, World! num_times times.
    """
    print("entering async function")
    print("num times: ", num_times)
    for i in range(num_times):
        await asyncio.sleep(0.1)
        print("Hello, World!")

async def main():
    hello_world(num_times=2)
    print("docstring for hello_world: ", hello_world.__doc__)

    await async_hello_world(num_times=2)
    print("docstring for async_hello_world: ", async_hello_world.__doc__)

asyncio.run(main())