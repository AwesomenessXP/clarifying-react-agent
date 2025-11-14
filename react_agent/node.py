import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from utils.is_async_callable import _is_async_callable
from enum import Enum
from typing import Any
from typing import Dict, List

class NodeList:
    def __init__(self, nodes: list['Node'] = None):
        self.nodes = nodes or []

    def add_node(self, node: 'Node'):
        self.nodes.append(node)

    def get_nodes(self) -> list['Node']:
        return self.nodes

class Node:
    def __init__(self, func: Callable, max_retries: int = 15):
        self.id = str(func.__name__)
        self.callable = func
        self.max_retries = max_retries

        if _is_async_callable(func):
            self.is_async = True
            print("Node initialized with async callable: ", func.__name__)
        else:
            self.is_async = False

    def get_id(self) -> str:
        return self.id
    
class NodeStatus(Enum):
    ACTIVE = "ACTIVE" # active, but not running
    INACTIVE = "INACTIVE" # inactive
    RUNNING = "RUNNING" # currently executing
    SUCCESS = "SUCCESS" # finished successfully
    RETRY = "RETRY" # needs to retry
    FAILED = "FAILED" # finished with error
    TERMINATED = "TERMINATED" # terminates the graph execution

# Used internally in the engine 
class NodeResult:
    def __init__(self, status: NodeStatus, messages: List | None = None, error: Exception = None):
        self.status = status
        self.messages = messages or []
        self.error = error