"""
WebSocket Handler for MCP Feedback Enhanced

This module provides real-time WebSocket communication for the feedback system.
Handles connection management, event broadcasting, and session synchronization.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from weakref import WeakSet

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from .config import get_settings
from .models import WebSocketMessage, MessageType, SessionStatus
from .session import get_session_manager

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and real-time communication.
    
    Features:
    - Connection lifecycle management
    - Session-based message routing
    - Event broadcasting
    - Automatic cleanup
    - Error handling and recovery
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.session_manager = get_session_manager()
        
        # Connection tracking
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_sessions: Dict[WebSocket, str] = {}
        
        # Message queues for offline sessions
        self.message_queues: Dict[str, List[WebSocketMessage]] = {}
        
        # Statistics
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        
    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """
        Accept a new WebSocket connection and associate it with a session.
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            await websocket.accept()
            
            # Validate session
            session = self.session_manager.get_session(session_id)
            if not session:
                await self._send_error(
                    websocket,
                    "INVALID_SESSION",
                    f"Session {session_id} not found"
                )
                await websocket.close(code=4004)
                return False
            
            # Check if session is expired
            if session.is_expired():
                await self._send_error(
                    websocket,
                    "SESSION_EXPIRED",
                    f"Session {session_id} has expired"
                )
                await websocket.close(code=4004)
                return False
            
            # Add connection to tracking
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            
            self.active_connections[session_id].add(websocket)
            self.connection_sessions[websocket] = session_id
            
            # Register with session manager
            self.session_manager.add_websocket_connection(session_id, websocket)
            
            # Update session activity
            self.session_manager.update_session_activity(session_id)
            
            # Activate session if not already active
            if session.status == SessionStatus.CREATED:
                self.session_manager.activate_session(session_id)
            
            # Send session assigned message
            await self._send_message(
                websocket,
                WebSocketMessage(
                    type=MessageType.SESSION_ASSIGNED,
                    session_id=session_id,
                    data={
                        "session_id": session_id,
                        "status": session.status.value,
                        "expires_at": session.expires_at.isoformat(),
                        "message": "Connected to feedback session"
                    }
                )
            )
            
            # Send any queued messages
            await self._send_queued_messages(websocket, session_id)
            
            # Update statistics
            self.total_connections += 1
            
            logger.info(f"WebSocket connected for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket for session {session_id}: {e}")
            try:
                await websocket.close(code=4000)
            except:
                pass
            return False
    
    async def disconnect(self, websocket: WebSocket):
        """
        Handle WebSocket disconnection and cleanup.
        
        Args:
            websocket: WebSocket connection to disconnect
        """
        try:
            session_id = self.connection_sessions.get(websocket)
            
            if session_id:
                # Remove from tracking
                if session_id in self.active_connections:
                    self.active_connections[session_id].discard(websocket)
                    
                    # Clean up empty session sets
                    if not self.active_connections[session_id]:
                        del self.active_connections[session_id]
                
                # Remove from session manager
                self.session_manager.remove_websocket_connection(session_id, websocket)
                
                # Remove from connection mapping
                del self.connection_sessions[websocket]
                
                logger.info(f"WebSocket disconnected for session {session_id}")
            
            # Close connection if still open
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
                
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def send_to_session(self, session_id: str, message: WebSocketMessage):
        """
        Send a message to all connections in a session.
        
        Args:
            session_id: Target session identifier
            message: Message to send
        """
        try:
            connections = self.active_connections.get(session_id, set())
            
            if not connections:
                # Queue message for when connections are available
                if session_id not in self.message_queues:
                    self.message_queues[session_id] = []
                self.message_queues[session_id].append(message)
                logger.debug(f"Queued message for offline session {session_id}")
                return
            
            # Send to all active connections
            disconnected = []
            for websocket in connections.copy():
                try:
                    await self._send_message(websocket, message)
                except Exception as e:
                    logger.warning(f"Failed to send message to WebSocket: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected:
                await self.disconnect(websocket)
                
        except Exception as e:
            logger.error(f"Error sending message to session {session_id}: {e}")
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """
        Broadcast a message to all active connections.
        
        Args:
            message: Message to broadcast
        """
        try:
            all_connections = []
            for connections in self.active_connections.values():
                all_connections.extend(connections)
            
            disconnected = []
            for websocket in all_connections:
                try:
                    await self._send_message(websocket, message)
                except Exception as e:
                    logger.warning(f"Failed to broadcast message to WebSocket: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected:
                await self.disconnect(websocket)
                
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
    
    async def handle_message(self, websocket: WebSocket, data: str):
        """
        Handle incoming WebSocket message.
        
        Args:
            websocket: Source WebSocket connection
            data: Raw message data
        """
        try:
            # Parse message
            try:
                message_data = json.loads(data)
                message = WebSocketMessage(**message_data)
            except (json.JSONDecodeError, ValueError) as e:
                await self._send_error(
                    websocket,
                    "INVALID_MESSAGE",
                    f"Invalid message format: {e}"
                )
                return
            
            session_id = self.connection_sessions.get(websocket)
            if not session_id:
                await self._send_error(
                    websocket,
                    "NO_SESSION",
                    "WebSocket not associated with a session"
                )
                return
            
            # Update session activity
            self.session_manager.update_session_activity(session_id)
            
            # Handle different message types
            if message.type == MessageType.PING:
                await self._handle_ping(websocket, message)
            elif message.type == MessageType.FEEDBACK_SUBMITTED:
                await self._handle_feedback_submitted(websocket, session_id, message)
            else:
                logger.warning(f"Unhandled message type: {message.type}")
            
            # Update statistics
            self.total_messages_received += 1
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(
                websocket,
                "PROCESSING_ERROR",
                f"Error processing message: {e}"
            )
    
    async def _handle_ping(self, websocket: WebSocket, message: WebSocketMessage):
        """Handle ping message"""
        pong_message = WebSocketMessage(
            type=MessageType.PONG,
            session_id=message.session_id,
            data={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        await self._send_message(websocket, pong_message)
    
    async def _handle_feedback_submitted(self, websocket: WebSocket, session_id: str, message: WebSocketMessage):
        """Handle feedback submitted notification"""
        # Broadcast to all connections in the session
        notification = WebSocketMessage(
            type=MessageType.FEEDBACK_SUBMITTED,
            session_id=session_id,
            data={
                "message": "Feedback has been submitted successfully",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        await self.send_to_session(session_id, notification)
    
    async def _send_message(self, websocket: WebSocket, message: WebSocketMessage):
        """Send a message to a specific WebSocket"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message.model_dump_json())
                self.total_messages_sent += 1
            else:
                logger.warning("Attempted to send message to disconnected WebSocket")
                
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            raise
    
    async def _send_error(self, websocket: WebSocket, error_code: str, error_message: str):
        """Send an error message to a WebSocket"""
        error_msg = WebSocketMessage(
            type=MessageType.ERROR,
            data={
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        try:
            await self._send_message(websocket, error_msg)
        except:
            pass  # Ignore errors when sending error messages
    
    async def _send_queued_messages(self, websocket: WebSocket, session_id: str):
        """Send any queued messages for a session"""
        try:
            if session_id in self.message_queues:
                messages = self.message_queues[session_id]
                for message in messages:
                    await self._send_message(websocket, message)
                
                # Clear the queue
                del self.message_queues[session_id]
                logger.debug(f"Sent {len(messages)} queued messages to session {session_id}")
                
        except Exception as e:
            logger.error(f"Error sending queued messages: {e}")
    
    async def cleanup_session(self, session_id: str):
        """Clean up all connections and data for a session"""
        try:
            # Disconnect all connections for the session
            if session_id in self.active_connections:
                connections = self.active_connections[session_id].copy()
                for websocket in connections:
                    await self.disconnect(websocket)
            
            # Clear message queue
            if session_id in self.message_queues:
                del self.message_queues[session_id]
                
            logger.info(f"Cleaned up WebSocket data for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    def get_connection_stats(self) -> Dict[str, any]:
        """Get WebSocket connection statistics"""
        active_sessions = len(self.active_connections)
        total_active_connections = sum(len(connections) for connections in self.active_connections.values())
        queued_sessions = len(self.message_queues)
        total_queued_messages = sum(len(messages) for messages in self.message_queues.values())
        
        return {
            "active_sessions": active_sessions,
            "total_active_connections": total_active_connections,
            "queued_sessions": queued_sessions,
            "total_queued_messages": total_queued_messages,
            "total_connections_ever": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    return websocket_manager
