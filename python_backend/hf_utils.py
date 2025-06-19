import os
import json
from huggingface_hub import HfFileSystem, HfApi
from huggingface_hub.utils import RepositoryNotFoundError, EntryNotFoundError

# Import HF_USER_MEMORIES_DATASET_ID from agent_config
# Assuming agent_config.py is in the same directory or Python path is set up.
# For direct execution or testing hf_utils.py, this might need adjustment
# or ensure environment variables are loaded if agent_config relies on them.
try:
    from .agent_config import HF_USER_MEMORIES_DATASET_ID
except ImportError:
    # Fallback for cases where this module might be run standalone with .env loaded
    # or for easier testing if HF_USER_MEMORIES_DATASET_ID is also in os.environ
    HF_USER_MEMORIES_DATASET_ID = os.getenv("HF_USER_MEMORIES_DATASET_ID", "gm42/user_memories") # Ensure a default

fs = HfFileSystem()
api = HfApi() # For operations like deleting repositories if needed, or checking existence

# Define file paths within the HF dataset
USER_METADATA_FILENAME = "chat_metadata.json"
USER_MESSAGES_FILENAME = "all_chat_messages.json"

def _get_user_data_path(user_id: str, filename: str) -> str:
    """Constructs the path to a user's data file on HF Hub."""
    return f"datasets/{HF_USER_MEMORIES_DATASET_ID}/{user_id}/{filename}"

def _ensure_user_directory_exists(user_id: str):
    """
    Ensures the base directory for the user exists in the HF dataset.
    This might not be strictly necessary for HfFileSystem.open if it creates paths,
    but can be useful for clarity or if other operations require directory existence.
    """
    user_dir_path = f"datasets/{HF_USER_MEMORIES_DATASET_ID}/{user_id}"
    if not fs.exists(user_dir_path):
        try:
            fs.mkdirs(user_dir_path, exist_ok=True)
            print(f"Created directory on Hugging Face Hub: {user_dir_path}")
        except Exception as e:
            print(f"Error creating directory {user_dir_path} on Hugging Face Hub: {e}")
            # Depending on fs.open behavior, this might not be a fatal error for file writing.

def load_user_data_from_hf(user_id: str) -> dict:
    """
    Loads user data (metadata and messages) from Hugging Face Hub.
    Returns a dictionary like {"metadata": {...}, "messages": {...}}.
    Initializes with empty structures if files are not found.
    """
    user_data = {"metadata": {}, "messages": {}}

    metadata_path = _get_user_data_path(user_id, USER_METADATA_FILENAME)
    messages_path = _get_user_data_path(user_id, USER_MESSAGES_FILENAME)

    try:
        if fs.exists(metadata_path):
            with fs.open(metadata_path, "r") as f:
                user_data["metadata"] = json.load(f)
        else:
            print(f"Metadata file not found for user {user_id} at {metadata_path}. Initializing empty.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {metadata_path} for user {user_id}: {e}. Initializing empty.")
    except Exception as e:
        print(f"Unexpected error loading metadata from {metadata_path} for user {user_id}: {e}. Initializing empty.")

    try:
        if fs.exists(messages_path):
            with fs.open(messages_path, "r") as f:
                user_data["messages"] = json.load(f)
        else:
            print(f"Messages file not found for user {user_id} at {messages_path}. Initializing empty.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {messages_path} for user {user_id}: {e}. Initializing empty.")
    except Exception as e:
        print(f"Unexpected error loading messages from {messages_path} for user {user_id}: {e}. Initializing empty.")

    return user_data

def save_chat_history_to_hf(user_id: str, all_user_messages: dict):
    """
    Saves the entire collection of a user's chat messages to HF Hub.
    `all_user_messages` is a dict where keys are chat_ids and values are lists of messages.
    """
    messages_path = _get_user_data_path(user_id, USER_MESSAGES_FILENAME)
    _ensure_user_directory_exists(user_id) # Ensure base path exists

    try:
        with fs.open(messages_path, "w") as f:
            json.dump(all_user_messages, f, indent=2)
        print(f"Chat history for user {user_id} saved to {messages_path}")
    except Exception as e:
        print(f"Error saving chat history for user {user_id} to {messages_path}: {e}")

