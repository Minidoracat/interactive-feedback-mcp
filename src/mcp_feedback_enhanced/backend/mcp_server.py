"""
MCP Server Implementation for MCP Feedback Enhanced

This module implements the Model Context Protocol server with the collect_feedback tool.
Provides seamless integration with MCP clients and LLM applications.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

from .config import get_settings
from .models import FeedbackModel, ImageModel, SessionModel, SessionStatus
from .session import get_session_manager
from .file_handler import get_file_handler

logger = logging.getLogger(__name__)


class MCPFeedbackServer:
    """
    MCP Server for feedback collection with enhanced features.
    
    Features:
    - collect_feedback tool implementation
    - Session management integration
    - File upload support
    - Real-time status tracking
    - Comprehensive error handling
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.session_manager = get_session_manager()
        self.file_handler = get_file_handler()
        
        # Initialize FastMCP server
        self.mcp = FastMCP(
            name="MCP Feedback Enhanced",
            description="Advanced feedback collection system with real-time web interface and file upload support"
        )
        
        # Register tools and prompts
        self._register_tools()
        self._register_prompts()
        
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.mcp.tool()
        async def collect_feedback(
            session_id: str,
            feedback_text: Optional[str] = None,
            images: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Collect user feedback with optional text and images.
            
            This tool allows MCP clients to collect feedback from users through
            a web interface. It supports text feedback and image uploads.
            
            Args:
                session_id: Unique session identifier (format: feedback_{timestamp}_{random})
                feedback_text: Optional text feedback from user
                images: Optional list of base64-encoded image data
                metadata: Optional additional metadata
                ctx: MCP context for advanced operations
                
            Returns:
                Dictionary containing collection results and session information
                
            Raises:
                ValueError: If session_id is invalid or feedback is empty
                RuntimeError: If session management fails
            """
            try:
                if ctx:
                    ctx.info(f"Starting feedback collection for session {session_id}")
                
                # Validate session ID format
                if not session_id or not session_id.startswith("feedback_"):
                    raise ValueError("Invalid session ID format. Must start with 'feedback_'")
                
                # Validate that we have some feedback content
                if not feedback_text and not images:
                    raise ValueError("Feedback must contain either text or images")
                
                # Get or create session
                session = self.session_manager.get_session(session_id)
                if not session:
                    # Create new session
                    session = self.session_manager.create_session(
                        session_id=session_id,
                        client_info={"source": "mcp_client", "tool": "collect_feedback"}
                    )
                    if ctx:
                        ctx.info(f"Created new session {session_id}")
                
                # Activate session
                self.session_manager.activate_session(session_id)
                
                # Process images if provided
                processed_images = []
                if images:
                    if ctx:
                        ctx.info(f"Processing {len(images)} images")
                        await ctx.report_progress(0, len(images))
                    
                    for i, image_data in enumerate(images):
                        try:
                            # Decode and process image
                            image_bytes, content_type = self.file_handler.decode_base64_image(image_data)
                            
                            # Generate filename
                            filename = f"feedback_image_{i+1}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jpg"
                            
                            # Process image
                            image_model = self.file_handler.process_image(
                                image_bytes=image_bytes,
                                content_type=content_type,
                                filename=filename
                            )
                            
                            processed_images.append(image_model)
                            
                            if ctx:
                                await ctx.report_progress(i + 1, len(images))
                                
                        except Exception as e:
                            logger.error(f"Error processing image {i+1}: {e}")
                            if ctx:
                                ctx.info(f"Failed to process image {i+1}: {e}")
                            # Continue with other images
                            continue
                
                # Create feedback model
                feedback = FeedbackModel(
                    session_id=session_id,
                    text=feedback_text,
                    images=processed_images,
                    metadata=metadata or {}
                )
                
                # Add feedback to session
                success = self.session_manager.add_feedback(session_id, feedback)
                if not success:
                    raise RuntimeError("Failed to add feedback to session")
                
                # Complete session
                self.session_manager.complete_session(session_id)
                
                # Prepare response
                response = {
                    "success": True,
                    "session_id": session_id,
                    "feedback_id": feedback.id,
                    "message": "Feedback collected successfully",
                    "summary": {
                        "text_length": len(feedback_text) if feedback_text else 0,
                        "image_count": len(processed_images),
                        "total_size_bytes": sum(img.size for img in processed_images),
                        "created_at": feedback.created_at.isoformat()
                    },
                    "session_status": session.status.value,
                    "web_interface_url": f"http://{self.settings.host}:{self.settings.port}/?session={session_id}"
                }
                
                if ctx:
                    ctx.info(f"Feedback collection completed successfully for session {session_id}")
                
                logger.info(f"Collected feedback for session {session_id}: {len(feedback_text) if feedback_text else 0} chars, {len(processed_images)} images")
                
                return response
                
            except ValueError as e:
                error_msg = f"Validation error: {e}"
                logger.error(error_msg)
                if ctx:
                    ctx.info(error_msg)
                raise ValueError(error_msg)
                
            except Exception as e:
                error_msg = f"Unexpected error during feedback collection: {e}"
                logger.error(error_msg)
                if ctx:
                    ctx.info(error_msg)
                raise RuntimeError(error_msg)
        
        @self.mcp.tool()
        async def get_session_status(
            session_id: str,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Get the current status of a feedback session.
            
            Args:
                session_id: Session identifier
                ctx: MCP context for advanced operations
                
            Returns:
                Dictionary containing session status and information
            """
            try:
                if ctx:
                    ctx.info(f"Checking status for session {session_id}")
                
                session = self.session_manager.get_session(session_id)
                if not session:
                    return {
                        "success": False,
                        "session_id": session_id,
                        "status": "not_found",
                        "message": "Session not found"
                    }
                
                # Update activity
                self.session_manager.update_session_activity(session_id)
                
                response = {
                    "success": True,
                    "session_id": session_id,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "is_expired": session.is_expired(),
                    "is_active": session.is_active(),
                    "has_feedback": session.feedback is not None,
                    "web_interface_url": f"http://{self.settings.host}:{self.settings.port}/?session={session_id}"
                }
                
                if session.feedback:
                    response["feedback_summary"] = {
                        "feedback_id": session.feedback.id,
                        "text_length": len(session.feedback.text) if session.feedback.text else 0,
                        "image_count": len(session.feedback.images),
                        "created_at": session.feedback.created_at.isoformat()
                    }
                
                return response
                
            except Exception as e:
                error_msg = f"Error getting session status: {e}"
                logger.error(error_msg)
                if ctx:
                    ctx.info(error_msg)
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": error_msg
                }
        
        @self.mcp.tool()
        async def create_feedback_session(
            session_id: Optional[str] = None,
            timeout_minutes: int = 60,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Create a new feedback collection session.
            
            Args:
                session_id: Optional custom session ID (auto-generated if not provided)
                timeout_minutes: Session timeout in minutes (default: 60)
                ctx: MCP context for advanced operations
                
            Returns:
                Dictionary containing new session information
            """
            try:
                # Generate session ID if not provided
                if not session_id:
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    random_id = str(uuid.uuid4())[:8]
                    session_id = f"feedback_{timestamp}_{random_id}"
                
                if ctx:
                    ctx.info(f"Creating new feedback session {session_id}")
                
                # Create session
                session = self.session_manager.create_session(
                    session_id=session_id,
                    client_info={"source": "mcp_client", "tool": "create_feedback_session"}
                )
                
                response = {
                    "success": True,
                    "session_id": session_id,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "timeout_minutes": timeout_minutes,
                    "web_interface_url": f"http://{self.settings.host}:{self.settings.port}/?session={session_id}",
                    "message": f"Session created successfully. Users can provide feedback at the web interface URL."
                }
                
                if ctx:
                    ctx.info(f"Created session {session_id}, expires at {session.expires_at}")
                
                logger.info(f"Created new feedback session {session_id}")
                
                return response
                
            except Exception as e:
                error_msg = f"Error creating feedback session: {e}"
                logger.error(error_msg)
                if ctx:
                    ctx.info(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
    
    def _register_prompts(self):
        """Register MCP prompts"""
        
        @self.mcp.prompt()
        def feedback_collection_guide(
            session_id: str,
            context: str = "general feedback"
        ) -> List[base.Message]:
            """
            Generate a prompt to guide users through the feedback collection process.
            
            Args:
                session_id: Session identifier for the feedback collection
                context: Context or purpose of the feedback collection
                
            Returns:
                List of messages to guide the user
            """
            web_url = f"http://{self.settings.host}:{self.settings.port}/?session={session_id}"
            
            return [
                base.UserMessage(
                    f"I need to collect feedback for: {context}"
                ),
                base.AssistantMessage(
                    f"I'll help you collect feedback using the MCP Feedback Enhanced system. "
                    f"I've created a feedback session with ID: {session_id}\n\n"
                    f"Users can provide feedback through the web interface at: {web_url}\n\n"
                    f"The web interface supports:\n"
                    f"- Text feedback input\n"
                    f"- Image uploads with drag-and-drop\n"
                    f"- Real-time status updates\n"
                    f"- Session management\n\n"
                    f"You can also use the collect_feedback tool directly to submit feedback programmatically."
                ),
                base.UserMessage(
                    "How should I proceed with the feedback collection?"
                )
            ]
    
    async def start(self):
        """Start the MCP server"""
        try:
            # Start session manager
            await self.session_manager.start()
            logger.info("MCP Feedback Server started successfully")
            
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server"""
        try:
            # Stop session manager
            await self.session_manager.stop()
            logger.info("MCP Feedback Server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")
            raise
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": "MCP Feedback Enhanced",
            "version": "0.1.0",
            "description": "Advanced feedback collection system with real-time web interface and file upload support",
            "capabilities": {
                "tools": ["collect_feedback", "get_session_status", "create_feedback_session"],
                "prompts": ["feedback_collection_guide"],
                "features": [
                    "Real-time web interface",
                    "File upload support",
                    "Session management",
                    "Image processing",
                    "WebSocket communication"
                ]
            },
            "endpoints": {
                "web_interface": f"http://{self.settings.host}:{self.settings.port}/",
                "api_docs": f"http://{self.settings.host}:{self.settings.port}/docs",
                "health_check": f"http://{self.settings.host}:{self.settings.port}/api/health"
            }
        }


# Global MCP server instance
mcp_feedback_server = MCPFeedbackServer()


def get_mcp_server() -> MCPFeedbackServer:
    """Get the global MCP server instance"""
    return mcp_feedback_server
