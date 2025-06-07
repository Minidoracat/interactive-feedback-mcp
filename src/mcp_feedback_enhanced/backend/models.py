"""
Data Models for MCP Feedback Enhanced

This module defines Pydantic models for data validation and serialization.
Includes models for sessions, feedback, images, and WebSocket messages.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class SessionStatus(str, Enum):
    """Session status enumeration"""
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ERROR = "error"


class MessageType(str, Enum):
    """WebSocket message types"""
    SESSION_ASSIGNED = "session_assigned"
    SESSION_STATUS = "session_status"
    FEEDBACK_REQUEST = "feedback_request"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    FILE_UPLOAD_START = "file_upload_start"
    FILE_UPLOAD_PROGRESS = "file_upload_progress"
    FILE_UPLOAD_COMPLETE = "file_upload_complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class ImageModel(BaseModel):
    """Model for image data"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., pattern=r"^image/(jpeg|png|gif|webp)$")
    size: int = Field(..., ge=1)
    data: str = Field(..., description="Base64 encoded image data")
    thumbnail: Optional[str] = Field(None, description="Base64 encoded thumbnail")
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("data")
    @classmethod
    def validate_base64_data(cls, v: str) -> str:
        """Validate base64 encoded data"""
        import base64
        try:
            # Remove data URL prefix if present
            if v.startswith("data:"):
                v = v.split(",", 1)[1]
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError("Invalid base64 encoded data")

    @field_validator("size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size limits"""
        max_size = 10 * 1024 * 1024  # 10MB
        if v > max_size:
            raise ValueError(f"File size {v} exceeds maximum allowed size {max_size}")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FeedbackModel(BaseModel):
    """Model for feedback data"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., min_length=1)
    text: Optional[str] = Field(None, max_length=10000)
    images: List[ImageModel] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode='after')
    def validate_feedback_content(self) -> Self:
        """Ensure feedback has either text or images"""
        if not self.text and not self.images:
            raise ValueError("Feedback must contain either text or images")
        return self

    @field_validator("images")
    @classmethod
    def validate_image_count(cls, v: List[ImageModel]) -> List[ImageModel]:
        """Validate number of images"""
        max_images = 10
        if len(v) > max_images:
            raise ValueError(f"Maximum {max_images} images allowed")
        return v

    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionModel(BaseModel):
    """Model for session data"""
    
    id: str = Field(..., min_length=1)
    status: SessionStatus = Field(default=SessionStatus.CREATED)
    feedback: Optional[FeedbackModel] = Field(None)
    client_info: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(...)
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        """Validate session ID format"""
        if not v.startswith("feedback_"):
            raise ValueError("Session ID must start with 'feedback_'")
        return v

    @model_validator(mode='after')
    def validate_expiration(self) -> Self:
        """Validate expiration time"""
        if self.expires_at <= self.created_at:
            raise ValueError("Expiration time must be after creation time")
        return self
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at

    def is_active(self) -> bool:
        """Check if session is active"""
        return (
            self.status == SessionStatus.ACTIVE and
            not self.is_expired()
        )

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def expire(self):
        """Mark session as expired"""
        self.status = SessionStatus.EXPIRED
        self.updated_at = datetime.now(timezone.utc)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebSocketMessage(BaseModel):
    """Model for WebSocket messages"""
    
    type: MessageType = Field(...)
    session_id: Optional[str] = Field(None)
    data: Optional[Dict[str, Any]] = Field(None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Model for error responses"""
    
    error: str = Field(...)
    message: str = Field(...)
    details: Optional[Dict[str, Any]] = Field(None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthResponse(BaseModel):
    """Model for health check responses"""
    
    status: str = Field(default="healthy")
    version: str = Field(...)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uptime: float = Field(...)
    sessions: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VersionResponse(BaseModel):
    """Model for version information responses"""
    
    version: str = Field(...)
    build_date: Optional[str] = Field(None)
    git_commit: Optional[str] = Field(None)
    python_version: str = Field(...)
    dependencies: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
