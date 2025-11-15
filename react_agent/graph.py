import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from react_agent.node import (
    Node, 
    NodeStatus, 
    NodeResult, 
    NodeActiveStatus
)
import asyncio
from typing import Any
from typing import Dict, List
from react_agent.message import Message
import inspect

class RunState:
    """
    Internal facing class for coordinating state between nodes
    """
    def __init__(self):
        self.step_count = 0

        # Message buffers for syncing data between nodes
        self.inbox_msgs: List[List[Message]] = []
        self.outbox_msgs: List[List[Message]] = []
        self.nodes_active_status: Dict[str, NodeStatus] = {}

class State:
    """
    User facing class for managing global state
    - the state dict must be immutable and read-only to the user
    - only the graph has access to the methods to update state
    - transform each message to a dict and map to the state dict
    """
    def __init__(self, state: Dict):
        if not isinstance(state, Dict):
            raise TypeError(f"Expected 'state' to be a dictionary, but received: {type(state)}")
        self.__state = state

    # --- Public View Properties (No Setters) ---

    @property
    def state(self) -> Dict:
        """
        Allows viewing the state, but not setting it externally.
        Updating the state creates a new instance -> don't modify the original state at all
        """
        return self.__state.copy()
    
    # TODO: add a param to either append or overwrite the data to the global state
    def _update_state(self, new_state: Dict) -> 'State':
        """
        Returns a new state instance to avoid mutating curr state
        """
        return State(new_state)
    
    def __repr__(self):
        return f"State(state='{self.state}')"
    
class Graph:
    def __init__(self, state: State):
        self.adjacency_list = {}
        self.node_registry = {}
        self.run_state = RunState()
        self.state = State(state.state)

    def add_node(self, node: Node):
        # Ensure the node doesn't already exist
        if self.node_registry.get(node.id) is not None:
            raise ValueError(f"Node with callable {node} already exists in the node list.")
        self.node_registry[node.id] = node
        self.adjacency_list[node.id] = []

    def has_state_dict(self, node: Node):
        # Ensure the to_node callable has a state dictionary parameter
        node_callable_params = inspect.signature(node.callable).parameters

        # Check if the first parameter's annotation is 'dict'
        # We access the first item in the ordered dictionary directly if we only care about the first param
        first_param = next(iter(node_callable_params.values()), None)

        if first_param is None:
            return False

        # Check if the annotation is exactly the built-in dict type
        if first_param.annotation not in (dict, Dict): # Check against both dict and typing.Dict
            return False
        
        return True

    def add_edge(self, from_node: Node | str, to_node: Node):
        if not isinstance(from_node, str) and not self.has_state_dict(from_node):
            raise TypeError(f"Node must have a state dictionary as the first param")
        
        if not self.has_state_dict(to_node):
            raise TypeError(f"Node must have a state dictionary as the first param")
        
        # Check if this is the initial edge
        if isinstance(from_node, str) and from_node == "START":
            if self.adjacency_list.get("START") is not None:
                raise ValueError(f"ERROR: another node has already been initialized!")
            self.adjacency_list["START"] = to_node.id
            return
        elif isinstance(from_node, str) and from_node != "START":
            raise ValueError(f"ERROR: string can only be 'START'")

        # Ensure the edge doesn't already exist
        if self.adjacency_list.get(from_node.id) is not None and to_node.id in self.adjacency_list[from_node.id]:
            raise ValueError(f"Edge from {from_node.id} to {to_node.id} already exists in the adjacency list.")
        
        # Ensure the to_node exists in the registry
        if self.node_registry.get(to_node.id) is None:
            raise ValueError(f"Node {to_node.id} does not exist in the node list.")

        # Ensure the from_node exists in the registry
        if self.node_registry.get(from_node.id) is None:
            raise ValueError(f"Node {from_node.id} does not exist in the node list.")
        
        self.adjacency_list[from_node.id].append(to_node.id)

    def get_node_by_id(self, node_id: str) -> Node | None:
        # Returns the actual node instance
        if self.node_registry.get(node_id) is not None:
            return self.node_registry.get(node_id)
        raise ValueError(f"Node with id {node_id} not found in the graph.")

    def get_all_nodes(self) -> list[Node]:
        nodes = []
        for node_id in self.node_registry:
            nodes.append(self.node_registry[node_id])
        return nodes
    
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
            if node.is_async:
                res = asyncio.run(func(self.state.state))
            else:
                res = func(self.state.state)
            node.status = NodeStatus.SUCCESS
            node.is_visited = True
            return NodeResult(
                status = node.status,
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
                msgs=[
                    Message(
                        node.id,
                        content = {
                            "INTERNAL_NODE_ERROR": f"{str(e)}"
                        }
                    )
                ],
                error=e
            )
        
    def update_active_status(self, node: Node) -> NodeActiveStatus:
        curr_node_status = node.status
        new_active_status = None
        match curr_node_status:
            case NodeStatus.SUCCESS | NodeStatus.TERMINATED:
                new_active_status = NodeActiveStatus.INACTIVE
            case _:
                new_active_status = NodeActiveStatus.ACTIVE
        return new_active_status

    def compile(self):
        # This is where the active node passes information about what nodes to activate in the future
        # ITERATION 0:
        # - init node doesn't look at the inbox_msgs
        # - set node status to running
        # - init node runs on default
        # - depending on node res, update status, then pass current node state
        # - pass node res to outbox_msgs
        # - pass current node errors -> handle errors later
        # - visit children and see which nodes to activate in the next superstep
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
            if self.run_state.step_count == 0:
                # find and execute the first node
                init_node_id = self.adjacency_list.get("START")
                init_node = self.get_node_by_id(init_node_id)
                self.run_state.nodes_active_status[init_node.id] = NodeActiveStatus.ACTIVE
                print("active nodes: ", self.run_state.nodes_active_status)

                print("status: ", init_node.status)
                res = self.run_node_callable(init_node)
                print("status: ", init_node.status)
                print("res: ", res)

                # update the active / inactive nodes lists based on the node result
                new_active_status = self.update_active_status(init_node)
                self.run_state.nodes_active_status[init_node.id] = new_active_status
                
                # Pass node res to global outbox_msgs buffer
                # Since only one node is active in the beginning, we can write directly to global
                self.run_state.outbox_msgs.append(res.msgs)
                print("outbox msgs: ", self.run_state.outbox_msgs)
                print("active nodes: ", self.run_state.nodes_active_status)

                new_state = self.state._update_state(res.msgs[0].body.get("content"))

                print("old state from graph: ", self.state.state)
                print("new state from graph: ", new_state.state)

                # TODO: create global state dict and initialize only when compile() runs -> each node needs a way to look at state
                # TODO: be able to make node functions and pass global state as a param
                #
                # TODO: CREATE BRANCHING LOGIC
                # 1. implement router functions, add to Graph class
                # 1.5 keep registry of router functions
                # 2. visit node children
                # 2.5 call router function
                # 3. determine next active node from router function result
                # 4. If no router, set all children to active
            
                self.run_state.step_count += 1
                continue

            break
