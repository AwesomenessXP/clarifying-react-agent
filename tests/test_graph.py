import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
from react_agent.graph import (Graph, State, START, END)
from react_agent.node import Node, ConditionalNode
from typing import Dict
import json

def hello_world(state: Dict):
    string = "Hello, world!"
    print(string)
    print("state in hello_world(): ", state)
    return {
        "result": string
    }

def good_bye(state: Dict):
    string = "Goodbye world"
    print(string)
    print("state in good_bye(): ", state)
    return {
        "result": string
    }

def hello_again(state: Dict):
    string = "Hello again!"
    print(string)
    print("state in hello_again(): ", state)
    return {
        "result": string
    }

async def async_hello(state: Dict):
    await asyncio.sleep(0.1)
    string = "Hello from async function!"
    print(string)
    print("state in async_hello(): ", state)
    return {
        "result": string
    }

def router(state: Dict):
    # return a key to the next node
    if state["result"] == "Hello, world!":
        return "has_result"
    else:
        return "no_result"
    
def router2(state: Dict):
    # return a key to the next node
    if state["result"] == "Hello, world!":
        return "has_result"
    else:
        return "no_result"

def main():
    state = State({
        "result": "Init"
    })
    graph = Graph(state)
    graph.add_node("node1", func=hello_world)
    graph.add_node("node2", func=hello_again)
    graph.add_node("node3", func=good_bye)
    graph.add_conditional_node("router", func=router)

    graph.add_edge(START, "node1")
    graph.add_edge("node1", "router")
    graph.add_conditional_edges(
        "router", 
        {
            "has_result": "node2",
            "no_result": "node3"
        }
    )
    graph.add_edge(from_node="node2", to_node=END)
    graph.add_edge(from_node="node3", to_node=END)
    # graph.add_edge(from_node="node3", to_node="node4")

    print("graph adjacency list: ", json.dumps(graph.adjacency_list, indent=2))

    graph.compile()

main()