import { writable } from 'svelte/store';

/**
 * @typedef {object} UploadedFileRecord
 * @property {string} filename
 * @property {string | null} content_type
 * @property {number} size
 * @property {"document" | "dataframe" | "text" | "other"} file_type
 * @property {string} local_path - Relative path like 'user_id/filename.ext'
 * @property {string | null} summary
 * @property {string | null} agent_readable_content
 */

// --- State ---
/** @type {import('svelte/store').Writable<UploadedFileRecord[]>} */
export const uploadedFiles = writable([]);

/** @type {import('svelte/store').Writable<boolean>} */
export const isUploading = writable(false);

/** @type {import('svelte/store').Writable<string | null>} */
export const uploadError = writable(null);

/** @type {import('svelte/store').Writable<string | null>} */
export const generalFileError = writable(null); // For errors in loading/deleting

// --- Functions ---

/**
 * Fetches the list of uploaded files from the server.
 */
export async function loadUploadedFiles() {
  generalFileError.set(null);
  // isLoadingList.set(true); // Optional: if loading list takes time
  try {
    const response = await fetch('/api/files');
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorData.detail || `Failed to fetch files: ${response.statusText}`);
    }
    const files = await response.json();
    uploadedFiles.set(files);
  } catch (error) {
    console.error("Error loading uploaded files:", error);
    generalFileError.set(error.message);
    uploadedFiles.set([]); // Clear or maintain old list? Clearing for now.
  } finally {
    // isLoadingList.set(false);
  }
}

/**
 * Uploads a new file to the server.
 * @param {File} fileToUpload - The HTML File object to upload.
 */
export async function uploadFile(fileToUpload) {
  if (!fileToUpload) {
    uploadError.set("No file selected.");
    return;
  }

  isUploading.set(true);
  uploadError.set(null);

  const formData = new FormData();
  formData.append("file", fileToUpload);

  try {
    const response = await fetch('/api/files/upload', {
      method: 'POST',
      body: formData,
      // Headers are not explicitly 'multipart/form-data'; browser sets it with FormData
    });

    const result = await response.json(); // Backend returns FileProcessDetail

    if (!response.ok) {
      throw new Error(result.message || result.detail || `Upload failed: ${response.statusText}`);
    }

    if (result.status === "error") {
        throw new Error(result.message || "File processing failed on server.");
    }

    // On successful upload and processing, refresh the list of files
    await loadUploadedFiles();
    console.log("File uploaded successfully:", result.filename);

  } catch (error) {
    console.error("Error uploading file:", error);
    uploadError.set(error.message);
  } finally {
    isUploading.set(false);
  }
}

/**
 * Deletes a file from the server.
 * @param {string} filename - The name of the file to delete.
 */
export async function deleteFile(filename) {
  if (!filename) return;

  generalFileError.set(null);
  // Optionally set a specific deleting state for the item in UI
  try {
    const response = await fetch(`/api/files/${filename}`, {
      method: 'DELETE',
    });

    const result = await response.json(); // Expects SimpleStatusResponse

    if (!response.ok || !result.success) {
      throw new Error(result.message || result.detail || `Failed to delete file: ${response.statusText}`);
    }

    // On successful deletion, refresh the list
    await loadUploadedFiles();
    console.log("File deleted successfully:", filename);

  } catch (error) {
    console.error(`Error deleting file ${filename}:`, error);
    generalFileError.set(error.message);
  }
}
