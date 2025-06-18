import os
import shutil
import re
import json
import io
import pathlib
from typing import List, Dict, Optional, Tuple, Literal

from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, Field

# Attempt to import document processing libraries
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document as DocxDocument # Alias to avoid conflict with LlamaIndex Document
except ImportError:
    DocxDocument = None
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    import pyreadstat
except ImportError:
    pyreadstat = None

from .agent_config import UI_ACCESSIBLE_WORKSPACE

# --- Pydantic Models ---
class UploadedFileRecord(BaseModel):
    filename: str
    content_type: Optional[str] = None # MIME type
    size: int # In bytes
    file_type: Literal["document", "dataframe", "text", "other"]
    local_path: str # Relative path within UI_ACCESSIBLE_WORKSPACE / user_id
    summary: Optional[str] = None # e.g., text snippet or dataframe head string

    # For agent consumption
    # For documents, this holds the full extracted text.
    # For dataframes, this might be JSON representation or specific insights.
    agent_readable_content: Optional[str] = None
    # df_json: Optional[str] = None # Alternative for dataframes

class FileProcessDetail(BaseModel):
    filename: str
    status: str # e.g., "success", "error", "unsupported"
    file_type: Optional[Literal["document", "dataframe", "text", "other"]] = None
    message: Optional[str] = None
    record: Optional[UploadedFileRecord] = None

# --- In-memory State Management for Uploaded Files ---
# { user_id: {filename: UploadedFileRecord} }
# Using filename as key within user's dict for easier lookup/update
user_file_uploads: Dict[str, Dict[str, UploadedFileRecord]] = {}

# --- Helper: Sanitize filename ---
def _sanitize_filename(filename: str) -> str:
    """Removes potentially unsafe characters from a filename."""
    filename = re.sub(r"[^\w\s.-]", "_", filename) # Allow alphanumeric, whitespace, dots, hyphens
    filename = re.sub(r"\s+", "_", filename) # Replace whitespace with underscores
    return filename

# --- Core File Handling Functions ---
def _get_user_file_dir(user_id: str, ensure_exists: bool = False) -> pathlib.Path:
    """Gets the user's specific file directory path and optionally creates it."""
    user_dir = pathlib.Path(UI_ACCESSIBLE_WORKSPACE) / user_id
    if ensure_exists:
        user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def _save_uploaded_file(user_id: str, file: UploadFile) -> Tuple[pathlib.Path, int]:
    """Saves an uploaded file to the user's workspace directory."""
    if file.filename is None:
        raise HTTPException(status_code=400, detail="File has no filename.")

    safe_filename = _sanitize_filename(pathlib.Path(file.filename).name)
    user_files_path = _get_user_file_dir(user_id, ensure_exists=True)
    destination_path = user_files_path / safe_filename

    file_size = 0
    try:
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = destination_path.stat().st_size
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        file.file.close() # Ensure the spooled file is closed

    return destination_path, file_size

def _process_document_file(file_path: pathlib.Path, file_extension: str) -> Tuple[str, Optional[str]]:
    """Extracts text content from document files (.pdf, .docx, .txt, .md)."""
    text_content = ""
    file_type: Literal["document", "text"] = "document"

    try:
        if file_extension == ".pdf":
            if not PdfReader: raise ImportError("PyPDF2 is not installed.")
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text_content += page.extract_text() or ""
        elif file_extension == ".docx":
            if not DocxDocument: raise ImportError("python-docx is not installed.")
            doc = DocxDocument(file_path)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        elif file_extension in [".txt", ".md"]:
            file_type = "text" # More specific
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        else:
            return "other", None # Should not happen if called correctly
    except Exception as e:
        print(f"Error processing document {file_path}: {e}")
        return "other", f"Error processing document: {e}" # Return error as content for now

    return file_type, text_content.strip()

def _process_dataframe_file(file_path: pathlib.Path, file_extension: str) -> Tuple[str, Optional[str], Optional[pd.DataFrame]]:
    """Loads tabular data into a pandas DataFrame and returns head as summary."""
    if not pd: raise ImportError("pandas is not installed.")
    df = None
    summary = None
    try:
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".xlsx":
            if not __import__('openpyxl'): raise ImportError("openpyxl is not installed for .xlsx files.")
            df = pd.read_excel(file_path)
        elif file_extension == ".sav":
            if not pyreadstat: raise ImportError("pyreadstat is not installed for .sav files.")
            df, _ = pyreadstat.read_sav(file_path) # pyreadstat returns df and metadata

        if df is not None:
            summary = df.head().to_string()
        return "dataframe", summary, df # Return df object for potential further use (not directly in UploadedFileRecord)
    except Exception as e:
        print(f"Error processing dataframe {file_path}: {e}")
        return "dataframe", f"Error processing dataframe: {e}", None


