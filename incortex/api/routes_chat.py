"""POST /v1/chat — one trip through the cognitive loop (Design_Doc §19.3-19.4)."""

from fastapi import APIRouter, Request

from incortex.api.schemas import ChatRequest, envelope

router = APIRouter()


@router.post("/v1/chat")
def chat(request: Request, body: ChatRequest):
    core = request.app.state.core
    context = core.handle(body.message, session_id=body.session_id)
    memory_updated = any(name == "store" for name, _ in context.stages)
    data = {
        "response": context.reply,
        "accepted": context.accepted,
        "confidence": context.chain_confidence,
        "intent": context.intent,
        "organs_used": context.organs_used,
        "memory_updated": memory_updated,
        "feedback_requested": context.accepted,  # rate real answers (§19.4)
        "session_id": context.session_id,
    }
    return envelope(data)
