"""
Configuration Management for MCP Feedback Enhanced

This module provides centralized configuration management using Pydantic Settings.
It supports environment variables, .env files, and default values.
"""

import os
from pathlib import Path
from typing import List, Optional, Set
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    """Server configuration settings"""
    
    # Server settings
    host: str = Field(
        default="127.0.0.1",
        description="Host to bind the server to"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port to bind the server to"
    )
    workers: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Number of worker processes"
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload for development"
    )
    log_level: str = Field(
        default="info",
        description="Log level (debug, info, warning, error, critical)"
    )
    
    # Session management
    session_timeout: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Session timeout in seconds (1 minute to 24 hours)"
    )
    session_cleanup_interval: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Session cleanup interval in seconds"
    )
    max_sessions: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of concurrent sessions"
    )
    
    # File upload settings
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,  # 1KB minimum
        le=100 * 1024 * 1024,  # 100MB maximum
        description="Maximum file size in bytes"
    )
    allowed_file_types: Set[str] = Field(
        default={"image/jpeg", "image/png", "image/gif", "image/webp"},
        description="Allowed MIME types for file uploads"
    )
    upload_dir: Path = Field(
        default=Path("uploads"),
        description="Directory to store uploaded files"
    )
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS"
    )
    
    # Security settings
    secret_key: str = Field(
        default="mcp-feedback-enhanced-secret-key-change-in-production",
        min_length=32,
        description="Secret key for signing tokens and sessions"
    )
    
    # Development settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Frontend settings
    frontend_dir: Optional[Path] = Field(
        default=None,
        description="Directory containing frontend build files"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="MCP_FEEDBACK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.lower()

    @field_validator("upload_dir")
    @classmethod
    def validate_upload_dir(cls, v: Path | str) -> Path:
        """Ensure upload directory exists"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("frontend_dir")
    @classmethod
    def validate_frontend_dir(cls, v: Optional[Path | str]) -> Optional[Path]:
        """Validate frontend directory if provided"""
        if v is not None:
            if isinstance(v, str):
                v = Path(v)
            if not v.exists():
                raise ValueError(f"Frontend directory does not exist: {v}")
        return v
    
    def get_frontend_dir(self) -> Path:
        """Get the frontend directory, with fallback to package default"""
        if self.frontend_dir:
            return self.frontend_dir
        
        # Default to package frontend directory
        package_dir = Path(__file__).parent.parent
        frontend_dist = package_dir / "frontend" / "dist"
        
        if frontend_dist.exists():
            return frontend_dist
        
        # Fallback for development
        dev_frontend = package_dir.parent.parent / "frontend-dev" / "dist"
        if dev_frontend.exists():
            return dev_frontend
        
        raise ValueError("Frontend build directory not found")
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.debug or self.reload or os.getenv("ENVIRONMENT") == "development"


# Global configuration instance
settings = ServerConfig()


def get_settings() -> ServerConfig:
    """Get the global settings instance"""
    return settings


def reload_settings() -> ServerConfig:
    """Reload settings from environment and files"""
    global settings
    settings = ServerConfig()
    return settings
