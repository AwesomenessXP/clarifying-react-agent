import inspect
from typing import Callable

def _unwrap(func: Callable) -> Callable:
    seen = set()
    while hasattr(func, "__wrapped__") and func not in seen:
        seen.add(func)
        func = func.__wrapped__
    return func

def _is_async_callable(func: Callable) -> bool:
    """Check if the original function is asynchronous."""
    f = _unwrap(func)
    if inspect.iscoroutinefunction(f):
        return True
    # Handle objects with async __call__
    call = getattr(f, "__call__", None)
    return inspect.iscoroutinefunction(call)