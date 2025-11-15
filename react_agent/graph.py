import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from react_agent.node import Node, NodeList, _is_async_callable, NodeStatus, NodeResult, NodeActiveStatus
import asyncio
from typing import Any
from typing import Dict, List
from react_agent.message import Message

class EngineState:
    def __init__(self):
        self.step_count = 0

        # Message buffers for syncing data between nodes
        self.inbox_msgs: List[List[Message]] = []
        self.outbox_msgs: List[List[Message]] = []
        self.nodes_active_status: Dict[str, NodeStatus] = {}
    
class Graph:
    def __init__(self):
        self.node_list = NodeList()
        self.adjacency_list = {}
        self.node_registry = {}
        self.engine_state = EngineState()

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

    def get_node_by_id(self, node_id: str) -> Node | None:
        # Returns the actual node instance
        for node in self.node_list.get_nodes():
            print("node id: ", node.id)
            if str(node.id) == node_id:
                return node
        raise ValueError(f"Node with id {node_id} not found in the graph.")

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
            parent_node_id = parent_node.id
            if child_node_id in self.get_node_children(parent_node_id):
                parents_count += 1
        return parents_count
    
    def run_node_callable(self, node: Node) -> NodeResult:
        node.status = NodeStatus.RUNNING
        try:
            func = self.get_node_callable(node.id)
            if _is_async_callable(func):
                res = asyncio.run(func())
            else:
                res = func()
            node.status = NodeStatus.SUCCESS
            node.is_visited = True
            return NodeResult(
                status = node.status,
                active_status=node.status,
                msgs=[
                    Message(
                        node.id,
                        content = res
                    )
                ]
            )
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.is_visited = True
            return NodeResult(
                status = node.status,
                active_status=node.status,
                msgs=[
                    Message(
                        node.id,
                        content = f"ERROR: {str(e)}"
                    )
                ],
                error=e
            )

    
    def compile(self):
        # This is where the active node passes information about what nodes to activate in the future
        # ITERATION 0:
        # - init node doesn't look at the inbox_msgs
        # - set node status to running
        # - init node runs on default
        # - depending on node res, update status, then pass current node state
        # - pass node res to outbox_msgs
        # - pass current node errors -> handle errors later
        # 
        # ITERATION N:
        # - set node status to running
        # - for each node, determine if they will be inactive in this step or not
        # - read inbox msgs sent to this node
        # - pass current node results
        # - pass current node's state (if terminated stop the engine, if retry, make the node active again)
        # - pass any errors sent from the current node -> handle errors later
        # - TRICKY: set a node to active / inactive based on conditional branching
        # 
        # ITERATION N+1:
        # - TRICKY: handle convergence later, can be append only for now
        # - prev nodes could have sent to the same message -> have a unique identifier so you know who sent the message
        # # Get the first node
        # starting_node = self.adjacency_list.get("START")
        # if starting_node is None:
        #     return Exception(f"Unable to compile the graph")
        # starting_node_id = starting_node[0]
        # print("starting_node", starting_node_id)

        # TODO: be able to traverse nodes serially
        while True:
            # Runs the initial step
            if self.engine_state.step_count == 0:
                # find and execute the first node
                init_node_ids = self.adjacency_list.get("START")
                init_node = self.get_node_by_id(init_node_ids[0])
                self.engine_state.nodes_active_status[init_node.id] = NodeActiveStatus.ACTIVE
                print("active nodes: ", self.engine_state.nodes_active_status)

                print("status: ", init_node.status)
                res = self.run_node_callable(init_node)
                print("status: ", init_node.status)
                print("res: ", res)

                # update the active / inactive nodes lists
                node_status = init_node.status
                match node_status:
                    case NodeStatus.SUCCESS | NodeStatus.TERMINATED:
                        self.engine_state.nodes_active_status[init_node.id] = NodeActiveStatus.INACTIVE
                    case _:
                        self.engine_state.nodes_active_status[init_node.id] = NodeActiveStatus.ACTIVE
                
                # Pass node res to global outbox_msgs buffer
                # Since only one node is active in the beginning, we can write directly to global
                self.engine_state.outbox_msgs.append(res.msgs)
                print("outbox msgs: ", self.engine_state.outbox_msgs)
                print("active nodes: ", self.engine_state.nodes_active_status)
            break



