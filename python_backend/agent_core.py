import os
from llama_index.core import Settings
from llama_index.core.agent import AgentRunner, FunctionCallingAgentWorker
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import LLM
from typing import Any, List, Dict, Optional

# Assuming agent_config.py is in the same directory (python_backend)
from .agent_config import initialize_settings, SUGGESTED_PROMPT_COUNT, PROJECT_ROOT, get_llm_temperature, update_llm_temperature

# --- STUBBED TOOLS (to be replaced by actual tools from tools.py later) ---
# These stubs ensure create_orchestrator_agent can be called without full tool implementations.
def get_search_tools() -> List[FunctionTool]:
    print("STUB: get_search_tools called, returning empty list.")
    return []

def get_semantic_scholar_tool_for_agent() -> Optional[FunctionTool]:
    print("STUB: get_semantic_scholar_tool_for_agent called, returning None.")
    return None

def get_web_scraper_tool_for_agent() -> Optional[FunctionTool]:
    print("STUB: get_web_scraper_tool_for_agent called, returning None.")
    return None

def get_rag_tool_for_agent() -> Optional[FunctionTool]:
    print("STUB: get_rag_tool_for_agent called, returning None.")
    return None

def get_coder_tools() -> List[FunctionTool]:
    print("STUB: get_coder_tools called, returning empty list.")
    return []
# --- END STUBBED TOOLS ---

# --- Default Prompts (from agent.py) ---
DEFAULT_PROMPTS = [
    "Help me brainstorm ideas.",
    "I need to develop my research questions.",
    "I have my topic and I need help with developing hypotheses.",
    "I have my hypotheses and I need help to design the study.",
    "Can you help me design my qualitative study?"
]

# --- Greeting Generation (from agent.py, adapted) ---
def generate_llm_greeting() -> str:
    """Generates a dynamic greeting message using the configured LLM."""
    static_fallback = "Hello! I'm ESI, your AI assistant for dissertation support. How can I help you today?"
    try:
        if not Settings.llm: # Check if LlamaIndex global Settings.llm is initialized
            print("generate_llm_greeting: Settings.llm not found, calling initialize_settings.")
            initialize_settings(temperature=get_llm_temperature()) # Use current/default temp

        llm = Settings.llm
        if not isinstance(llm, LLM):
             print("Warning: LLM not configured correctly for greeting generation. Falling back.")
             return static_fallback

        prompt = "Generate a short, friendly greeting (1-2 sentences) for ESI, an AI dissertation assistant. Mention ESI by name and offer help. Provide only the greeting."
        response = llm.complete(prompt)
        greeting = response.text.strip()

        if not greeting or len(greeting) < 10:
            print("Warning: LLM generated an empty or too short greeting. Falling back.")
            return static_fallback

        print(f"Generated LLM Greeting: {greeting}")
        return greeting
    except Exception as e:
        print(f"Error generating LLM greeting: {e}. Falling back to static message.")
        return static_fallback

