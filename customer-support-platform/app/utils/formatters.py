from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from app.utils.enums import TicketStatus, TicketCriticality


def format_error_response(message: str, code: str = "error") -> Dict[str, str]:
    """Format error response."""
    return {
        "status": "error",
        "code": code,
        "message": message
    }


def format_success_response(
    data: Any,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Format success response."""
    response = {
        "status": "success",
        "data": data
    }
    if message:
        response["message"] = message
    return response


def format_ticket_summary(
    ticket_id: str,
    status: TicketStatus,
    criticality: TicketCriticality,
    created_at: datetime,
    category: str
) -> str:
    """Format ticket summary for notifications."""
    return (
        f"Ticket #{ticket_id}\n"
        f"Status: {status.value}\n"
        f"Criticality: {criticality.value}\n"
        f"Category: {category}\n"
        f"Created: {created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def format_pagination_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int
) -> Dict[str, Any]:
    """Format paginated response."""
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


def format_file_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"