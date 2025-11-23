# Clarifying React Agent

A graph-based execution engine inspired by LangGraph for building reactive agents with conditional branching, state management, and asynchronous node execution.

## Overview

This project implements a simplified LangGraph architecture that uses a Bulk Synchronous Parallel (BSP) execution model. The engine supports:

- **Graph-based execution**: Nodes connected via edges form a directed graph
- **Conditional branching**: Router nodes enable dynamic path selection
- **State management**: Global immutable state shared across nodes
- **Asynchronous execution**: Support for both sync and async node functions
- **Message passing**: Nodes communicate via inbox messages
- **Termination handling**: Automatic graph termination when all nodes complete

## Architecture

### Core Components

- **Graph**: Main execution engine that orchestrates node execution
- **Node**: Base unit of computation that processes state and produces messages
- **ConditionalNode**: Special router node that determines execution paths based on state
- **State**: Immutable global state container
- **Message**: Communication unit between nodes
- **RunState**: Internal coordination state for BSP execution

### Execution Model

The engine follows a BSP (Bulk Synchronous Parallel) model with supersteps:

#### Iteration 0 (Initialization)
- Init node doesn't look at inbox_msgs
- Set node status to running
- Init node runs on default state
- Update status based on node result
- Pass current node state
- Pass node result to inbox_msgs
- Pass current node errors (handle errors later)
- Visit children and determine which nodes to activate in the next superstep

#### Iteration N (Subsequent Steps)
- Set node status to running
- For each node, determine if they will be inactive in this step
- Read inbox msgs sent to this node
- Pass current node results
- Pass current node's state (if terminated stop the engine, if retry, make the node active again)
- Pass any errors sent from the current node (handle errors later)
- Set a node to active/inactive based on conditional branching

#### Iteration N+1 (Convergence)
- Handle convergence (can be append-only for now)
- Previous nodes could have sent to the same message → have a unique identifier so you know who sent the message

## Implementation Progress

### ✅ Completed Features

- ✅ Create global state dict and initialize only when `invoke()` runs → each node needs a way to look at state
- ✅ Be able to make node functions and pass global state as a param
- ✅ **Branching Logic Implementation**
  - ✅ Implement router nodes, add to Graph class
  - ✅ Make node a protocol/interface so router nodes can use the same blueprint as base node
  - ✅ If the current node has a router node as a child, pass state to it and execute callable
  - ✅ Activate the node in callable result → add to internal buffer (if not init node) → add to active nodes list at barrier
  - ✅ If the current node has more than one child node → handle parallelism
  - ✅ If the current node has one child → add to internal buffer (if not init node) → add to active nodes list at barrier
- ✅ Activate next superstep's nodes
  - Visit node children
  - Call router function
  - Determine next active node from router function result
  - If no router, set all children to active
- ✅ Implement termination
  - End only if there are no active nodes left, or ALL active nodes are END
  - DO NOT end if not all nodes are END, one branch might have finished, but not the others
- ✅ Test simple loops
- ✅ Add a max recursion limit
- ✅ Save all states in a global list
- ✅ Create compile() and validate the structure of the directed graph

### ☐ TODO

- ☐ Wrap tools in ToolNode and add to_node obj to Message class for sending tool messages
- ☐ Test failure / retries
- ☐ Begin integrating OpenAI API for agent

## Usage

### Basic Example

```python
from react_agent.graph import Graph, State, START, END

# Initialize graph with initial state
initial_state = State({"query": "Hello, world!", "message": "Hiiii"})
graph = Graph(initial_state)

# Define node functions
def init_node(state: dict):
    return {"message": state["query"]}

def process_node(state: dict):
    return {"processed": state["message"].upper()}

# Add nodes
graph.add_node("init", init_node)
graph.add_node("process", process_node)

# Connect nodes
graph.add_edge(START, "init")
graph.add_edge("init", "process")
graph.add_edge("process", END)

# Execute graph
await graph.invoke()
```

### Conditional Branching Example

```python
def route_decision(state: dict) -> str:
    last_message = state.get('messages', [])[-1] if state.get('messages') else ""
    
    if "final answer" in last_message.lower():
        return "end_workflow"
    elif "call tool" in last_message.lower():
        return "tool_node"
    else:
        return "llm_node"

# Add conditional node
graph.add_conditional_node("router", route_decision)

# Map router results to nodes
graph.add_conditional_edges(
    "router",
    {
        "end_workflow": END,
        "tool_node": "run_tool_node",
        "llm_node": "call_llm_node",
    }
)
```

## Development

### Setup

```bash
# Create virtual environment
./setup_venv.sh

# Install dependencies
pip install -r requirements.txt

# Run tests
./run_test_graph.sh
```

### Testing

The project uses pytest for testing. Run tests with:

```bash
pytest
```

## Project Structure

```
clarifying-react-agent/
├── react_agent/
│   ├── __init__.py
│   ├── graph.py          # Main graph execution engine
│   ├── node.py           # Node definitions and status
│   ├── react_agent.py    # ReAct agent implementation
│   └── tool.py           # Tool definitions
├── tests/
│   ├── test_graph.py     # Graph execution tests
│   └── test_tools.py     # Tool tests
├── utils/
│   └── is_async_callable.py
├── requirements.txt
└── pytest.ini
```

## Notes

- The state dictionary is immutable and read-only to users
- Only the graph has access to methods to update state
- Each message is transformed to a dict and mapped to the state dict
- Nodes can be either synchronous or asynchronous
- The engine supports parallel execution of active nodes within a superstep
- Conditional nodes enable dynamic routing based on state analysis