# --- Comprehensive Agent Definition (from agent.py, adapted) ---
def create_orchestrator_agent(dynamic_tools: List[FunctionTool] = None, max_search_results: int = 10) -> AgentRunner:
    """
    Creates a single comprehensive agent that has access to all specialized tools (currently stubbed).
    Adapted from agent.py.
    """
    if not Settings.llm: # Check if LlamaIndex global Settings.llm is initialized
        print("create_orchestrator_agent: Settings.llm not found, calling initialize_settings.")
        initialize_settings(temperature=get_llm_temperature())

    print("Initializing STUBBED tools for the comprehensive agent...")

    search_tools = get_search_tools()
    lit_reviewer_tool = get_semantic_scholar_tool_for_agent()
    web_scraper_tool = get_web_scraper_tool_for_agent()
    rag_tool = get_rag_tool_for_agent()
    coder_tools = get_coder_tools()

    all_tools = []
    if search_tools: all_tools.extend(search_tools)
    if lit_reviewer_tool: all_tools.append(lit_reviewer_tool)
    if web_scraper_tool: all_tools.append(web_scraper_tool)
    if rag_tool: all_tools.append(rag_tool)
    if coder_tools: all_tools.extend(coder_tools)

    if dynamic_tools:
        all_tools.extend(dynamic_tools)

    if not all_tools:
        # This is expected with stubs that return empty lists or None
        print("Warning: No tools could be initialized for the comprehensive agent (stubs returned empty/None). Agent will have limited functionality.")

    # Path for esi_agent_instruction.md. PROJECT_ROOT from agent_config is python_backend dir.
    # So, os.path.dirname(PROJECT_ROOT) is the actual project root (/app).
    instruction_path = os.path.join(os.path.dirname(PROJECT_ROOT), "esi_agent_instruction.md")

    try:
        with open(instruction_path, "r") as f:
             system_prompt_base = f.read().strip()
    except FileNotFoundError:
        print(f"Warning: System instruction file '{instruction_path}' not found. Using default base prompt for the comprehensive agent.")
        system_prompt_base = "You are ESI, an AI assistant for dissertation support."

    # System prompt content from agent.py (simplified for brevity here, but full content in actual use)
    comprehensive_system_prompt = f"""{system_prompt_base}
Your role is to understand the user's query and use the available tools to gather information, perform tasks, and synthesize a comprehensive final answer.
Verbosity Control: Check for 'Verbosity Level: X.' (1-5). Default 3.
You have access to the following tools (currently STUBBED): Search, Literature Review, Web Scraper, RAG, Coder, read_uploaded_document, analyze_uploaded_dataframe.
Your process: Analyze, select tool(s), formulate inputs, call tool(s), review responses, synthesize final answer.
Include specific markers from tools in your response: ---RAG_SOURCE---{{...}}, ---DOWNLOAD_FILE---filename.ext, and Python code blocks.
Be proactive and thorough. Cite sources. Acknowledge tool errors.
Focus on delivering the answer for the current query. Avoid conversational filler about chat history. Never use "Ah".
"""

    comprehensive_agent_worker = FunctionCallingAgentWorker.from_tools(
        tools=all_tools, # Will be empty or minimal due to stubs
        llm=Settings.llm,
        system_prompt=comprehensive_system_prompt,
        verbose=True,
    )
    comprehensive_agent_runner = AgentRunner(comprehensive_agent_worker)
    print("Comprehensive agent created with STUBBED tools.")
    return comprehensive_agent_runner

# --- Suggested Prompts (from agent.py, adapted) ---
def generate_suggested_prompts(chat_history: List[Dict[str, Any]]) -> List[str]:
    """Generates concise suggested prompts based on chat history."""
    try:
        if not Settings.llm:
            print("generate_suggested_prompts: Settings.llm not found, calling initialize_settings.")
            initialize_settings(temperature=get_llm_temperature())

        llm = Settings.llm
        if not llm:
            print("Critical Warning: LLM is None even after initialization attempt in generate_suggested_prompts. Falling back to defaults.")
            return DEFAULT_PROMPTS

        last_assistant_message_content = ""
        for message in reversed(chat_history):
            if message["role"] == "assistant":
                last_assistant_message_content = message["content"]
                break

        context_messages = chat_history[-4:]
        context_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in context_messages])

        prompt = f"""Based on the recent conversation context, and especially focusing on the last assistant's reply, suggest exactly {SUGGESTED_PROMPT_COUNT} concise follow-up prompts (under 15 words each) for a user working on a dissertation.
These prompts should be questions a student might ask their dissertation supervisor about *their own* research, progress, or challenges, directly building upon the last assistant's response.
Do NOT generate prompts that ask the supervisor about their own work, or ask the supervisor to write content for the student.
Output ONLY the prompts, each on a new line, without numbering or introductory text.

Last Assistant's Reply:
{last_assistant_message_content}

Conversation Context (for broader understanding):
{context_str}
"""
        print("Generating suggested prompts using LLM...")
        response = llm.complete(prompt)
        suggestions_text = response.text.strip()
        suggested_prompts = [line.strip() for line in suggestions_text.split('\n') if line.strip()]

        if len(suggested_prompts) == SUGGESTED_PROMPT_COUNT and all(suggested_prompts):
            print(f"LLM generated prompts: {suggested_prompts}")
            return suggested_prompts
        else:
            print(f"Warning: LLM generated unexpected output for suggestions: '{suggestions_text}'. Falling back to defaults.")
            return DEFAULT_PROMPTS
    except Exception as e:
        print(f"Error generating suggested prompts with LLM: {e}. Falling back to defaults.")
        return DEFAULT_PROMPTS
