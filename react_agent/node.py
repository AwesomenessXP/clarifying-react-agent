import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from utils.is_async_callable import _is_async_callable
from enum import Enum
from typing import Dict, List
from react_agent.message import Message
import time

class NodeActiveStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    def __repr__(self):
        return f"NodeActiveStatus.{self.name}"
    
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
        # Get the current time in nanoseconds as an integer
        timestamp_ns = time.time_ns()
        
        # Get the function's name
        func_name = str(func.__name__)
        
        # Combine them using an f-string
        # Example format: "my_function_1701383345123456789"
        self.id = f"{func_name}_{timestamp_ns}"
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
    
class BranchNode(Node):
    """
    WHAT BRANCH NODE SHOULD DO:

    ---EXAMPLE FUNCTION DEFINITION---
        def route_decision(state):
            # Analyze the state, e.g., check the last LLM response
            last_message = state['messages'][-1]
            
            if "final answer" in last_message.lower():
                return "end_workflow" # This must match a path name
            elif "call tool" in last_message.lower():
                return "tool_node" # This must match a path name
            else:
                return "llm_node" # This must match a path name

    ---EXAMPLE CONNECTING TO GRAPH---
    builder.add_node("router", route_decision)
    # ... other nodes added ...

    builder.add_conditional_edges(
        # From the 'router' node...
        "router", 
        # Use the 'route_decision' function to decide the next path
        route_decision, 
        # Map the function's return values to actual nodes/paths
        {
            "end_workflow": END,           # Go to END if router returns "end_workflow"
            "tool_node": "run_tool_node",  # Go to run_tool_node if router returns "tool_node"
            "llm_node": "call_llm_node",   # Go to call_llm_node if router returns "llm_node"
        }
    )

    """
    pass

# Used internally in the engine 
class NodeResult:
    def __init__(self, status: NodeStatus, msgs: List[Message] = [], error: Exception = None):
        self.status = status
        self.msgs = msgs
        self.error = error

    def __repr__(self):
        return f"NodeResult(status={self.status}, msgs='{self.msgs}', error={self.error})"