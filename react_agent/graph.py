import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from react_agent.node import Node, NodeList, _is_async_callable
import asyncio
    
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

    def add_edge(self, from_node: Node | str, to_node: Node):
        # Check if this is the initial edge
        if isinstance(from_node, str) and from_node == "START":
            if self.adjacency_list.get("START") is not None:
                raise ValueError(f"ERROR: another node has already been initialized!")
            self.adjacency_list["START"] = []
            self.adjacency_list["START"].append(to_node.id)
            return
        elif isinstance(from_node, str) and from_node != "START":
            raise ValueError(f"ERROR: string can only be 'START'")

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
    
    def get_node_parents(self, child_node_id: str) -> int:
        parents_count = 0
        # Search through parents to see if the curr node belongs to them
        for parent_node in self.get_all_nodes():
            parent_node_id = parent_node.get_id()
            if child_node_id in self.get_node_children(parent_node_id):
                parents_count += 1
        return parents_count
    
    def compile(self):
        # Get the first node
        starting_node = self.adjacency_list.get("START")
        if starting_node is None:
            return Exception(f"Unable to compile the graph")
        starting_node_id = starting_node[0]
        print("starting_node", starting_node_id)

        # FIRST RUN:

        # Run first node, then go to children
        starting_node_callable = self.get_node_callable(starting_node_id)
        print("running first node")
        starting_node_callable()

        # SECOND RUN:

        # Run the first node's children
        starting_node_children = self.get_node_children(starting_node_id)
        print("running first nodes children")
        for child_id in starting_node_children:
            func = self.get_node_callable(child_id)
            func()

        # THIRD RUN: 

        # Run the children's children
        print("running children's children")
        for child in starting_node_children:
            starting_node_children_children = self.get_node_children(child)
            for child_id in starting_node_children_children:
                func = self.get_node_callable(child_id)
                if _is_async_callable(func):
                    asyncio.run(func())
                else:
                    func()

