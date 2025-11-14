import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
from react_agent.graph import Graph, Node
import json

def hello_world():
    print("Hello, World!")

def good_bye():
    print("Goodbye, World!")

async def async_hello():
    await asyncio.sleep(0.1)
    print("Hello from async function!")

def main():
    graph = Graph()
    node1 = Node(func=hello_world)
    node2 = Node(func=good_bye)
    node3 = Node(func=async_hello)
    graph.add_node(node1)
    print("node1: ", node1)
    graph.add_node(node2)
    print("node2: ", node2)
    graph.add_node(node3)
    graph.add_edge(from_node=node1, to_node=node2)
    graph.add_edge(from_node=node2, to_node=node3)
    # graph.add_edge(from_node=node2, to_node=node1)  # Adding a cycle for testing

    print("graph adjacency list: ", json.dumps(graph.adjacency_list, indent=2))

    # Run the functions in the graph
    adjacency_list = graph.adjacency_list
    for from_node_id in adjacency_list:
        print(f"From node {from_node_id}:")
        node_children = graph.get_node_children(from_node_id)
        for to_node_id in node_children:
            func = graph.get_node_callable(to_node_id)
            node = graph.node_registry.get(to_node_id)
            if node.is_async:
                asyncio.run(func())
            else:
                func()

main()