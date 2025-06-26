from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.websockets import handle_ticket_websocket

router = APIRouter(prefix="/ws/v1", tags=["WebSocket"])

@router.websocket("/tickets/updates")
async def ticket_updates(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time ticket updates.
    
    Events:
    - ticket_created: New ticket created
    - ticket_assigned: Ticket assigned to agent
    - ticket_updated: Status or other fields updated
    - message_added: New message in ticket
    """
    await handle_ticket_websocket(websocket, token)