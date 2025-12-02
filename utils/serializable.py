import json

def to_serializable(obj):
    # Already serializable
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    
    # Dict → convert each value
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}

    # List or tuple → convert each element
    if isinstance(obj, (list, tuple)):
        return [to_serializable(i) for i in obj]
    
    # Pydantic models
    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    # Dataclasses
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
    except:
        pass

    # Objects with __dict__
    if hasattr(obj, "__dict__"):
        return {k: to_serializable(v) for k, v in vars(obj).items()}
    
    # Fallback → string
    return str(obj)