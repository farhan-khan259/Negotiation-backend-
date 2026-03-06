import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agents.state import AgentState
from app.agents.prompts import STRATEGIST_PROMPT, NEGOTIATOR_PROMPT, CRITIC_PROMPT
from app.core.config import settings
from app.core.rag import get_retriever

llm = ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY)

async def strategist_node(state: AgentState):
    """
    Analyzes documents and defines the strategy.
    """
    # 1. Retrieve context
    context = ""
    try:
        retriever = get_retriever(user_id=state.get("user_id"))
        # Assuming the first message contains the initial context/goal
        query = state['messages'][0].content if state['messages'] else "negotiation terms"
        docs = await retriever.ainvoke(query)
        context = "\n".join([d.page_content for d in docs])
    except Exception as e:
        # If vector store is unavailable, proceed without context
        print(f"Retriever unavailable, proceeding without context: {e}")
    
    # 2. Generate Strategy
    user_prefs = state.get("strategy", {})
    prompt = STRATEGIST_PROMPT.format(
        tone=user_prefs.get("tone", "professional"),
        goal=user_prefs.get("goal", "lower price"),
        deal_value=state.get("deal_value", 0),
        context=context
    )
    
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    
    # Parse JSON (Simplistic parsing for MVP)
    try:
        strategy_json = json.loads(response.content.replace("```json", "").replace("```", ""))
    except:
        # Fallback if LLM doesn't return clean JSON
        strategy_json = {"raw_strategy": response.content}
    
    return {"strategy": strategy_json}

async def negotiator_node(state: AgentState):
    """
    Generates the next response to the supplier.
    """
    strategy = state['strategy']
    history = "\n".join([f"{m.type}: {m.content}" for m in state['messages']])
    
    prompt = NEGOTIATOR_PROMPT.format(
        strategy=json.dumps(strategy, indent=2),
        history=history
    )
    
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    
    return {"messages": [response]}

async def critic_node(state: AgentState):
    """
    Validates the generated response.
    """
    last_message = state['messages'][-1]
    strategy = state['strategy']
    
    prompt = CRITIC_PROMPT.format(
        response=last_message.content,
        strategy=json.dumps(strategy),
        max_price=strategy.get("max_price", "N/A"),
        tone=strategy.get("raw_strategy", "professional") # fallback
    )
    
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    
    if "APPROVED" in response.content:
        return {"next_step": "send_to_supplier"}
    else:
        return {"next_step": "revise", "messages": [SystemMessage(content=f"Critic Revision: {response.content}")]}