def save_chat_metadata_to_hf(user_id: str, chat_metadata: dict):
    """Saves the user's chat metadata (index of chats) to HF Hub."""
    metadata_path = _get_user_data_path(user_id, USER_METADATA_FILENAME)
    _ensure_user_directory_exists(user_id) # Ensure base path exists

    try:
        with fs.open(metadata_path, "w") as f:
            json.dump(chat_metadata, f, indent=2)
        print(f"Chat metadata for user {user_id} saved to {metadata_path}")
    except Exception as e:
        print(f"Error saving chat metadata for user {user_id} to {metadata_path}: {e}")

def delete_chat_from_hf(user_id: str, chat_id: str, all_user_messages: dict, chat_metadata: dict):
    """
    Deletes a specific chat session (both messages and its metadata entry) from HF Hub.
    Updates are made to the passed-in dicts, then these full structures are re-saved.
    """
    if chat_id in all_user_messages:
        del all_user_messages[chat_id]
        save_chat_history_to_hf(user_id, all_user_messages) # Save updated messages dict
    else:
        print(f"Chat ID {chat_id} not found in messages for user {user_id}. No messages deleted from HF.")

    if chat_id in chat_metadata:
        del chat_metadata[chat_id]
        save_chat_metadata_to_hf(user_id, chat_metadata) # Save updated metadata dict
    else:
        print(f"Chat ID {chat_id} not found in metadata for user {user_id}. No metadata entry deleted from HF.")

def delete_all_user_data_from_hf(user_id: str):
    """
    Deletes all data (metadata and messages files) for a given user from HF Hub.
    This effectively removes the user's folder in the dataset.
    """
    user_folder_path_on_hub = f"{user_id}" # Relative path within the dataset repo

    try:
        # HfFileSystem.rm() can delete files or directories
        # Construct the full path as seen by HfFileSystem if it's not relative to repo root
        full_user_dir_path = f"datasets/{HF_USER_MEMORIES_DATASET_ID}/{user_id}"

        if fs.exists(full_user_dir_path):
            fs.rm(full_user_dir_path, recursive=True)
            print(f"Successfully deleted all data for user {user_id} from Hugging Face Hub at {full_user_dir_path}.")
        else:
            print(f"No data found for user {user_id} on Hugging Face Hub at {full_user_dir_path}. Nothing to delete.")

    except Exception as e:
        print(f"Error deleting data for user {user_id} from Hugging Face Hub: {e}")
        # This might require more specific error handling based on HfApi/HfFileSystem capabilities

# Example usage (for testing, typically not run directly like this)
if __name__ == '__main__':
    # Ensure .env is loaded if running this directly and HF_TOKEN etc. are needed by HfFileSystem
    from dotenv import load_dotenv
    load_dotenv()

    print(f"Using HF Dataset ID: {HF_USER_MEMORIES_DATASET_ID}")
    test_user_id = "test_user_123"

    # Test loading (will likely be empty first time)
    user_data = load_user_data_from_hf(test_user_id)
    print(f"Loaded data for {test_user_id}: {user_data}")

    # Test saving metadata
    user_data["metadata"]["chat1"] = {"name": "Test Chat 1", "last_updated": "today"}
    user_data["metadata"]["chat2"] = {"name": "Test Chat 2", "last_updated": "yesterday"}
    save_chat_metadata_to_hf(test_user_id, user_data["metadata"])

    # Test saving messages
    user_data["messages"]["chat1"] = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
    save_chat_history_to_hf(test_user_id, user_data["messages"])

    # Re-load to verify
    loaded_data_after_save = load_user_data_from_hf(test_user_id)
    print(f"Reloaded data for {test_user_id} after save: {loaded_data_after_save}")

    # Test deleting a chat
    # delete_chat_from_hf(test_user_id, "chat2", loaded_data_after_save["messages"], loaded_data_after_save["metadata"])
    # reloaded_after_delete_one = load_user_data_from_hf(test_user_id)
    # print(f"Reloaded data for {test_user_id} after deleting chat2: {reloaded_after_delete_one}")

    # Test deleting all user data (use with caution)
    # delete_all_user_data_from_hf(test_user_id)
    # reloaded_after_delete_all = load_user_data_from_hf(test_user_id)
    # print(f"Reloaded data for {test_user_id} after deleting all: {reloaded_after_delete_all}")
