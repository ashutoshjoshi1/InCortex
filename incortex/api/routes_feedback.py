"""POST /v1/feedback — grade the session's last task (Design_Doc §19.2)."""

from fastapi import APIRouter, Request

from incortex.api.schemas import FeedbackRequest, envelope

router = APIRouter()


@router.post("/v1/feedback")
def feedback(request: Request, body: FeedbackRequest):
    core = request.app.state.core
    # A missing task raises ValueError -> the app-level handler turns it
    # into a 400 envelope with the message intact.
    result = core.feedback(success=body.success, rating=body.rating,
                           session_id=body.session_id)
    return envelope(result.content)
