from typing import Any, List
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.api import deps
from app.agents.graph import app_graph
from app.agents.state import AgentState
from app.crud import crud_negotiation
from app.schemas.negotiation import NegotiationCreate, Negotiation as NegotiationSchema
from app.schemas.message import MessageCreate, Message as MessageSchema
from app.models.negotiation import Negotiation as NegotiationModel
from app.models.message import Message as MessageModel

router = APIRouter()

def _wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    for word in words:
        if sum(len(w) for w in current) + len(current) + len(word) <= max_chars:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [""]

def _build_transcript_pdf(negotiation: NegotiationModel, messages: List[MessageModel]) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    def draw_line(text: str, line_height: int = 14) -> None:
        nonlocal y
        if y <= margin:
            pdf.showPage()
            y = height - margin
        pdf.drawString(margin, y, text)
        y -= line_height

    title = f"Negotiation Transcript #{negotiation.id}"
    draw_line(title, 18)
    draw_line(f"Supplier: {negotiation.supplier_name}")
    draw_line(f"Tone: {negotiation.tone} | Goal: {negotiation.goal}")
    draw_line(f"Deal Value: {negotiation.deal_value}")
    draw_line(f"Created: {negotiation.created_at.isoformat()}")
    draw_line("", 12)
    draw_line("Messages:")
    draw_line("", 8)

    for msg in messages:
        timestamp = msg.timestamp.isoformat() if msg.timestamp else ""
        header = f"[{timestamp}] {msg.sender.upper()}:"
        draw_line(header)
        content = (msg.content or "").replace("\n", " ").strip()
        for line in _wrap_text(content, 95):
            draw_line(f"  {line}")
        draw_line("", 8)

    pdf.save()
    buffer.seek(0)
    return buffer

def _db_messages_to_langchain(db_messages: List[MessageModel]) -> List[Any]:
    messages = []
    for msg in db_messages:
        if msg.sender == "buyer" or msg.sender == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.sender == "ai":
            messages.append(AIMessage(content=msg.content))
        elif msg.sender == "supplier":
            messages.append(HumanMessage(content=f"Supplier: {msg.content}")) # Treat supplier as human for now
    return messages

@router.post("/start", response_model=dict)
async def start_negotiation(
    user_input: dict,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> Any:
    """
    Start a new negotiation session with the AI.
    """
    # 1. Create Negotiation Record
    neg_in = NegotiationCreate(
        supplier_name=user_input.get("supplier_name", "Unknown Supplier"),
        deal_value=float(user_input.get("estimatedValue", 0)),
        tone=user_input.get("negotiationTone", "professional"),
        goal=user_input.get("primaryGoal", "lower-price"),
        autonomy_mode="human-in-loop" if float(user_input.get("estimatedValue", 0)) >= 1000 else "autonomous"
    )
    negotiation = await crud_negotiation.create_negotiation(db, neg_in, current_user.id)
    
    # 2. Initial State
    initial_msg_content = f"Start negotiation with {neg_in.supplier_name}"
    
    # Save initial system/user message
    # await crud_negotiation.create_message(db, MessageCreate(
    #     negotiation_id=negotiation.id,
    #     sender="user", 
    #     content=initial_msg_content
    # ))

    initial_state: AgentState = {
        "messages": [HumanMessage(content=initial_msg_content)],
        "negotiation_id": str(negotiation.id),
        "user_id": current_user.id,
        "strategy": {
            "tone": neg_in.tone,
            "goal": neg_in.goal
        },
        "documents": [],
        "next_step": "start",
        "deal_value": neg_in.deal_value,
        "requires_approval": neg_in.deal_value >= 1000
    }
    
    # 3. Run Graph
    final_state = await app_graph.ainvoke(initial_state)
    
    # 4. Save AI Responses
    ai_messages = [m for m in final_state['messages'] if isinstance(m, AIMessage)]
    saved_messages = []
    for m in ai_messages:
        msg = await crud_negotiation.create_message(db, MessageCreate(
            negotiation_id=negotiation.id,
            sender="ai",
            content=m.content
        ))
        saved_messages.append(msg)
    
    return {
        "negotiation_id": negotiation.id,
        "messages": [m.content for m in ai_messages],
        "strategy": final_state.get('strategy')
    }

@router.get("/{negotiation_id}", response_model=dict)
async def get_negotiation_summary(
    negotiation_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> Any:
    """
    Get negotiation details and message history for the current user.
    """
    negotiation = await crud_negotiation.get_negotiation(db, negotiation_id, user_id=current_user.id)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    messages = await crud_negotiation.get_messages(db, negotiation_id)
    negotiation_out = NegotiationSchema.model_validate(negotiation)
    messages_out = [MessageSchema.model_validate(msg) for msg in messages]
    return {
        "negotiation": negotiation_out,
        "messages": messages_out,
    }

@router.get("/{negotiation_id}/transcript")
async def download_transcript(
    negotiation_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> Any:
    """
    Download a PDF transcript of the negotiation.
    """
    negotiation = await crud_negotiation.get_negotiation(db, negotiation_id, user_id=current_user.id)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    messages = await crud_negotiation.get_messages(db, negotiation_id)
    pdf_buffer = _build_transcript_pdf(negotiation, messages)
    filename = f"negotiation-{negotiation_id}-transcript.pdf"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/{negotiation_id}/chat", response_model=dict)
async def chat_negotiation(
    negotiation_id: int,
    user_input: dict,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> Any:
    """
    Continue negotiation: User sends a message (or approval), AI responds.
    """
    negotiation = await crud_negotiation.get_negotiation(db, negotiation_id, user_id=current_user.id)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")
        
    user_message = user_input.get("message")
    
    # 1. Save User Message
    if user_message:
        await crud_negotiation.create_message(db, MessageCreate(
            negotiation_id=negotiation.id,
            sender="user",
            content=user_message
        ))

    # 2. Load History
    db_messages = await crud_negotiation.get_messages(db, negotiation_id)
    history = _db_messages_to_langchain(db_messages)
    
    # 3. Prepare State
    current_state: AgentState = {
        "messages": history,
        "negotiation_id": str(negotiation.id),
        "user_id": current_user.id,
        "strategy": {
            "tone": negotiation.tone,
            "goal": negotiation.goal
        },
        "documents": [],
        "next_step": "continue",
        "deal_value": negotiation.deal_value,
        "requires_approval": negotiation.deal_value >= 1000
    }
    
    # 4. Run Graph
    final_state = await app_graph.ainvoke(current_state)
    
    # 5. Extract NEW AI messages (simple diff or just take the last ones)
    # Since LangGraph appends, we can check if the last message is AI and not in our DB history count
    # But simpler: just take the last message if it's AI
    last_message = final_state['messages'][-1]
    response_messages = []
    
    if isinstance(last_message, AIMessage):
        # Check if we already saved this (unlikely with unique runs but possible if graph returns history)
        # For now, assume the graph generated a new response
        msg = await crud_negotiation.create_message(db, MessageCreate(
            negotiation_id=negotiation.id,
            sender="ai",
            content=last_message.content
        ))
        response_messages.append(msg.content)
        
    return {
        "negotiation_id": negotiation.id,
        "messages": response_messages
    }
