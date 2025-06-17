import uuid

import json
import asyncio
import datetime
import os # Added for os.makedirs
from fastapi import FastAPI, Request, Response, Cookie, HTTPException, Path, Body, UploadFile, File # Added UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple

import uvicorn

# Agent module imports
from .agent_config import ( # Grouped imports
    initialize_settings as agent_initialize_settings,
    update_llm_temperature,
    get_llm_temperature,
    MAX_CHAT_HISTORY_MESSAGES,
    UI_ACCESSIBLE_WORKSPACE # Added UI_ACCESSIBLE_WORKSPACE
)
from .agent_core import create_orchestrator_agent, generate_llm_greeting as core_generate_llm_greeting

# Chat module imports
from .chat_models import (
    ChatMessage, ChatSession, NewChatMessageRequest, NewChatMessageResponse,
    ChatMetadata, RenameChatRequest, ListChatsResponse, SimpleStatusResponse
)
import python_backend.chat_handler as chat_handler

# File module imports
import python_backend.file_handler as file_handler # Added
from .file_handler import FileProcessDetail, UploadedFileRecord # Added specific model imports

app = FastAPI()

# --- Constants for Cookies ---
USER_ID_COOKIE = "esi_user_id"
LTM_PREF_COOKIE = "esi_ltm_pref"

# --- Models ---
class LLMSettings(BaseModel):
    temperature: float = 0.7
    verbosity: int = 3
    search_results_count: int = 5
    long_term_memory_enabled: bool = True

class InitResponse(BaseModel):
    user_id: str
    settings: LLMSettings
    greeting: str

# --- Global State ---
app_level_settings = LLMSettings()
app.state.agent_runner = None
app.state.user_chat_data_cache: Dict[str, Dict[str, Dict]] = {}

# --- Cookie Helper ---
def set_persistent_cookie(response: Response, key: str, value: str, days: int = 365):
    response.set_cookie(
        key=key, value=value, max_age=days * 24 * 60 * 60,
        httponly=True, samesite="lax", path="/"
    )

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI app startup: Initializing LlamaIndex global settings...")
    agent_initialize_settings(temperature=app_level_settings.temperature)

    # Ensure UI_ACCESSIBLE_WORKSPACE exists
    try:
        os.makedirs(UI_ACCESSIBLE_WORKSPACE, exist_ok=True)
        print(f"User uploaded files workspace ensured at: {UI_ACCESSIBLE_WORKSPACE}")
    except Exception as e:
        print(f"Error creating UI_ACCESSIBLE_WORKSPACE at {UI_ACCESSIBLE_WORKSPACE}: {e}")

    print("FastAPI app started. LlamaIndex global settings initialized.")

# --- User Chat Data Cache Helper ---
def get_user_chat_data_from_cache_or_load(user_id: str, ltm_enabled: bool) -> Tuple[Dict[str, ChatMetadata], Dict[str, List[ChatMessage]]]:
    if ltm_enabled and user_id in app.state.user_chat_data_cache:
        cached_data = app.state.user_chat_data_cache[user_id]
        parsed_metadata = {k: (v if isinstance(v, ChatMetadata) else ChatMetadata(**v)) for k, v in cached_data.get("metadata", {}).items()}
        parsed_messages = {}
        for chat_id_key, msg_list in cached_data.get("messages", {}).items():
            parsed_messages[chat_id_key] = [(m if isinstance(m, ChatMessage) else ChatMessage(**m)) for m in msg_list]
        return parsed_metadata, parsed_messages

    metadata, messages_data = chat_handler.load_user_chats(user_id, ltm_enabled)
    if ltm_enabled:
        app.state.user_chat_data_cache[user_id] = {"metadata": metadata, "messages": messages_data}
    return metadata, messages_data

# --- API Endpoints (Init, Settings, Root) ---
@app.post("/api/init", response_model=InitResponse)
async def initialize_session(request: Request, response: Response):
    user_id = request.cookies.get(USER_ID_COOKIE)
    new_user_flag = False
    if not user_id:
        user_id = str(uuid.uuid4())
        new_user_flag = True
        set_persistent_cookie(response, USER_ID_COOKIE, user_id)

    ltm_pref_cookie_val = request.cookies.get(LTM_PREF_COOKIE)
    if ltm_pref_cookie_val is not None:
        app_level_settings.long_term_memory_enabled = ltm_pref_cookie_val.lower() == 'true'
    elif new_user_flag:
        set_persistent_cookie(response, LTM_PREF_COOKIE, str(app_level_settings.long_term_memory_enabled))

    agent_initialize_settings(temperature=app_level_settings.temperature)
    if app.state.agent_runner is None:
        app.state.agent_runner = create_orchestrator_agent()

    greeting = core_generate_llm_greeting()
    app_level_settings.temperature = get_llm_temperature()
    return InitResponse(user_id=user_id, settings=app_level_settings, greeting=greeting)

