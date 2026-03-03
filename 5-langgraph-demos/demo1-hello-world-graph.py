# first define state. The state is basically an object which is passed between th nodes
# and edges of the graph.

from typing import TypedDict, Literal
import random
from langgraph.graph import StateGraph, START, END

# First define the state which will be passed between the nodes and edges of the graph. 
# The state is basically a dictionary which can hold any information that the nodes and edges need to access and modify. 
# In this example, we will just have a simple state with a single key "graph_state" which will hold a string value.
class State(TypedDict):
    message: str
    mood: str
    response: str


## Next define the node functions. The nodes are basically functions which take in a state and return a new state.
def greet(state: State):
    print('greet node executing in the graph')
    return {"message": "Hello! How are you?"}

def happy_response(state: State):
    print("happy_response node executing in the graph")
    return {"response": "I'm happy to hear that!", "mood": "happy"}

def sad_response(state: State):
    print("sad_response node executing in the graph")
    return {"response": "Cheer up!", "mood": "sad"}

## Nodes are now defined, then lets connect them with edges to form an actual graph
## Edge is a function which return the next node to visit, conditional edge is possible
## below decide_mood function is an example of a conditional edge which decides the 
## next node to visit based on the current state of the graph. In this example, we will just randomly decide to go to node2 or node3.
def decide_mood(state) -> Literal['happy_response', 'sad_response']:

    #Lets read the current state to decide on the next node
    user_input = state["message"]

    if(random.random() < 0.5):
        return "happy_response"
    
    return "sad_response"

## Then we build the graph, first the nodes
builder = StateGraph(State)
builder.add_node("greet", greet)
builder.add_node("happy_response", happy_response)
builder.add_node("sad_response", sad_response)

## then the edges
builder.add_edge(START, "greet")
builder.add_conditional_edges("greet", decide_mood)
builder.add_edge("happy_response", END)
builder.add_edge("sad_response", END)

graph = builder.compile()

## execute the graph with invoke method
initial_graph_state = {"message": "Hello world.", "mood": "", "response": ""}
print("Invoking the graph...")
print("Initial state: ", initial_graph_state)
end_state = graph.invoke(initial_graph_state)
print("Graph execution completed. Final state: ", end_state)




