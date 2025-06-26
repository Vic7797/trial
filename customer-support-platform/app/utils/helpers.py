from datetime import datetime, timezone
from typing import List, Optional
import hashlib
import uuid

from fastapi import UploadFile

from app.utils.constants import MAX_FILE_SIZE, ALLOWED_MIME_TYPES


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID."""
    return uuid.uuid4()


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def generate_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return filename.split('.')[-1].lower() if '.' in filename else ''


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for storage."""
    # Remove potentially dangerous characters
    safe_chars = ('-', '_', '.')
    filename = ''.join(c for c in filename if c.isalnum() or c in safe_chars)
    return filename.lower()


def validate_file(file: UploadFile) -> Optional[str]:
    """Validate file size and type. Returns error message if invalid."""
    if file.size > MAX_FILE_SIZE:
        return f"File size exceeds maximum limit of {MAX_FILE_SIZE} bytes"
    
    if file.content_type not in ALLOWED_MIME_TYPES:
        return "File type not supported"
    
    return None


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def mask_sensitive_data(data: str) -> str:
    """Mask sensitive data like emails and phone numbers."""
    if '@' in data:  # Email
        username, domain = data.split('@')
        return f"{username[:2]}{'*' * (len(username)-2)}@{domain}"
    elif data.isdigit() and len(data) >= 10:  # Phone number
        return f"{data[:2]}{'*' * (len(data)-4)}{data[-2:]}"
    return data