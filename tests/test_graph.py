import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
from react_agent.graph import Graph, Node
import json

def hello_world():
    print("Hello, World!")

def good_bye():
    print("Goodbye, World!")

def hello_again():
    print("Hello again!")

async def async_hello():
    await asyncio.sleep(0.1)
    print("Hello from async function!")

def main():
    graph = Graph()
    node1 = Node(func=hello_world)
    node2 = Node(func=good_bye)
    node3 = Node(func=hello_again)
    node4 = Node(func=async_hello)
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)
    graph.add_node(node4)

    graph.add_edge("START", node1)
    graph.add_edge(from_node=node1, to_node=node2)
    graph.add_edge(from_node=node1, to_node=node3)
    graph.add_edge(from_node=node2, to_node=node4)
    graph.add_edge(from_node=node3, to_node=node4)

    print("graph adjacency list: ", json.dumps(graph.adjacency_list, indent=2))

    graph.compile()

main()