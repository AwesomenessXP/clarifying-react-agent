import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Callable
from react_agent.node import (
    NodeStatus, 
    NodeActiveStatus,
    BaseNode,
    ConditionalNode,
    Node
)
import asyncio
from typing import Any
from typing import Dict, List
import inspect
import json

START = "START"
END = "END"
    
class Message:
    def __init__(self, node: BaseNode, content: dict | str):
        """
        Initializes content: dict[str, Any]
        """
        if isinstance(node, Node) and not isinstance(content, dict):
             raise TypeError(f"Expected 'content' to be a dictionary, but received: {type(content)}")
        elif isinstance(node, ConditionalNode) and not isinstance(content, str):
            raise TypeError(f"Expected 'content' to be a string, but received: {type(content)}")

        self.node = node
        self.content = content

    def __repr__(self):
        return f"Message(node='{self.node.id}, content='{self.content}')"
    
# Used internally in the engine 
class NodeResult:
    def __init__(self, status: NodeStatus, msg: Message, error: Exception = None):
        self.status = status
        self.msg = msg
        self.error = error

    def __repr__(self):
        return f"NodeResult(status={self.status}, msg='{self.msg}', error={self.error})"

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
        - be able to append / overwrite / merge to global state
        """
        return State(new_state)
    
    def __repr__(self):
        return f"State(state='{self.state}')"
    
class RunState:
    """
    Internal facing class for coordinating state between nodes
    """
    def __init__(self):
        self.step_count = 0

        # Message buffers for syncing data between nodes
        self.inbox_msgs: List[Message] = []
        self.nodes_status_map: Dict[str, NodeStatus] = {}

    def get_type(self, x):
        match x:
            case int():
                return int()
            case str():
                return str()
            case bool():
                return bool()
            case float():
                return float()
            case list():
                return list()
            case dict():
                return dict()
            case _:
                return "unknown type"
            
    def is_valid_list_type(self, content, new_item):
        return len(content) > 0 and type(content[-1]) == type(new_item)
            
    def merge_content(self, type_to_merge, new_content, key, value):
        match type_to_merge:
            case int() | str() | bool() | float() | dict():
                if type(new_content.get(key)) != list:
                    new_content[key] = [value] 
                else:
                    if not self.is_valid_list_type(new_content[key], value):
                        raise TypeError(f"Type {type(value)} unable to be merged to a list of {type(new_content[key][-1])}")
                    new_content[key].append(value)
            case list():
                if new_content.get(key) == None:
                    new_content[key] = [value]
                else:
                    if not self.is_valid_list_type(new_content[key], value):
                        raise TypeError(f"Type {type(value)} unable to be merged to a list of {type(new_content[key][-1])}")
                    new_content[key] = new_content[key] + [value]
            case _:
                raise TypeError(f"Type {type(value)} unable to be merged")
            
        return new_content[key]

    def merge_state(self, local_inbox_msgs: List[Message]) -> Dict:
        new_content = {}
        # If there is no parallelism, return early
        if len(local_inbox_msgs) == 1:
            for key, value in local_inbox_msgs[0].content.items():
                new_content[key] = value
            return new_content

        # Common case
        for msg in local_inbox_msgs:
            content = msg.content
            for key, value in content.items():
                # Ensure the types are known
                if self.get_type(value) == "unknown type":
                    raise TypeError(f"Type {type(value)} is unknown")
                
                type_to_merge = self.get_type(value)
                
                # Merge the values
                try:
                    new_content[key] = self.merge_content(
                        type_to_merge, 
                        new_content, 
                        key, 
                        value
                    )
                except Exception as e:
                    raise Exception(f"Error:", e)
        
        # Return new state
        return new_content
    
class Graph:
    def __init__(self, state: State):
        self.adjacency_list = {}
        self.node_registry = {}
        self.run_state = RunState()
        self.state = State(state.state)

    def add_node(self, custom_name: str, func: Callable):
        # Validate the node doesn't already exist
        if self.node_registry.get(custom_name) is not None:
            raise ValueError(f"Node with id {custom_name} already exists in the node list.")
        node = Node(id=custom_name,func=func)
        self.node_registry[custom_name] = node
        self.adjacency_list[custom_name] = []

    def add_conditional_node(self, custom_name: str, func: Callable):
        # Validate the node doesn't already exist
        if self.node_registry.get(custom_name) is not None:
            raise ValueError(f"Node with id {custom_name} already exists in the node list.")
        node = ConditionalNode(id=custom_name,func=func)
        self.node_registry[custom_name] = node

    def has_state_dict(self, node_id: str):
        # Validate the to_node callable has a state dictionary parameter
        node = self.node_registry.get(node_id)
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

    def add_edge(self, from_node: str, to_node: str):
        # Validate if this is the initial edge
        if from_node == START:
            if self.adjacency_list.get(START) is not None:
                raise ValueError(f"ERROR: another node has already been initialized!")
            self.adjacency_list[START] = to_node
            return
        
        # Validate the to_node exists in the registry
        if to_node != END and self.node_registry.get(to_node) is None:
            raise ValueError(f"Node {to_node} hasn't been added to the graph yet")
        
        if to_node == END:
            self.adjacency_list[from_node].append(to_node)
            return
        
        if not self.has_state_dict(to_node):
            raise TypeError(f"Node must have a state dictionary as the first param")

        # Validate the from_node exists in the registry
        if self.node_registry.get(from_node) is None:
            raise ValueError(f"Node {from_node} hasn't been added to the graph yet")

        # Validate the edge doesn't already exist
        if self.adjacency_list.get(from_node) is not None and to_node in self.adjacency_list[from_node]:
            raise ValueError(f"Edge from {from_node} to {to_node} already exists in the adjacency list.")
        
        self.adjacency_list[from_node].append(to_node)

    def add_conditional_edges(self, custom_name: str, result_map: Dict):
        if self.node_registry.get(custom_name) is None:
            raise ValueError(f"Node {custom_name} hasn't been added to the graph yet")
        
        router_node = self.node_registry.get(custom_name)

        # Check if each value in the results map is in the node registry
        for result in result_map:
            result_node_id = result_map[result]
            if not self.node_registry.get(result_node_id):
                raise ValueError(f"Node {custom_name} hasn't been added to the graph yet")
            
        # save result map to adjacency list (acts like children)
        self.adjacency_list[router_node.id] = result_map

    def get_node_by_id(self, node_id: str) -> BaseNode | None:
        # Returns the actual node instance
        if self.node_registry.get(node_id) is not None:
            return self.node_registry.get(node_id)
        raise ValueError(f"Node with id {node_id} not found in the graph.")

    def get_all_nodes(self) -> list[BaseNode]:
        nodes = []
        for node_id in self.node_registry:
            nodes.append(self.node_registry[node_id])
        return nodes
    
    def get_active_nodes(self):
        return {k: v for k, v in self.run_state.nodes_status_map.items() if v == NodeActiveStatus.ACTIVE}
    
    def get_node_callable(self, node_id: str) -> Callable:
        if self.node_registry.get(node_id) is not None:
            return self.node_registry[node_id].callable
        raise ValueError(f"Node with id {node_id} not found in the graph.")
    
    def get_node_children(self, node_id: str) -> list[str]:
        if self.adjacency_list.get(node_id) is not None:
            return self.adjacency_list[node_id]
        raise ValueError(f"Node with id {node_id} not found in the graph.")
    
    def activate_local_children_nodes(self, active_node_id: str):
        active_children = []
        children = self.adjacency_list.get(active_node_id)
        print("children of", active_node_id, ": ", children)
        if len(children) > 1:
            # If there's more than one router node, throw an error
            router_node_count = 0
            for child_id in children:
                if child_id == END:
                    children.remove(child_id)
                child_node = self.node_registry.get(child_id)
                if isinstance(child_node, ConditionalNode):
                    router_node_count += 1
                if router_node_count > 1:
                    raise Exception("ERROR: Each node can only map to one conditional router")
            active_children = children
        elif len(children) == 1:
            child_id = children[0]
            if child_id == END:
                children.remove(child_id)
                return children
            # Lookup the node in registry
            child_node = self.node_registry.get(child_id)

            # Check if the child node is a branching node or regular node
            if isinstance(child_node, ConditionalNode):
                print("router node: ", child_node)
                router_node_res = self.run_node_callable(child_node)
                # Use the adjacency list to find the node mapping of the result
                result_map = self.adjacency_list[child_node.id]
                if result_map.get(router_node_res.msg.content) is not None:
                    result_node_id = result_map.get(router_node_res.msg.content)
                    active_children.append(result_node_id)
                    print("routing to node:", result_node_id)
            elif isinstance(child_node, Node):
                active_children.append(child_id)

        return active_children
    
    def activate_shared_children_nodes(self, active_children):
        for child in active_children:
            self.run_state.nodes_status_map[child] = NodeActiveStatus.ACTIVE
    
    def get_node_parents(self, child_node_id: str) -> int:
        parents_count = 0
        # Search through parents to see if the curr node belongs to them
        for parent_node in self.get_all_nodes():
            parent_node_id = parent_node.id
            if child_node_id in self.get_node_children(parent_node_id):
                parents_count += 1
        return parents_count
    
    def run_node_callable(self, node: BaseNode) -> NodeResult:
        node.status = NodeStatus.RUNNING
        try:
            func = self.get_node_callable(node.id)
            if node.is_async:
                res = asyncio.run(func(self.state.state))
            else:
                res = func(self.state.state)

            node.status = NodeStatus.SUCCESS
            node.is_visited = True
            node_result = NodeResult(
                status = node.status,
                msg = Message(
                    node,
                    content = res
                )
            )
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.is_visited = True
            node_result = NodeResult(
                status = node.status,
                msg= Message(
                    node,
                    content = {
                        "INTERNAL_NODE_ERROR": f"{str(e)}"
                    }
                ),
                error=e
            )
        node.result = node_result
        return node_result
        
    def update_active_status(self, node: BaseNode) -> NodeActiveStatus:
        # Check if the node loops to itself
        if node.id in self.adjacency_list.get(node.id):
            return NodeActiveStatus.ACTIVE

        curr_node_status = node.status
        new_active_status = None
        match curr_node_status:
            case NodeStatus.SUCCESS | NodeStatus.TERMINATED:
                new_active_status = NodeActiveStatus.INACTIVE
            case _:
                new_active_status = NodeActiveStatus.ACTIVE
        return new_active_status
    
    def run_bsp(self, node_id):
        node = self.get_node_by_id(node_id)
        self.run_state.nodes_status_map[node_id] = NodeActiveStatus.ACTIVE
        return self.run_node_callable(node).msg

    def apply_partial_update(self, msg: Message):
        node = msg.node
        node.internal_inbox_msg = msg
        self.node_registry[node.id] = node

    async def run_bsp_async(self, active_node_ids: list[str]):
        loop = asyncio.get_running_loop()

        msgs = await asyncio.gather(*[
            loop.run_in_executor(None, self.run_bsp, node_id)
            for node_id in active_node_ids
        ])

        for msg in msgs:
            self.apply_partial_update(msg)

    async def invoke(self):
        # This is where the active node passes information about what nodes to activate in the future
        # ITERATION 0:
        # - init node doesn't look at the inbox_msgs
        # - set node status to running
        # - init node runs on default
        # - depending on node res, update status, then pass current node state
        # - pass node res to inbox_msgs
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

        # FINISHED: create global state dict and initialize only when invoke() runs -> each node needs a way to look at state
        # FINISHED: be able to make node functions and pass global state as a param
        #
        # FINISHED: CREATE BRANCHING LOGIC
        # FINISHED: 1. implement router nodes, add to Graph class
        # FINISHED: 1.1 make node a protocol / interface so router nodes can use the same blueprint as base node
        # FINISHED: 1.2 if the current node has a router node as a child, pass state to it and execute callable
        # FINISHED: 1.2 (cont) activate the node in callable res -> add to internal buffer (if not init node) -> add to active nodes list at barrier
        # FINISHED: 1.3 if the current node has more than one child node -> handle parallelism later on
        # FINISHED: 1.4 if the current node has one child -> add to internal buffer (if not init node) -> add to active nodes list at barrier

        # FINISHED: activate next superstep's nodes
        # 2. visit node children
        # 2.5 call router function
        # 3. determine next active node from router function result
        # 4. If no router, set all children to active

        # TODO: save all states in a global list
        # TODO: implement termination
        # - end only if there are no active nodes left, or ALL active nodes are END
        # - DO NOT end if not all nodes are END, one branch might have finished, but not the others
        # TODO: test simple loops
        # TODO: test infinite loops
        # TODO: test failure / retries
        # TODO: be able to detect and handle cycles, and a max recursion limit

        # TODO: be able to traverse nodes serially
        print("\n")
        while True:
            print("================================ SUPERSTEP ITERATION ", self.run_state.step_count, "===============================")
            # Runs the initial step
            if self.run_state.step_count == 0:
                # BEGINNING OF INIT NODE CONDITION
                init_node_id = self.adjacency_list.get(START)
                print("adjacency list: ", json.dumps(self.adjacency_list, indent = 2))
                init_node = self.get_node_by_id(init_node_id)
                self.run_state.nodes_status_map[init_node_id] = NodeActiveStatus.ACTIVE
                print("node statuses: ", self.run_state.nodes_status_map)

                print("status: ", init_node.status)
                res = self.run_node_callable(init_node)
                print("status: ", init_node.status)
                print("res: ", res)

                # ------ BARRIER --------------------

                # update the active / inactive nodes lists based on the node result
                new_active_status = self.update_active_status(init_node)
                self.run_state.nodes_status_map[init_node.id] = new_active_status
                
                # Pass node res to global inbox_msgs buffer
                # Since only one node is active in the beginning, we can write directly to global
                self.run_state.inbox_msgs.append(res.msg)
                print("inbox msgs: ", self.run_state.inbox_msgs)
                print("node statuses: ", self.run_state.nodes_status_map)

                # Update the global state
                print("old state from graph: ", self.state.state)
                print("result: ", res)
                new_state = self.state._update_state(res.msg.content)
                self.state = new_state
                print("new state from graph: ", new_state.state)

                # Get the children of the init node
                active_children = self.activate_local_children_nodes(init_node_id)

                # Activate the child nodes globally for the next superstep
                self.activate_shared_children_nodes(active_children)

                # END OF INIT NODE CONDITION
            else:
                # START OF N+1 SUPERSTEP
                # read which nodes are active in this round
                active_nodes = self.get_active_nodes()

                print("active nodes: ", active_nodes)

                # Process each active node (not in parallel yet)
                await self.run_bsp_async(active_nodes)

                # ------ BARRIER --------------------

                # superstep-local bucket for messages
                local_inbox_msgs = []

                # update the global active / inactive nodes lists based on the node result
                # NOTE: check from the node_registry for the updated nodes!
                for active_node_id in active_nodes:
                    print("node", active_node_id)
                    node = self.get_node_by_id(active_node_id)
                    new_active_status = self.update_active_status(node)
                    self.run_state.nodes_status_map[node.id] = new_active_status
                
                    # Pass node results to local inbox_msgs buffer
                    local_inbox_msgs.append(node.result.msg)
                    print("node result: ", node.result.msg.content)
                
                print("global inbox msgs: ", self.run_state.inbox_msgs)
                print("local inbox msgs: ", local_inbox_msgs)
                print("node statuses: ", self.run_state.nodes_status_map)

                # Use a merging strategy to append to global inbox
                # TODO: in the future, allow users to pick a merging strategy (append, overwrite, keep first)
                print("old state from graph: ", self.state.state)
                new_content = self.run_state.merge_state(local_inbox_msgs)
                new_state = self.state._update_state(new_content)
                self.state = new_state
                print("new state from graph: ", self.state.state)

                # Get the children of the active nodes and determine which to activate
                active_children = []

                for active_node_id in active_nodes:
                    active_children = self.activate_local_children_nodes(active_node_id)
                    # Deduplicate children if multiple nodes activate the same ones
                    for child in active_children:
                        if child not in active_children: 
                            active_children.append(child)

                # Activate the child nodes globally for the next superstep
                self.activate_shared_children_nodes(active_children)

            if len(self.get_active_nodes()) == 0:
                print("ending the loop, no active nodes left")
                break

            # Temporary: end the loop after 5 iterations
            # if self.run_state.step_count == 5:
            #     break
            
            self.run_state.step_count += 1
            print("\n")
