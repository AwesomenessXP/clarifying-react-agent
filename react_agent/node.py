import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from utils.is_async_callable import _is_async_callable
from enum import Enum
from typing import Dict, List
from react_agent.message import Message

class NodeActiveStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    def __repr__(self):
        return f"NodeActiveStatus.{self.name}"

class NodeList:
    def __init__(self, nodes: List['Node'] = None):
        self.nodes = nodes or []

    def add_node(self, node: 'Node'):
        self.nodes.append(node)

    def get_nodes(self) -> List['Node']:
        return self.nodes
    
class NodeStatus(Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING" # currently executing
    SUCCESS = "SUCCESS" # finished successfully
    RETRY = "RETRY" # needs to retry
    FAILED = "FAILED" # finished with error
    TERMINATED = "TERMINATED" # terminates the graph execution

    def __repr__(self):
        return f"NodeStatus.{self.name}"

class Node:
    def __init__(self, func: Callable, max_retries: int = 15, status: NodeStatus = NodeStatus.INITIALIZED):
        self.id = str(func.__name__)
        self.callable = func
        self.max_retries = max_retries
        self.is_visited = False
        self.status = status

        if _is_async_callable(func):
            self.is_async = True
            print("Node initialized with async callable: ", func.__name__)
        else:
            self.is_async = False

    def __repr__(self):
        return f"Node(id={self.id}, callable={self.callable}, max_retries={self.max_retries}, is_visited={self.is_visited}, status={self.status})"

# Used internally in the engine 
class NodeResult:
    def __init__(self, status: NodeStatus, active_status: NodeActiveStatus, msgs: List[Message] = [], error: Exception = None):
        self.status = status
        self.active_status = active_status
        self.msgs = msgs
        self.error = error

    def __repr__(self):
        return f"NodeResult(status={self.status}, active_status={self.active_status} msgs='{self.msgs}', error={self.error})"