import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
from react_agent.tool import tool
import json

class MyClass:
    def __init__(self, value: int):
        self.value = value

@tool
def hello_world(num_times: int, array: list[int] =[1,2,3]):
    """
    This will print Hello, World! num_times times.
    """
    print("entering sync function")
    print("num times: ", num_times)
    hello_world_list = []
    for i in range(num_times):
        hello_world_list.append("Hello, World!")
    return hello_world_list

@tool
async def async_hello_world(num_times: int, array: list[int] = [1,3], not_required: str = "default"):
    """
    This will asynchronously print Hello, World! num_times times.
    """
    print("entering async function")
    print("num times: ", num_times)
    hello_world_list = []
    for i in range(num_times):
        await asyncio.sleep(0.1)
        hello_world_list.append("Hello, World!")
    return hello_world_list

async def wrapped_async_in_async(num_times: int):
    """
    This will call an async function from a sync function.
    """
    print("entering async function that calls async function")
    result = await async_hello_world(num_times)
    return result

async def main():
    try:
        hello_world_result = hello_world(num_times=2)
    except Exception as e:
        print("Error calling hello_world: ", str(e))

    # async_hello_world is NOT a funtion, but a Tool instance that behaves like a function
    # - this is becausel tool_instance.__call__ is the underlying code of tool_instance()
    # - the tool instance returns a raw value, just like a normal function would!
    async_hello_world_result = await async_hello_world(num_times=2)
    print("async_hello_world_result args schema: ", json.dumps(async_hello_world.args_schema, indent=2))
    print("async_hello_world_result content: ", async_hello_world_result)

    wrapped_async_result = await wrapped_async_in_async(num_times=2)
    print("wrapped_async_result: ", wrapped_async_result)

asyncio.run(main())