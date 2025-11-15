from typing import Any

class Message:
    def __init__(self, node_id: str, content: dict):
        """
        Initializes content: dict[str, Any]
        """
        if not isinstance(content, dict):
             raise TypeError(f"Expected 'content' to be a dictionary, but received: {type(content)}")

        self.body = {
            "node_id": node_id,
            "content": content
        }

    def __repr__(self):
        return f"Message(body='{self.body}')"