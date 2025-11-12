import functools

def tool(func):
    # preserve the original function's metadata
    @functools.wraps(func)
    # pass the args to the function
    def wrapper(*args, **kwargs):
        print("Before function")
        result = func(*args, **kwargs)
        print("After function")
        return result
    return wrapper

@tool
def hello_world(num_times):
    """
    This will print Hello, World! num_times times.
    """
    print("num times: ", num_times)
    for i in range(num_times):
        print("Hello, World!")

if __name__ == "__main__":
    hello_world(num_times=2)
    print("docstring for hello_world: ", hello_world.__doc__)