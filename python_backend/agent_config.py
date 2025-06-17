import os
from llama_index.core import Settings
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.llms import LLM # For type hinting
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# PROJECT_ROOT for agent_config.py will be the 'python_backend' directory.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# --- File System Paths ---
# Workspace for files uploaded by the user via UI, accessible by FastAPI and potentially agent tools
UI_ACCESSIBLE_WORKSPACE_RELATIVE = "user_uploaded_files"
# This path will be /app/python_backend/user_uploaded_files
UI_ACCESSIBLE_WORKSPACE = os.path.join(PROJECT_ROOT, UI_ACCESSIBLE_WORKSPACE_RELATIVE)

# Workspace for Code Interpreter (if different) - can be defined later if needed
# CODE_INTERPRETER_WORKSPACE_RELATIVE = "code_interpreter_ws"
# CODE_INTERPRETER_WORKSPACE = os.path.join(PROJECT_ROOT, CODE_INTERPRETER_WORKSPACE_RELATIVE)


# --- Constants ---
SUGGESTED_PROMPT_COUNT = 4
MAX_CHAT_HISTORY_MESSAGES = 20 # Max messages to send to LLM from history

# --- Hugging Face Configuration for User Data ---
HF_USER_MEMORIES_DATASET_ID = os.getenv("HF_USER_MEMORIES_DATASET_ID", "gm42/user_memories")

# --- Global Settings ---
_settings_initialized = False

current_api_llm_settings = {
    "temperature": 0.7,
}

def initialize_settings(temperature: float = 0.7):
    global _settings_initialized
    if _settings_initialized:
        # print("Settings already initialized.") # Reduce noise
        return

    print(f"Initializing LLM and Embedding models settings with temperature: {temperature}...")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    Settings.embed_model = GoogleGenAIEmbedding(model_name="models/text-embedding-004", api_key=google_api_key)
    Settings.llm = Gemini(
        model_name="models/gemini-1.5-flash-latest",
        api_key=google_api_key,
        temperature=temperature
    )
    _settings_initialized = True
    current_api_llm_settings['temperature'] = temperature
    print("LLM and Embedding models settings initialized successfully.")

def get_llm_temperature() -> float:
    if Settings.llm and hasattr(Settings.llm, 'temperature'):
        return Settings.llm.temperature
    return current_api_llm_settings['temperature']

def update_llm_temperature(temperature: float):
    current_api_llm_settings['temperature'] = temperature
    if Settings.llm and hasattr(Settings.llm, 'temperature'):
        Settings.llm.temperature = temperature
        print(f"LLM temperature updated to: {temperature}")
    else:
        print("LLM not yet initialized or temperature attribute not found. Storing temperature for next initialization.")

# Other API keys from original config.py could be centralized here if needed by multiple backend modules
# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# HF_TOKEN = os.getenv("HF_TOKEN")
