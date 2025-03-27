import os
import json
from typing import Dict, Any, Optional, List, Union
import redis

class RedisService:
    """
    Service for handling Redis operations including session management and caching.
    """
    
    def __init__(self, host: str = None, port: int = None):
        """
        Initialize the Redis service.
        
        Args:
            host: Redis host
            port: Redis port
        """
        # Get connection details from environment or use defaults
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", 6379))
        
        # Initialize Redis client
        self.redis_client = redis.Redis(
            host=self.host,
            port=self.port,
            decode_responses=True  # Automatically decode responses to strings
        )
        
        # Session expiration time (24 hours in seconds)
        self.session_expiry = 86400
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Get the session data from Redis
            session_data = self.redis_client.get(f"session:{session_id}")
            
            # Return parsed data if it exists
            if session_data:
                logger.info(f"Retrieved session {session_id} from Redis")
                return json.loads(session_data)
            
            logger.warning(f"Session {session_id} not found in Redis")
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
            return None
    
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Save or update a session.
        
        Args:
            session_id: The unique session identifier
            session_data: The session data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Convert data to JSON string
            session_json = json.dumps(session_data)
            
            # Save to Redis with expiration
            self.redis_client.setex(
                f"session:{session_id}",
                self.session_expiry,
                session_json
            )
            
            logger.info(f"Saved session {session_id} to Redis with expiry {self.session_expiry}s")
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error saving session {session_id}: {str(e)}")
            return False
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update specific fields in an existing session.
        
        Args:
            session_id: The unique session identifier
            update_data: The data to update in the session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing session
            session_data = self.get_session(session_id)
            
            # Return False if session doesn't exist
            if not session_data:
                return False
            
            # Update the session data
            session_data.update(update_data)
            
            # Save the updated session
            return self.save_session(session_id, session_data)
        except Exception as e:
            print(f"Error updating session: {str(e)}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the session key
            self.redis_client.delete(f"session:{session_id}")
            return True
        except Exception as e:
            print(f"Error deleting session: {str(e)}")
            return False
    
    def add_to_chat_history(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a message to the chat history for a session.
        
        Args:
            session_id: The unique session identifier
            message: The message to add (should have 'role' and 'content' keys)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing session
            session_data = self.get_session(session_id)
            
            # Create new session if it doesn't exist
            if not session_data:
                session_data = {"chat_history": []}
            
            # Ensure chat_history exists
            if "chat_history" not in session_data:
                session_data["chat_history"] = []
            
            # Add message to chat history
            session_data["chat_history"].append(message)
            
            # Save the updated session
            return self.save_session(session_id, session_data)
        except Exception as e:
            print(f"Error adding to chat history: {str(e)}")
            return False
    
    def get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get the chat history for a session.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            List of chat messages
        """
        try:
            # Get existing session
            session_data = self.get_session(session_id)
            
            # Return empty list if session doesn't exist or has no chat history
            if not session_data or "chat_history" not in session_data:
                return []
            
            return session_data["chat_history"]
        except Exception as e:
            print(f"Error getting chat history: {str(e)}")
            return []
    
    def save_location(self, session_id: str, location: Dict[str, Any]) -> bool:
        """
        Save a location to the session for reuse.
        
        Args:
            session_id: The unique session identifier
            location: Location data including coordinates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the session with the location
            return self.update_session(session_id, {"last_location": location})
        except Exception as e:
            print(f"Error saving location: {str(e)}")
            return False
    
    def get_last_location(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last used location for a session.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            Location data or None if not available
        """
        try:
            # Get existing session
            session_data = self.get_session(session_id)
            
            # Return None if session doesn't exist or has no last_location
            if not session_data or "last_location" not in session_data:
                return None
            
            return session_data["last_location"]
        except Exception as e:
            print(f"Error getting last location: {str(e)}")
            return None
    
    def ping(self) -> bool:
        """
        Check if Redis is reachable.
        
        Returns:
            True if Redis is reachable, False otherwise
        """
        try:
            return self.redis_client.ping()
        except Exception as e:
            print(f"Error connecting to Redis: {str(e)}")
            return False