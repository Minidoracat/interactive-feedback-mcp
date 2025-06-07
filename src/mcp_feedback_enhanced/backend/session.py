"""
Session Management for MCP Feedback Enhanced

This module provides session management functionality including creation,
storage, cleanup, and lifecycle management.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from weakref import WeakSet

from .models import SessionModel, SessionStatus, FeedbackModel
from .config import get_settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions with automatic cleanup and lifecycle management.
    
    Features:
    - In-memory session storage
    - Automatic session expiration
    - Background cleanup task
    - Session activity tracking
    - WebSocket connection tracking
    """
    
    def __init__(self):
        self.sessions: Dict[str, SessionModel] = {}
        self.websocket_connections: Dict[str, WeakSet] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self.settings = get_settings()
        
    async def start(self):
        """Start the session manager and background tasks"""
        if self._running:
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")
        
    async def stop(self):
        """Stop the session manager and cleanup tasks"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
        # Close all WebSocket connections
        for session_id, connections in self.websocket_connections.items():
            for ws in list(connections):
                try:
                    await ws.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket for session {session_id}: {e}")
                    
        self.sessions.clear()
        self.websocket_connections.clear()
        logger.info("Session manager stopped")
        
    def create_session(self, session_id: str, client_info: Optional[Dict] = None) -> SessionModel:
        """
        Create a new session
        
        Args:
            session_id: Unique session identifier
            client_info: Optional client information
            
        Returns:
            Created session model
            
        Raises:
            ValueError: If session already exists or invalid parameters
        """
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} already exists")
            
        if not session_id.startswith("feedback_"):
            raise ValueError("Session ID must start with 'feedback_'")
            
        # Check session limit
        if len(self.sessions) >= self.settings.max_sessions:
            # Clean up expired sessions first
            self._cleanup_expired_sessions()
            
            if len(self.sessions) >= self.settings.max_sessions:
                raise ValueError("Maximum number of sessions reached")
        
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.settings.session_timeout)
        
        session = SessionModel(
            id=session_id,
            status=SessionStatus.CREATED,
            client_info=client_info or {},
            expires_at=expires_at
        )
        
        self.sessions[session_id] = session
        self.websocket_connections[session_id] = WeakSet()
        
        logger.info(f"Created session {session_id}, expires at {expires_at}")
        return session
        
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """
        Get session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session model if found and not expired, None otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
            
        if session.is_expired():
            self._expire_session(session_id)
            return None
            
        return session
        
    def activate_session(self, session_id: str) -> bool:
        """
        Activate a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was activated, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
            
        session.status = SessionStatus.ACTIVE
        session.update_activity()
        
        logger.info(f"Activated session {session_id}")
        return True
        
    def update_session_activity(self, session_id: str) -> bool:
        """
        Update session activity timestamp
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was updated, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
            
        session.update_activity()
        return True
        
    def complete_session(self, session_id: str) -> bool:
        """
        Mark session as completed
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was completed, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
            
        session.complete()
        logger.info(f"Completed session {session_id}")
        return True
        
    def add_feedback(self, session_id: str, feedback: FeedbackModel) -> bool:
        """
        Add feedback to session
        
        Args:
            session_id: Session identifier
            feedback: Feedback model
            
        Returns:
            True if feedback was added, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
            
        session.feedback = feedback
        session.update_activity()
        
        logger.info(f"Added feedback to session {session_id}")
        return True
        
    def remove_session(self, session_id: str) -> bool:
        """
        Remove session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was removed, False otherwise
        """
        if session_id not in self.sessions:
            return False
            
        # Close WebSocket connections
        if session_id in self.websocket_connections:
            connections = self.websocket_connections[session_id]
            for ws in list(connections):
                try:
                    asyncio.create_task(ws.close())
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
            del self.websocket_connections[session_id]
            
        del self.sessions[session_id]
        logger.info(f"Removed session {session_id}")
        return True
        
    def add_websocket_connection(self, session_id: str, websocket):
        """
        Add WebSocket connection to session
        
        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        if session_id not in self.websocket_connections:
            self.websocket_connections[session_id] = WeakSet()
            
        self.websocket_connections[session_id].add(websocket)
        logger.debug(f"Added WebSocket connection to session {session_id}")
        
    def remove_websocket_connection(self, session_id: str, websocket):
        """
        Remove WebSocket connection from session
        
        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        if session_id in self.websocket_connections:
            try:
                self.websocket_connections[session_id].discard(websocket)
                logger.debug(f"Removed WebSocket connection from session {session_id}")
            except KeyError:
                pass
                
    def get_session_websockets(self, session_id: str) -> List:
        """
        Get all WebSocket connections for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of WebSocket connections
        """
        if session_id not in self.websocket_connections:
            return []
            
        return list(self.websocket_connections[session_id])
        
    def get_session_stats(self) -> Dict[str, int]:
        """
        Get session statistics
        
        Returns:
            Dictionary with session statistics
        """
        stats = {
            "total": len(self.sessions),
            "created": 0,
            "active": 0,
            "completed": 0,
            "expired": 0,
            "error": 0
        }
        
        for session in self.sessions.values():
            if session.is_expired():
                stats["expired"] += 1
            else:
                stats[session.status.value] += 1
                
        return stats
        
    def _expire_session(self, session_id: str):
        """Mark session as expired"""
        session = self.sessions.get(session_id)
        if session:
            session.expire()
            logger.info(f"Expired session {session_id}")
            
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
                
        for session_id in expired_sessions:
            self.remove_session(session_id)
            
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self._running:
            try:
                self._cleanup_expired_sessions()
                await asyncio.sleep(self.settings.session_cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying


# Global session manager instance
session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    return session_manager
