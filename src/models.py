from typing import Optional
from pydantic import BaseModel, Field

class MailMessage(BaseModel):
    """
    Pydantic model representing the mail message schema, including fields
    for internal retry tracking.
    """
    id: str = Field(..., min_length=1, description="Unique identifier for the email message")
    to: str = Field(..., min_length=1, description="Recipient email address")
    subject: str = Field(..., min_length=1, description="Email subject line")
    body: str = Field(..., min_length=1, description="Email content body")
    content_type: str = Field(default="text/plain", description="Content-Type format: 'text/plain' or 'text/html'")
    
    # Internal state tracking fields (not present in raw input but saved during processing)
    attempts: int = Field(default=0, description="Number of dispatch attempts executed")
    next_retry_at: Optional[float] = Field(default=None, description="Unix timestamp for when the next retry is scheduled")
