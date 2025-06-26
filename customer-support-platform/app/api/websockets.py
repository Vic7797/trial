"""WebSocket manager for real-time ticket updates."""
from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
from app.core.security import verify_ws_token
from app.core.logging import logger


class TicketUpdateManager:
    """Manage WebSocket connections for ticket updates."""

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_users: Dict[UUID, Set[WebSocket]] = {}
        # organization_id -> Dict[UUID, Set[WebSocket]]
        self.org_connections: Dict[UUID, Dict[UUID, Set[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID, org_id: UUID):
        """Connect a new WebSocket client."""
        await websocket.accept()

        # Add to user connections
        if user_id not in self.active_users:
            self.active_users[user_id] = set()
        self.active_users[user_id].add(websocket)

        # Add to organization connections
        if org_id not in self.org_connections:
            self.org_connections[org_id] = {}
        if user_id not in self.org_connections[org_id]:
            self.org_connections[org_id][user_id] = set()
        self.org_connections[org_id][user_id].add(websocket)

        logger.info(f"WebSocket connected: user={user_id}, org={org_id}")

    async def disconnect(self, websocket: WebSocket, user_id: UUID, org_id: UUID):
        """Disconnect a WebSocket client."""
        # Remove from user connections
        if user_id in self.active_users:
            self.active_users[user_id].discard(websocket)
            if not self.active_users[user_id]:
                del self.active_users[user_id]

        # Remove from organization connections
        if org_id in self.org_connections:
            if user_id in self.org_connections[org_id]:
                self.org_connections[org_id][user_id].discard(websocket)
                if not self.org_connections[org_id][user_id]:
                    del self.org_connections[org_id][user_id]
            if not self.org_connections[org_id]:
                del self.org_connections[org_id]

        logger.info(f"WebSocket disconnected: user={user_id}, org={org_id}")

    async def broadcast_to_organization(
        self,
        org_id: UUID,
        message: dict,
        exclude_user: UUID = None
    ):
        """Broadcast message to all users in an organization."""
        if org_id not in self.org_connections:
            return

        for user_id, connections in self.org_connections[org_id].items():
            if user_id == exclude_user:
                continue
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(
                        f"Error broadcasting to user {user_id}: {str(e)}"
                    )

    async def send_to_user(self, user_id: UUID, message: dict):
        """Send message to a specific user's connections."""
        if user_id not in self.active_users:
            return

        for websocket in self.active_users[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {str(e)}")


# Global WebSocket manager instance
manager = TicketUpdateManager()


async def handle_ticket_websocket(
    websocket: WebSocket,
    token: str
):
    """Handle WebSocket connections for ticket updates."""
    # Verify token and get user info
    user = await verify_ws_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    try:
        await manager.connect(websocket, user.id, user.organization_id)
        
        while True:
            # Keep connection alive and handle disconnection
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            
    finally:
        await manager.disconnect(websocket, user.id, user.organization_id)


async def notify_ticket_created(org_id: UUID, ticket_id: UUID, ticket_data: dict):
    """Notify about new ticket creation."""
    await manager.broadcast_to_organization(
        org_id,
        {
            "event": "ticket_created",
            "ticket_id": str(ticket_id),
            "data": ticket_data
        }
    )


async def notify_ticket_assigned(
    org_id: UUID,
    ticket_id: UUID,
    agent_id: UUID,
    ticket_data: dict
):
    """Notify about ticket assignment."""
    # Notify the assigned agent
    await manager.send_to_user(
        agent_id,
        {
            "event": "ticket_assigned",
            "ticket_id": str(ticket_id),
            "data": ticket_data
        }
    )

    # Broadcast to organization (except assigned agent)
    await manager.broadcast_to_organization(
        org_id,
        {
            "event": "ticket_assigned",
            "ticket_id": str(ticket_id),
            "data": ticket_data
        },
        exclude_user=agent_id
    )


async def notify_ticket_updated(org_id: UUID, ticket_id: UUID, ticket_data: dict):
    """Notify about ticket updates."""
    await manager.broadcast_to_organization(
        org_id,
        {
            "event": "ticket_updated",
            "ticket_id": str(ticket_id),
            "data": ticket_data
        }
    )


async def notify_message_added(
    org_id: UUID,
    ticket_id: UUID,
    message_data: dict
):
    """Notify about new ticket messages."""
    await manager.broadcast_to_organization(
        org_id,
        {
            "event": "message_added",
            "ticket_id": str(ticket_id),
            "data": message_data
        }
    )
