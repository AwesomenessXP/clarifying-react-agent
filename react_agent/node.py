import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from utils.is_async_callable import _is_async_callable
from enum import Enum
from typing import Dict, List
import time
import abc

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

class BaseNode(abc.ABC):
    def __init__(self, id: str, func: Callable, status: NodeStatus = NodeStatus.INITIALIZED):
        self.id = id
        self.callable = func
        self.is_visited = False
        self.status = status
        self.internal_inbox_msg = None # internal message for isolating updates
        self.result = None

        if _is_async_callable(func):
            self.is_async = True
            print("Node initialized with async callable: ", func.__name__)
        else:
            self.is_async = False
    
class Node(BaseNode):
    """
    A concrete implementation of BaseNode with no additional logic needed.
    It inherits everything from BaseNode.
    """
    pass
    
class ConditionalNode(BaseNode):
    """
    Conditional Nodes are able to route to different nodes
    """
    def __repr__(self):
        return f"ConditionalNode(id: {self.id}, callable={self.callable.__name__}, status={self.status})"
    
class ToolNode(BaseNode):
    """
1. Start from what you already have

In your implementation right now, a node is basically:

“something that takes state and returns an update to state.”

So first question for you:

🧠 If you squint, is a tool actually different from any other node, or is it just a node that happens to call an external system?

If your runtime only cares about:
	•	“here’s a function that takes state, returns state-delta”

…then maybe the tool is just a particular kind of node with a convention.

⸻

2. What makes a “tool node” special?

Conceptually, a tool node usually has three extra responsibilities beyond a normal node:
	1.	Structured input
It needs to pull specific fields from the state (or messages) and map them into tool arguments.
Where in your state would you expect the tool input to live?
A messages list? A tool_request field? Something else?
	2.	Side effects / IO boundary
It crosses the boundary into the outside world (HTTP request, DB query, etc).
Does your scheduler need to know this is “special” IO,
or can it just treat it as “a node that might be slow and async”?
	3.	Structured output + logging
It needs to:
	•	Put the tool result back into the state (structured)
	•	Optionally append a “tool message” to your messages history
In your state shape, where will the tool result live?
And how will you remember which tool was called later for replay/debugging?

Once you answer those, the shape of a “tool node” almost falls out.

⸻

3. Who should know it’s a “tool node”?

Another key design question:

Should your runtime/graph engine know about “tool nodes” as a special type,
or should a tool node be just a normal node whose inner function follows a convention?

Two paths:
	•	Engine-aware:
	•	You add a kind = "tool" or similar in your node metadata.
	•	The runtime might, for example, treat it differently for tracing, retries, or timeouts.
	•	Engine-agnostic:
	•	To the engine, it’s just node(name="call_ironscales", func=...).
	•	The func internally knows it’s calling a tool and how to update state.

Which direction fits the philosophy of your engine so far?

⸻

4. Think in terms of “adapters”

A nice way to think of a tool node:

It’s an adapter between your graph state and a “tool function”.

So mentally, you could separate:
	•	A tool definition: “Given some inputs, I hit this API and return a result.”
	•	A tool node: “Given the current state, I:
	•	Extract the right inputs
	•	Call the tool
	•	Put the result back into state
	•	Log a message in messages describing what happened”

Ask yourself:

Where in your codebase do you want that adapter logic to live?
Close to the tool definition, or inside generic node wrappers?

⸻

5. Messages + tracing

You already decided you’ll have a messages list in the state.

So a key design question:

When a tool node runs, what message entries should it append?

Typical pattern conceptually:
	•	Before tool call: a message like “agent requested tool X with args Y”
	•	After tool call: a message like “tool X responded with Z”

If you solve what those messages look like, and where they go in state, you’re basically defining what it means to be a tool node in your engine.

⸻

6. Questions to answer for yourself (design spec)

If you answer these, you’ve designed your tool node:
	1.	How does a node know which tool it represents?
	2.	Where in state does it look to build the tool’s input?
	3.	How does it represent success/failure in the state after calling the tool?
	4.	What entries does it append to messages so future nodes (and you, debugging) can see the tool call happened?
	5.	Does the scheduler/runtime need to treat tool nodes differently, or are they just “slow/effectful nodes” from its point of view?

Write those answers out in English first. Once you’re happy with that conceptual contract, turning it into code will be almost mechanical.

If you want, you can tell me your current state shape (fields you already have), and I’ll ask you very targeted questions to help you “click” into one specific, clean design.
    """
    pass