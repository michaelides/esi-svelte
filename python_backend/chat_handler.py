import uuid
import re
import datetime
import asyncio # Added for simulated streaming
from typing import List, Dict, Tuple, Optional, AsyncGenerator

# LlamaIndex specific imports
from llama_index.core.llms import ChatMessage as LlamaChatMessage
from llama_index.core.llms import MessageRole as LlamaMessageRole
from llama_index.core.agent import AgentRunner

# Project-specific imports
from .chat_models import ChatMessage, ChatSession, ChatMetadata
from .agent_config import MAX_CHAT_HISTORY_MESSAGES, SUGGESTED_PROMPT_COUNT
from .agent_core import generate_llm_greeting as core_generate_llm_greeting
from .agent_core import DEFAULT_PROMPTS as CORE_DEFAULT_PROMPTS
from .hf_utils import (
    load_user_data_from_hf,
    save_chat_history_to_hf,
    save_chat_metadata_to_hf,
    # delete_chat_from_hf # Not used directly in this file by modified logic
)

def format_llama_chat_history(messages: List[ChatMessage]) -> List[LlamaChatMessage]:
    llama_history = []
    for msg in messages:
        role = LlamaMessageRole.USER if msg.role == "user" else LlamaMessageRole.ASSISTANT
        llama_history.append(LlamaChatMessage(role=role, content=msg.content))

    if len(llama_history) > MAX_CHAT_HISTORY_MESSAGES:
        llama_history = llama_history[-MAX_CHAT_HISTORY_MESSAGES:]
    return llama_history

# This is the original non-streaming version
def get_agent_chat_response(
    agent_runner: AgentRunner,
    query: str,
    history: List[LlamaChatMessage],
    # Verbosity and temperature are assumed to be set on the agent/LLM instance
    # verbosity_level: int, # Example if needed to prepend to query
    # temperature_val: float # Example if LLM needs it per call
) -> str:
    if not agent_runner:
        print("Error: Agent runner is not available.")
        return "I'm sorry, but I'm currently unable to process your request."
    try:
        # Example: Prepend verbosity to query if agent handles it this way
        # query_with_verbosity = f"Verbosity Level: {verbosity_level}. {query}"
        response = agent_runner.chat(query, chat_history=history) # Using original query
        return str(response)
    except Exception as e:
        print(f"Error getting agent chat response: {e}")
        # Log the full error for debugging:
        # import traceback
        # print(traceback.format_exc())
        return "I encountered an error trying to process your request. Please try again."

# New streaming function (simulated)
async def get_agent_chat_response_stream(
    agent_runner: AgentRunner,
    query: str,
    history: List[LlamaChatMessage],
    verbosity_level: int, # Keep for consistency, though simulation won't use it directly
    temperature_val: float # Keep for consistency
) -> AsyncGenerator[str, None]:
    """
    Simulates streaming by breaking up the response from the non-streaming method.
    Yields words of the response.
    """
    # Get the full response using the existing non-streaming function.
    # The actual LLM call happens here.
    full_response_text = get_agent_chat_response(agent_runner, query, history) # Original call

    words = full_response_text.split(" ")
    for i, word in enumerate(words):
        # Yield the word, adding a space unless it's the last word or empty.
        yield word + (" " if i < len(words) - 1 and word else "")
        await asyncio.sleep(0.05) # Simulate network delay/processing time for each token/word

def load_user_chats(user_id: str, ltm_enabled: bool) -> Tuple[Dict[str, ChatMetadata], Dict[str, List[ChatMessage]]]:
    if not ltm_enabled:
        return {}, {}
    user_hf_data = load_user_data_from_hf(user_id)

    parsed_metadata = {}
    if isinstance(user_hf_data.get("metadata"), dict):
        for chat_id, meta_dict in user_hf_data["metadata"].items():
            if isinstance(meta_dict, dict):
                 parsed_metadata[chat_id] = ChatMetadata(**meta_dict)
            elif isinstance(meta_dict, ChatMetadata):
                 parsed_metadata[chat_id] = meta_dict

    parsed_messages_data = {}
    if isinstance(user_hf_data.get("messages"), dict):
        for chat_id, msg_list_dicts in user_hf_data["messages"].items():
            if isinstance(msg_list_dicts, list):
                try:
                    parsed_messages_data[chat_id] = [ChatMessage(**msg_dict) for msg_dict in msg_list_dicts if isinstance(msg_dict, dict)]
                except Exception as e:
                    print(f"Error parsing messages for chat {chat_id} for user {user_id}: {e}. Skipping this chat's messages.")
                    parsed_messages_data[chat_id] = [] # Provide empty list on error for this chat

    return parsed_metadata, parsed_messages_data

