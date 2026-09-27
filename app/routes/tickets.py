"""Support ticket triage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.fixtures import tickets
from app.model_client import ModelTimeout, ModelUnavailable, get_client
from app.models import ModelPayload, Ticket, TicketTriage, TicketTriageResponse

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/{ticket_id}/triage", response_model=TicketTriageResponse)
def triage_ticket(ticket_id: str) -> TicketTriageResponse:
    ticket_data = next((item for item in tickets() if item["id"] == ticket_id), None)
    if ticket_data is None:
        raise HTTPException(status_code=404, detail=f"no ticket with id {ticket_id}")

    try:
        result = get_client().complete("classify_ticket", {
            "subject": ticket_data["subject"],
            "body": ticket_data["body"],
        })
    except ModelTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    value = result.value
    return TicketTriageResponse(
        ticket=Ticket(**ticket_data),
        triage=TicketTriage(
            category=value["category"],
            priority=value["priority"],
            suggested_team=value["team"],
            draft_first_reply=value["draft_reply"],
            requires_human_review=result.confidence < 0.50,
        ),
        model=ModelPayload(**result.as_dict()),
    )