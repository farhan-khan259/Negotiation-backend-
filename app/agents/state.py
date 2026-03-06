from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    negotiation_id: str
    user_id: int
    strategy: dict
    documents: List[str]
    next_step: str
    deal_value: float
    requires_approval: bool