def _generate_chat_name(user_query: str, existing_names: List[str]) -> str:
    words = re.findall(r'\b\w+\b', user_query.lower())
    base_name = " ".join(words[:4]).capitalize()
    if not base_name: base_name = "New Chat"
    name, counter = base_name, 1
    while name in existing_names:
        name = f"{base_name} ({counter})"
        counter += 1
    return name

def create_new_chat_session(
    user_id: str,
    chat_metadata_index: Dict[str, ChatMetadata],
    all_user_chat_messages: Dict[str, List[ChatMessage]],
    ltm_enabled: bool,
    first_user_query: Optional[str] = None
) -> ChatSession:
    new_chat_id = str(uuid.uuid4())
    existing_chat_names = [meta.name for meta in chat_metadata_index.values()]
    chat_name_query = first_user_query if first_user_query else "General Discussion"
    new_chat_name = _generate_chat_name(chat_name_query, existing_chat_names)

    assistant_greeting_content = core_generate_llm_greeting()
    initial_message = ChatMessage(role="assistant", content=assistant_greeting_content)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_session = ChatSession(
        chat_id=new_chat_id, name=new_chat_name, messages=[initial_message], last_updated=now_iso
    )

    chat_metadata_index[new_chat_id] = ChatMetadata(
        chat_id=new_chat_id, name=new_chat_name, last_updated=now_iso
    )
    all_user_chat_messages[new_chat_id] = new_session.messages

    if ltm_enabled:
        save_chat_metadata_to_hf(user_id, {k: v.model_dump() for k, v in chat_metadata_index.items()})
        save_chat_history_to_hf(user_id, {k: [m.model_dump() for m in v_list] for k, v_list in all_user_chat_messages.items()})
    return new_session

# This function is for the NON-STREAMING endpoint if kept, or for internal use.
# The streaming endpoint will manage message saving differently around the stream.
def add_message_to_chat_session(
    user_id: str, chat_id: str, user_query: str,
    chat_metadata_index: Dict[str, ChatMetadata],
    all_user_chat_messages: Dict[str, List[ChatMessage]],
    agent_runner: AgentRunner, ltm_enabled: bool,
    verbosity_level: int, temperature_val: float # Added these for consistency
) -> Optional[ChatMessage]:
    if chat_id not in all_user_chat_messages or chat_id not in chat_metadata_index:
        return None

    current_chat_messages = all_user_chat_messages[chat_id]
    user_message = ChatMessage(role="user", content=user_query)
    current_chat_messages.append(user_message)

    llama_history = format_llama_chat_history(current_chat_messages[:-1])

    # Using the non-streaming response for saving.
    assistant_content = get_agent_chat_response(
        agent_runner, user_query, llama_history # Pass verbosity and temp if get_agent_chat_response uses them
    )
    assistant_message = ChatMessage(role="assistant", content=assistant_content)
    current_chat_messages.append(assistant_message)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    chat_metadata_index[chat_id].last_updated = now_iso

    if ltm_enabled:
        save_chat_history_to_hf(user_id, {k: [m.model_dump() for m in v_list] for k, v_list in all_user_chat_messages.items()})
        save_chat_metadata_to_hf(user_id, {k: v.model_dump() for k, v in chat_metadata_index.items()})
    return assistant_message

def rename_chat_session_logic(
    user_id: str, chat_id: str, new_name: str,
    chat_metadata_index: Dict[str, ChatMetadata], ltm_enabled: bool
) -> Optional[ChatMetadata]:
    if chat_id not in chat_metadata_index: return None

    chat_metadata_index[chat_id].name = new_name
    chat_metadata_index[chat_id].last_updated = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if ltm_enabled:
        save_chat_metadata_to_hf(user_id, {k: v.model_dump() for k, v in chat_metadata_index.items()})
    return chat_metadata_index[chat_id]

def delete_chat_session_logic(
    user_id: str, chat_id: str,
    all_user_chat_messages: Dict[str, List[ChatMessage]],
    chat_metadata_index: Dict[str, ChatMetadata], ltm_enabled: bool
) -> bool:
    chat_found = False
    if chat_id in all_user_chat_messages:
        del all_user_chat_messages[chat_id]
        chat_found = True
    if chat_id in chat_metadata_index:
        del chat_metadata_index[chat_id]
        chat_found = True

    if ltm_enabled and chat_found: # Only save if something was actually deleted locally
        save_chat_history_to_hf(user_id, {k: [m.model_dump() for m in v_list] for k, v_list in all_user_chat_messages.items()})
        save_chat_metadata_to_hf(user_id, {k: v.model_dump() for k, v in chat_metadata_index.items()})
    return chat_found