@app.get("/api/settings", response_model=LLMSettings)
async def get_app_settings_endpoint():
    app_level_settings.temperature = get_llm_temperature()
    return app_level_settings

@app.post("/api/settings", response_model=LLMSettings)
async def update_app_settings_endpoint(settings: LLMSettings, response: Response):
    global app_level_settings
    if app_level_settings.long_term_memory_enabled != settings.long_term_memory_enabled:
        set_persistent_cookie(response, LTM_PREF_COOKIE, str(settings.long_term_memory_enabled))

    app_level_settings = settings
    update_llm_temperature(app_level_settings.temperature)
    app_level_settings.temperature = get_llm_temperature()
    return app_level_settings

@app.get("/")
async def read_root():
    return {"message": "ESI Backend is running with Chat and File Endpoints"}

# --- Chat Management Endpoints ---
@app.get("/api/chats", response_model=ListChatsResponse)
async def list_user_chats(user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)):
    if not user_id: raise HTTPException(status_code=401, detail="User ID not found.")
    chat_metadata_index, _ = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    return ListChatsResponse(chats=list(chat_metadata_index.values()))

@app.post("/api/chats", response_model=ChatSession)
async def create_new_chat_endpoint(request: Request, user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)):
    if not user_id: raise HTTPException(status_code=401, detail="User ID not found.")
    first_query: Optional[str] = None
    try: body = await request.json(); first_query = body.get("first_query")
    except: pass
    chat_metadata_index, all_user_chat_messages = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    new_chat = chat_handler.create_new_chat_session(
        user_id, chat_metadata_index, all_user_chat_messages, app_level_settings.long_term_memory_enabled, first_query
    )
    app.state.user_chat_data_cache[user_id] = {"metadata": chat_metadata_index, "messages": all_user_chat_messages}
    return new_chat

@app.get("/api/chats/{chat_id}", response_model=ChatSession)
async def get_specific_chat_session(chat_id: str = Path(...), user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)):
    if not user_id: raise HTTPException(status_code=401, detail="User ID not found.")
    chat_metadata_index, all_user_chat_messages = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    if chat_id not in chat_metadata_index or chat_id not in all_user_chat_messages:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return ChatSession(
        chat_id=chat_id, name=chat_metadata_index[chat_id].name,
        messages=all_user_chat_messages[chat_id], last_updated=chat_metadata_index[chat_id].last_updated
    )

@app.post("/api/chats/{chat_id}/message", response_model=NewChatMessageResponse)
async def post_message_to_chat(
    chat_id: str = Path(...), request_body: NewChatMessageRequest = Body(...),
    user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)
):
    if not user_id: raise HTTPException(status_code=401, detail="User ID not found.")
    if not app.state.agent_runner: raise HTTPException(status_code=503, detail="Agent unavailable.")
    chat_metadata_index, all_user_chat_messages = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    if chat_id not in chat_metadata_index: raise HTTPException(status_code=404, detail="Chat not found.")

    assistant_msg_obj = chat_handler.add_message_to_chat_session(
        user_id, chat_id, request_body.query, chat_metadata_index, all_user_chat_messages,
        app.state.agent_runner, app_level_settings.long_term_memory_enabled,
        app_level_settings.verbosity, app_level_settings.temperature
    )
    if not assistant_msg_obj: raise HTTPException(status_code=500, detail="Assistant response failed.")
    app.state.user_chat_data_cache[user_id] = {"metadata": chat_metadata_index, "messages": all_user_chat_messages}
    return NewChatMessageResponse(chat_id=chat_id, assistant_message=assistant_msg_obj)

