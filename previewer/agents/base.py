from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class MessageType(str, Enum):
    """Types of messages that can be sent between agents."""
    FILE_ANALYSIS = 'file_analysis'
    REVIEW_REQUEST = 'review_request'
    REVIEW = 'review'
    REPORT = 'report'
    ERROR = 'error'

class Message(BaseModel):
    """Message passed between agents."""
    type: MessageType
    content: Dict[str, Any]
    source: str

    class Config:
        arbitrary_types_allowed = True

class AgentState(BaseModel):
    """State of an agent."""
    agent_id: str = "base_agent"
    status: str = "ready"
    memory: Dict = {}
    last_message: Optional[Message] = None

    class Config:
        arbitrary_types_allowed = True

class BaseAgent:
    """Base class for all agents."""
    
    def __init__(self):
        """Initialize agent state."""
        self.state = AgentState()
        
    def create_message(self, type: MessageType, content: Dict[str, Any], source: str = None) -> Message:
        """Create a message from this agent."""
        return Message(
            type=type,
            content=content,
            source=source or self.state.agent_id
        )
    
    def process_message(self, message: Message) -> List[Message]:
        """Process an incoming message and return a list of response messages."""
        raise NotImplementedError("Agents must implement process_message")

    def update_state(self, **kwargs):
        """Update agent's internal state."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
