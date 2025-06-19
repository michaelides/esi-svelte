from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional
import datetime

# Represents a single message in a chat
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

# Represents a full chat session, including its messages
class ChatSession(BaseModel):
    chat_id: str
    name: str
    # Using Field to ensure default is a new list for each instance
    messages: List[ChatMessage] = Field(default_factory=list)
    # Optional: Add last_updated timestamp for sorting or display
    last_updated: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


# Request model for sending a new message to an existing chat
class NewChatMessageRequest(BaseModel):
    query: str
    # Client might send recent history for context, but backend will typically load full history
    # This is optional and its usage depends on API design choices.
    history: Optional[List[ChatMessage]] = None

# Response model after sending a new message
class NewChatMessageResponse(BaseModel):
    chat_id: str
    assistant_message: ChatMessage
    # Optionally, the server can return the full updated history
    # full_history: Optional[List[ChatMessage]] = None

# Metadata for a single chat session (used for listing chats)
class ChatMetadata(BaseModel):
    chat_id: str
    name: str
    last_updated: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    # Could add message_count or other summary info here

# Request model for renaming a chat session
class RenameChatRequest(BaseModel):
    new_name: str

# Response model for listing chats (could just be a list of ChatMetadata)
class ListChatsResponse(BaseModel):
    chats: List[ChatMetadata]

# General success/failure response for operations like delete
class SimpleStatusResponse(BaseModel):
    success: bool
    message: Optional[str] = None
