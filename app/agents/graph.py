from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes import strategist_node, negotiator_node, critic_node

def should_approve(state: AgentState):
    """
    Conditional logic to determine if human approval is needed.
    """
    if state.get("requires_approval") and state.get("deal_value", 0) >= 1000:
        return "wait_for_human"
    return "send_to_supplier"

# Define the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("strategist", strategist_node)
workflow.add_node("negotiator", negotiator_node)
workflow.add_node("critic", critic_node)

# Set entry point
workflow.set_entry_point("strategist")

# Define edges
workflow.add_edge("strategist", "negotiator")
workflow.add_edge("negotiator", "critic")

# Conditional edge from critic
def critic_router(state: AgentState):
    if state.get("next_step") == "revise":
        return "negotiator" # Loop back to fix
    
    # If approved, check for human approval requirement
    if state.get("requires_approval", False):
        return "wait_for_human"
    
    return END

workflow.add_conditional_edges(
    "critic",
    critic_router,
    {
        "negotiator": "negotiator",
        "wait_for_human": END, # In a real graph, this would be an interrupt
        END: END
    }
)

# Compile
app_graph = workflow.compile()