def process_and_register_uploaded_file(user_id: str, file: UploadFile) -> FileProcessDetail:
    """Main function to save, process, and register an uploaded file."""
    if file.filename is None: # Should be caught by _save_uploaded_file but good for early exit
        return FileProcessDetail(filename="unknown", status="error", message="File has no filename.")

    original_filename = file.filename

    try:
        saved_path, file_size = _save_uploaded_file(user_id, file)
        file_extension = saved_path.suffix.lower()

        # Relative path for storage in record (user_id/filename.ext)
        relative_path = f"{user_id}/{saved_path.name}"

        file_type: Literal["document", "dataframe", "text", "other"] = "other"
        summary: Optional[str] = None
        agent_content: Optional[str] = None
        # actual_df_for_tools: Optional[pd.DataFrame] = None # Not stored in record directly

        if file_extension in [".pdf", ".docx", ".txt", ".md"]:
            _type, text_content = _process_document_file(saved_path, file_extension)
            file_type = _type # document or text
            if text_content and not text_content.startswith("Error processing document"):
                summary = (text_content[:200] + "...") if len(text_content) > 200 else text_content
                agent_content = text_content
            else: # Content is an error message or empty
                summary = text_content if text_content else "Could not extract text."
        elif file_extension in [".csv", ".xlsx", ".sav"]:
            if not pd: # Check if pandas is available before claiming it's a dataframe
                return FileProcessDetail(filename=original_filename, status="error", message="Pandas library not available for dataframe processing.")
            _type, df_summary, _ = _process_dataframe_file(saved_path, file_extension)
            file_type = _type # dataframe
            summary = df_summary if df_summary and not df_summary.startswith("Error processing dataframe") else "Could not read dataframe head."
            # For dataframes, agent_readable_content could be a JSON sample, or path.
            # For now, let's make it the path, as agent tools might load it.
            agent_content = str(saved_path) # Agent tool will use this path.

        else: # Other file types
            summary = f"File type '{file_extension}' not fully processed. Saved at server."

        record = UploadedFileRecord(
            filename=saved_path.name, # Use sanitized name
            content_type=file.content_type,
            size=file_size,
            file_type=file_type,
            local_path=relative_path, # Store relative path from UI_ACCESSIBLE_WORKSPACE
            summary=summary,
            agent_readable_content=agent_content
        )

        if user_id not in user_file_uploads:
            user_file_uploads[user_id] = {}
        user_file_uploads[user_id][record.filename] = record

        return FileProcessDetail(
            filename=original_filename, status="success", file_type=file_type, record=record
        )

    except HTTPException as he: # Re-raise HTTP exceptions from _save_uploaded_file
        return FileProcessDetail(filename=original_filename, status="error", message=he.detail)
    except ImportError as ie: # Handle missing processing libraries
        print(f"ImportError during file processing: {ie}")
        return FileProcessDetail(filename=original_filename, status="error", message=f"Processing library missing: {ie.name}. Please install it.")
    except Exception as e:
        print(f"Unhandled error processing file {original_filename}: {e}")
        # import traceback; traceback.print_exc(); # For debugging
        return FileProcessDetail(filename=original_filename, status="error", message=f"Server error processing file: {e}")


def list_uploaded_files_for_user(user_id: str) -> List[UploadedFileRecord]:
    return list(user_file_uploads.get(user_id, {}).values())

def get_uploaded_file_record(user_id: str, filename: str) -> Optional[UploadedFileRecord]:
    return user_file_uploads.get(user_id, {}).get(filename)

def delete_uploaded_file(user_id: str, filename: str) -> bool:
    user_specific_uploads = user_file_uploads.get(user_id)
    if not user_specific_uploads or filename not in user_specific_uploads:
        return False

    record_to_delete = user_specific_uploads[filename]
    # Construct full path from UI_ACCESSIBLE_WORKSPACE and record's local_path (which is user_id/filename)
    # Note: record.local_path here is relative to UI_ACCESSIBLE_WORKSPACE, not just user_id dir.
    # Correction: local_path in model is user_id/filename.ext.
    # So full path is UI_ACCESSIBLE_WORKSPACE / user_id / filename.ext
    # No, record.local_path is defined as "Path within UI_ACCESSIBLE_WORKSPACE / user_id"
    # So it's just "filename.ext" relative to the user's folder.

    # Let's clarify: `record.local_path` should be `user_id/filename.ext` as stored.
    # Or, if `_get_user_file_dir(user_id)` is the base, then `local_path` is just `filename.ext`.
    # The current `_save_uploaded_file` returns full path `destination_path`.
    # `relative_path` is `f"{user_id}/{saved_path.name}"`. This is relative to `UI_ACCESSIBLE_WORKSPACE`.
    # So, `full_physical_path = pathlib.Path(UI_ACCESSIBLE_WORKSPACE) / record.local_path`

    full_physical_path = pathlib.Path(UI_ACCESSIBLE_WORKSPACE) / record_to_delete.local_path

    try:
        if full_physical_path.exists():
            full_physical_path.unlink() # Delete file
            # Optionally, try to delete user_id folder if empty
            user_dir = _get_user_file_dir(user_id)
            if not any(user_dir.iterdir()): # Check if directory is empty
                try:
                    user_dir.rmdir()
                except OSError as e: # May fail if there's a race condition or hidden files
                    print(f"Could not remove empty directory {user_dir}: {e}")
        else:
            print(f"File not found on disk for deletion: {full_physical_path}")
            # Still remove from record if it exists, might be an orphaned record

        del user_specific_uploads[filename]
        if not user_specific_uploads: # If last file for user, remove user entry
            del user_file_uploads[user_id]

        return True
    except Exception as e:
        print(f"Error deleting file {filename} for user {user_id}: {e}")
        return False

def get_agent_readable_document_content(user_id: str, filename: str) -> Optional[str]:
    record = get_uploaded_file_record(user_id, filename)
    if record and record.file_type in ["document", "text"]:
        return record.agent_readable_content
    return None

def get_agent_analyzable_dataframe_path(user_id: str, filename: str) -> Optional[str]:
    """Returns the full disk path to the dataframe file for an agent tool to load."""
    record = get_uploaded_file_record(user_id, filename)
    if record and record.file_type == "dataframe":
        # record.local_path is user_id/filename.ext relative to UI_ACCESSIBLE_WORKSPACE
        full_path = str(pathlib.Path(UI_ACCESSIBLE_WORKSPACE) / record.local_path)
        return full_path
    return None
