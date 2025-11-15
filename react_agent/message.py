from typing import Any

class Message:
    def __init__(self, node_id: str, content: Any):
        """
        Initializes content: dict[str, Any]
        """
        self.content = {}
        self.content[node_id] = [content]

    def __repr__(self):
        return f"Message(content='{self.content}')"