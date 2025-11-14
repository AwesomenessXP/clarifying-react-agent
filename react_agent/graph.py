import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from utils.is_async_callable import _is_async_callable

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
    
class Graph:
    def __init__(self):
        self.node_list = NodeList()
        self.adjacency_list = {}
        self.node_registry = {}

    def add_node(self, node: Node):
        # Ensure the node doesn't already exist
        if self.node_registry.get(node.id) is not None:
            raise ValueError(f"Node with callable {node} already exists in the node list.")
        self.node_list.add_node(node)
        self.node_registry[node.id] = node
        self.adjacency_list[node.id] = []

    def add_edge(self, from_node: Node, to_node: Node):
        # Ensure the edge doesn't already exist
        if self.adjacency_list.get(from_node.id) is not None and to_node.id in self.adjacency_list[from_node.id]:
            raise ValueError(f"Edge from {from_node.id} to {to_node.id} already exists in the adjacency list.")
        
        # Ensure the to_node exists in the registry
        if self.node_registry.get(to_node.id) is None:
            raise ValueError(f"To node {to_node.id} does not exist in the node list.")

        # Ensure the from_node exists in the registry
        if self.node_registry.get(from_node.id) is None:
            raise ValueError(f"From node {from_node.id} does not exist in the node list.")
        
        self.adjacency_list[from_node.id].append(to_node.id)

    def get_all_nodes(self) -> list[Node]:
        return self.node_list.get_nodes()
    
    def get_node_callable(self, node_id: str) -> Callable:
        if self.node_registry.get(node_id) is not None:
            return self.node_registry[node_id].callable
        raise ValueError(f"Node with id {node_id} not found in the graph.")
    
    def get_node_children(self, node_id: str) -> list[str]:
        if self.adjacency_list.get(node_id) is not None:
            return self.adjacency_list[node_id]
        raise ValueError(f"Node with id {node_id} not found in the graph.")