@app.post("/api/chats/{chat_id}/message_stream")
async def stream_chat_message(
    chat_id: str = Path(...), request_data: NewChatMessageRequest = Body(...),
    user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE),
):
    if not user_id: raise HTTPException(status_code=401, detail="User not authenticated.")
    if not app.state.agent_runner: raise HTTPException(status_code=503, detail="Agent is not available.")
    chat_metadata_index, all_user_chat_messages = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    if chat_id not in all_user_chat_messages or chat_id not in chat_metadata_index:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    current_chat_messages = all_user_chat_messages[chat_id]
    user_api_message = ChatMessage(role="user", content=request_data.query)
    current_chat_messages.append(user_api_message)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    chat_metadata_index[chat_id].last_updated = now_iso
    if app_level_settings.long_term_memory_enabled:
        chat_handler.save_chat_history_to_hf(user_id, {k: [m.model_dump() for m in v_list] for k, v_list in all_user_chat_messages.items()})
        chat_handler.save_chat_metadata_to_hf(user_id, {k: v.model_dump() for k, v in chat_metadata_index.items()})
    app.state.user_chat_data_cache[user_id] = {"metadata": chat_metadata_index, "messages": all_user_chat_messages}

    llama_history = chat_handler.format_llama_chat_history(current_chat_messages)
    async def event_generator():
        full_assistant_response = ""
        try:
            stream = chat_handler.get_agent_chat_response_stream(
                app.state.agent_runner, request_data.query, llama_history,
                app_level_settings.verbosity, app_level_settings.temperature
            )
            async for chunk in stream:
                full_assistant_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'eos'})}\n\n"
        except Exception as e:
            print(f"Error during stream generation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            return
        if full_assistant_response.strip():
            assistant_api_message = ChatMessage(role="assistant", content=full_assistant_response)
            current_chat_messages.append(assistant_api_message)
            chat_metadata_index[chat_id].last_updated = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if app_level_settings.long_term_memory_enabled:
                chat_handler.save_chat_history_to_hf(user_id, {k: [m.model_dump() for m in v_list] for k, v_list in all_user_chat_messages.items()})
                chat_handler.save_chat_metadata_to_hf(user_id, {k: v.model_dump() for k, v in chat_metadata_index.items()})
            app.state.user_chat_data_cache[user_id] = {"metadata": chat_metadata_index, "messages": all_user_chat_messages}
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.put("/api/chats/{chat_id}", response_model=ChatMetadata)
async def rename_chat_endpoint(
    chat_id: str = Path(...), request_body: RenameChatRequest = Body(...),
    user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)
):
    if not user_id: raise HTTPException(status_code=401, detail="User ID not found.")
    chat_metadata_index, _ = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    updated_metadata = chat_handler.rename_chat_session_logic(
        user_id, chat_id, request_body.new_name, chat_metadata_index, app_level_settings.long_term_memory_enabled
    )
    if not updated_metadata: raise HTTPException(status_code=404, detail="Chat not found for renaming.")
    app.state.user_chat_data_cache.setdefault(user_id, {"metadata": {}, "messages": {}})["metadata"] = chat_metadata_index
    return updated_metadata

@app.delete("/api/chats/{chat_id}", response_model=SimpleStatusResponse)
async def delete_chat_endpoint(
    chat_id: str = Path(...), user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)
):
    if not user_id: raise HTTPException(status_code=401, detail="User ID not found.")
    chat_metadata_index, all_user_chat_messages = get_user_chat_data_from_cache_or_load(user_id, app_level_settings.long_term_memory_enabled)
    success = chat_handler.delete_chat_session_logic(
        user_id, chat_id, all_user_chat_messages, chat_metadata_index, app_level_settings.long_term_memory_enabled
    )
    app.state.user_chat_data_cache[user_id] = {"metadata": chat_metadata_index, "messages": all_user_chat_messages}
    return SimpleStatusResponse(success=success, message=f"Delete operation for chat {chat_id} processed.")

# --- File Management Endpoints ---
@app.post("/api/files/upload", response_model=FileProcessDetail)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in cookies.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    # Process and register the file
    process_detail = file_handler.process_and_register_uploaded_file(user_id, file)

    if process_detail.status == "error":
        raise HTTPException(status_code=500, detail=process_detail.message or "File processing failed.")

    return process_detail

@app.get("/api/files", response_model=List[UploadedFileRecord])
async def list_files_endpoint(user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)):
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in cookies.")
    return file_handler.list_uploaded_files_for_user(user_id)

@app.delete("/api/files/{filename}", response_model=SimpleStatusResponse)
async def delete_file_endpoint(
    filename: str = Path(...),
    user_id: Optional[str] = Cookie(None, alias=USER_ID_COOKIE)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in cookies.")

    success = file_handler.delete_uploaded_file(user_id, filename)
    if not success:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found or delete failed.")
    return SimpleStatusResponse(success=True, message=f"File '{filename}' deleted successfully.")

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
