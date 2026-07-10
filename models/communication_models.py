"""
ResQNet AI - Communication Pydantic Models
"""

from typing import List
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    """A single notification sent by the Communication Agent."""
    recipient_type:  str    # citizen|hospital|ambulance|authority|public
    recipient_name:  str
    recipient_id:    int = 0
    channel:         str    # sms|email|app|broadcast
    message:         str
    status:          str = "sent"


class CommunicationResult(BaseModel):
    """Output of the Communication Agent."""
    notifications:          List[NotificationItem] = Field(default_factory=list)
    public_safety_alert:    str = ""
    hospital_notice:        str = ""
    ambulance_dispatch_msg: str = ""
    authority_briefing:     str = ""
    total_notified:         int = 0
    reasoning:              str = ""
    is_simulation:          bool = False
