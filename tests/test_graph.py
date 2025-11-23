import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
import asyncio
from react_agent.graph import Graph, State, START, END
from typing import Dict

# @pytest.mark.asyncio
# async def test_simple_linear_flow():
#     """Test a simple linear flow: START -> node1 -> node2 -> node3 -> node4 -> END"""
#     def node1(state: Dict):
#         print("running node1")
#         return {"step": 1, "message": "Node 1 executed"}
    
#     def node2(state: Dict):
#         print("running node2")
#         return {"step": 2, "message": "Node 2 executed"}
    
#     def node3(state: Dict):
#         print("running node3")
#         return {"step": 3, "message": "Node 3 executed"}
    
#     def node4(state: Dict):
#         print("running node4")
#         return {"step": 4, "message": "Node 4 executed"}
    
#     def node_last(state: Dict):
#         print("running node_last")
#         return {"step": 5, "message": "Node last executed"}
    
#     state = State({"step": 0, "message": "Initial state"})
#     graph = Graph(state)
    
#     # Add nodes
#     graph.add_node("node1", func=node1)
#     graph.add_node("node2", func=node2)
#     graph.add_node("node3", func=node3)
#     graph.add_node("node4", func=node4)
    
#     # Add edges
#     graph.add_edge(START, "node1")
#     graph.add_edge("node1", "node2")
#     graph.add_edge("node2", "node3")
#     graph.add_edge("node3", "node4")
#     graph.add_edge("node4", END)
    
#     # Execute graph
#     graph.compile()
#     await graph.invoke()
    
#     # Verify final state
#     assert graph.state.state["step"] == 4
#     assert graph.state.state["message"] == "Node 4 executed"
#     assert graph.run_state.step_count > 0

# @pytest.mark.asyncio
# async def test_conditional_edges():
#     """Test conditional routing based on state"""
#     def hello_world(state: Dict):
#         string = "Hello, world!"
#         return {"result": string}
    
#     def hello_again(state: Dict):
#         string = "Hello again!"
#         return {"result": string}
    
#     def good_bye(state: Dict):
#         string = "Goodbye world"
#         return {"result": string}
    
#     def router(state: Dict):
#         # Return a key to the next node based on state
#         if state["result"] == "Hello, world!":
#             return "has_result"
#         else:
#             return "no_result"
    
#     state = State({"result": "Init"})
#     graph = Graph(state)
    
#     # Add nodes
#     graph.add_node("node1", func=hello_world)
#     graph.add_node("node2", func=hello_again)
#     graph.add_node("node3", func=good_bye)
#     graph.add_conditional_node("router", func=router)
    
#     # Add edges
#     graph.add_edge(START, "node1")
#     graph.add_edge("node1", "router")
#     graph.add_conditional_edges(
#         "router",
#         {
#             "has_result": "node3",
#             "no_result": "node2"
#         }
#     )
#     graph.add_edge("node2", END)
#     graph.add_edge("node3", END)
    
#     # Execute graph
#     graph.compile()
#     await graph.invoke()
    
# #     # Verify that router correctly routed to node3 (since node1 returns "Hello, world!")
# #     # The final state should have "Goodbye world" from node3
#     assert graph.state.state["result"] == "Goodbye world"
#     assert "node3" in graph.run_state.nodes_status_map

# @pytest.mark.asyncio
# async def test_concurrent_nodes():
#     """Test that multiple nodes can be executed (concurrency simulation)"""
#     execution_order = []
    
#     def node1(state: Dict):
#         execution_order.append("node1")
#         return {"step": 1, "executed": ["node1"]}
    
#     def node2(state: Dict):
#         execution_order.append("node2")
#         return {"step": 2, "executed": ["node2"]}
    
#     async def async_node(state: Dict):
#         await asyncio.sleep(0.01)  # Simulate async work
#         execution_order.append("async_node")
#         return {"step": 3, "executed": ["async_node"]}
    
#     def node3(state: Dict):
#         execution_order.append("node3")
#         # Merge results from previous nodes
#         executed = state.get("executed", [])
#         executed.append("node3")
#         return {"step": 4, "executed": executed}
    
#     state = State({"step": 0, "executed": []})
#     graph = Graph(state)
    
#     # Add nodes
#     graph.add_node("node1", func=node1)
#     graph.add_node("node2", func=node2)
#     graph.add_node("node3", func=node3)
#     graph.add_node("async_node", func=async_node)
    
#     # Create a flow: START -> node1 -> [node2, async_node] -> node3 -> END
#     # Note: Current implementation may run serially, but we test the structure
#     graph.add_edge(START, "node1")
#     graph.add_edge("node1", "node2")
#     graph.add_edge("node1", "async_node")
#     graph.add_edge("async_node", "node3")
#     graph.add_edge("node2", "node3")
#     graph.add_edge("node3", END)
    
#     # Execute graph
#     graph.compile()
#     await graph.invoke()
    
# #     # Verify execution occurred
#     assert len(execution_order) > 0
#     assert "node1" in execution_order
# #     # Note: Due to current serial implementation, exact order may vary
# #     # This test verifies the graph structure supports multiple paths

# @pytest.mark.asyncio
# async def test_simple_loop():
#     def node_first(state: Dict):
#         print("running node_first")
#         state["step"] += 1
#         return {"step": state["step"], "message": "Node first executed"}
    
#     def router(state: Dict):
#         # Return a key to the next node based on state
#         if state["step"] < 4:
#             return "no_result"
#         else:
#             return "has_result"
    
#     def node_last(state: Dict):
#         print("running node_last")
#         return {"step": 5, "message": "Node last executed"}
    
#     state = State({"step": 0, "message": "Initial state"})
#     graph = Graph(state)
    
#     # Add nodes
#     graph.add_node("node_first", func=node_first)
#     graph.add_node("node_last", func=node_last)
#     graph.add_conditional_node("router", func=router)
    
#     # Add edges
#     graph.add_edge(START, "node_first")
#     graph.add_edge("node_first", "router")
#     graph.add_conditional_edges(
#         "router",
#         {
#             "has_result": "node_last",
#             "no_result": "node_first"
#         }
#     )
#     graph.add_edge("node_last", END)
    
#     # Execute graph
#     graph.compile()
#     await graph.invoke()
    
#     # Verify final state
#     assert graph.state.state["step"] == 5
#     assert graph.state.state["message"] == "Node last executed"
#     assert graph.run_state.step_count > 0

@pytest.mark.asyncio
async def test_simple_infinite_loop():
    def node_first(state: Dict):
        print("running node_first")
        return {"step": state["step"] + 1, "message": "Node first executed"}
    
    def router(state: Dict):
        # Return a key to the next node based on state
        if state["step"] != -1:
            return "no_result"
        else:
            return "has_result"
    
    state = State({"step": 0, "message": "Initial state"})
    graph = Graph(state)
    
    # Add nodes
    graph.add_node("node_first", func=node_first)
    
    # Add edges
    graph.add_edge(START, "node_first")
    graph.add_edge("node_first", "node_first")
    
    # Execute graph
    graph.compile()
    await graph.invoke()
    
    # Be able to stop the loop after x max loops
    assert graph.state.state["step"] == 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
