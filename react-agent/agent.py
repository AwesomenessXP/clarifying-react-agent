# Create a React Agent for handling user queries and generating responses.
from typing import Any, Dict, List

class ReActAgent:
    def __init__ (self, tools: List[Any], llm: Any, prompt_template: str):
        self.tools = tools
        self.llm = llm
        self.prompt_template = prompt_template