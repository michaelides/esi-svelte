<script>
  import { get } from 'svelte/store'; // Added get; Ensured semicolon
  import {
    llmTemperature,
    llmVerbosity,
    searchResultsCount,
    longTermMemoryEnabled,
    updateSettingsOnServer
  } from '$lib/stores/uiStore.js'; // Ensured semicolon

  import {
    chatHistoryMetadata,
    currentChatId,
    isLoadingChatList,
    createNewChat,
    selectChat,
    renameChat,
    deleteChat
  } from '$lib/stores/chatStore.js'; // Ensured semicolon

  // All fileStore.js related imports and premature code have been removed.
  // The file upload section in the template is also commented out or placeholder.

  import { slide } from 'svelte/transition'; // Ensured semicolon
  import { flip } from 'svelte/animate';   // Ensured semicolon (Uncommented)

  // For chat rename (existing)
  // let chatToRenameId = null; // Not directly used with prompt
  // let newChatNameInput = ""; // Not directly used with prompt

  function handleNewChat() {
    createNewChat();
  }

  function handleSelectChat(chatId) {
    if (get(currentChatId) !== chatId) {
      selectChat(chatId);
    }
  }

  function promptRenameChat(chat) {
    const newName = prompt(`Enter new name for "${chat.name}":`, chat.name);
    if (newName && newName.trim() !== "" && newName !== chat.name) {
      renameChat(chat.chat_id, newName.trim());
    }
  }

  function confirmDeleteChat(chatId, chatName) {
    if (confirm(`Are you sure you want to delete chat "${chatName}"?`)) {
      deleteChat(chatId);
    }
  }

  // For LLM settings update (existing)
  let debounceTimeout;
  function debouncedUpdateSettings() {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      updateSettingsOnServer();
    }, 500);
  }

  // For file upload - All related logic removed as fileStore.js is not ready
  // let selectedFileElement;
  // async function handleFileUpload(event) { ... }
  // function getFileIcon(fileType) { ... }
</script>

<aside class="sidebar">
  <section class="chat-history-section">
    <div class="section-header">
      <h3>Chat History</h3>
      <button on:click={handleNewChat} title="Create New Chat">+</button>
    </div>
    {#if $isLoadingChatList}
      <p class="loading-text">Loading chats...</p>
    {:else if $chatHistoryMetadata.length === 0}
      <p class="no-items-text">No chats yet. Start a new one!</p>
    {:else}
      <ul class="item-list chat-list">
        {#each $chatHistoryMetadata as chat (chat.chat_id)}
          <li
            transition:slide|local={{ duration: 200 }} <!-- transition on li -->
            animate:flip={{ duration: 200 }}         <!-- animate on li -->
            <!-- title attribute removed from li -->
          >
            <button
              type="button"
              class="chat-item-button"
              class:selected={$currentChatId === chat.chat_id}
              on:click={() => handleSelectChat(chat.chat_id)}
              aria-label={chat.name}
              title={chat.name}
            >
              <span class="item-name chat-name">{chat.name}</span>
              <div class="item-actions chat-actions">
                <button class="action-btn rename-btn" on:click|stopPropagation={() => promptRenameChat(chat)} title="Rename">✏️</button>
                <button class="action-btn delete-btn" on:click|stopPropagation={() => confirmDeleteChat(chat.chat_id, chat.name)} title="Delete">🗑️</button>
              </div>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <section class="file-upload-section">
    <div class="section-header">
      <h3>Uploaded Files</h3>
    </div>
    <!-- File input and related UI commented out until fileStore.js is ready -->
    <!--
    <input
      type="file"
      on:change={handleFileUpload}
      disabled={$isFileUploading}
      bind:this={selectedFileElement}
      class="file-input"
    />
    {#if $isFileUploading}
      <p class="loading-text">Uploading file...</p>
    {/if}
    {#if $generalFileError}
       <p class="error-text">File Error: {$generalFileError}</p>
    {/if}

    {#if $uploadedFiles.length === 0 && !$isFileUploading}
      <p class="no-items-text">No files uploaded yet.</p>
    {:else if $uploadedFiles.length > 0}
      <ul class="item-list file-list">
        {#each $uploadedFiles as file (file.filename)}
          <li title={file.filename}>
            <span class="file-icon">{getFileIcon(file.file_type)}</span>
            <span class="item-name file-name">{file.filename}</span>
            <div class="item-actions file-actions">
              <button class="action-btn delete-btn" on:click={() => deleteUploadedFile(file.filename)} title="Delete File">🗑️</button>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
    -->
    <p><em>(File upload functionality will be implemented here.)</em></p>
  </section>

  <section class="settings-section">
    <h3>LLM Settings</h3>
    <div>
      <label class="checkbox-label">
        <input type="checkbox" bind:checked={$longTermMemoryEnabled} on:change={updateSettingsOnServer} />
        Enable Long-term Memory
      </label>
    </div>
    <div>
      <label for="temperature_sidebar">Temperature: {$llmTemperature.toFixed(1)}</label>
      <input type="range" id="temperature_sidebar" bind:value={$llmTemperature} on:input={debouncedUpdateSettings} min="0" max="2" step="0.1" />
    </div>
    <div>
      <label for="verbosity_sidebar">Verbosity: {$llmVerbosity}</label>
      <input type="number" id="verbosity_sidebar" bind:value={$llmVerbosity} on:change={updateSettingsOnServer} min="1" max="5" step="1" />
    </div>
    <div>
      <label for="searchResultsCount_sidebar">Search Results: {$searchResultsCount}</label>
      <input type="number" id="searchResultsCount_sidebar" bind:value={$searchResultsCount} on:change={updateSettingsOnServer} min="1" max="10" step="1" />
    </div>
  </section>

  <section class="about-section">
    <h3>About ESI</h3>
    <p>ESI Scholarly Instructor - SvelteKit Edition</p>
  </section>
</aside>

<style>
  .sidebar {
    width: 300px; /* Increased width slightly */
    padding: 1rem; border-right: 1px solid #e0e0e0; height: 100vh;
    display: flex; flex-direction: column; gap: 1.25rem; /* Increased gap */
    overflow-y: auto; background-color: #fcfcfc;
  }
  .sidebar section { border-bottom: 1px solid #f0f0f0; padding-bottom: 1.25rem; }
  .sidebar section:last-child { border-bottom: none; padding-bottom: 0; }

  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; }
  h3 { margin-top: 0; margin-bottom: 0; font-size: 1.15em; color: #333; font-weight: 600;}

  .section-header button {
    background: none; border: none; font-size: 1.6rem; cursor: pointer; color: #007bff; padding: 0.1rem 0.3rem; line-height: 1;
  }
  .section-header button:hover { color: #0056b3; }

  .item-list { list-style: none; padding-left: 0; margin: 0; max-height: 220px; overflow-y: auto; }
  /* Original .item-list li styles are mostly moved to .chat-item-button or are no longer needed on li directly */
  .item-list li {
    margin-bottom: 0.3rem; /* Keep for spacing between items */
    /* display: flex; This is now on the button if it needs to fill the li */
  }
  /* .chat-list li { cursor: pointer; } /* Removed, button handles cursor */
  /* .item-list li:hover { background-color: #f0f0f0; } /* Moved to button */
  /* .chat-list li.selected { background-color: #007bff; color: white; } /* Moved to button */
  /* .chat-list li.selected .item-name, .chat-list li.selected .action-btn { color: white; } /* Handled by button's selected class */

  .chat-item-button {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0.65rem 0.5rem; /* Matched original li padding */
    margin: 0;
    border: none;
    background: none;
    text-align: left;
    font-size: inherit;
    font-family: inherit;
    color: inherit;
    cursor: pointer;
    border-radius: 0.3rem; /* Matched original li radius */
    transition: background-color 0.2s ease; /* Added transition here */
  }

  .chat-item-button:hover {
    background-color: #f0f0f0; /* Matched original li hover */
  }

  .chat-item-button.selected {
    background-color: #007bff; /* Matched original li selected */
    color: white;
  }

  .chat-item-button.selected .item-name,
  .chat-item-button.selected .action-btn {
    color: white;
  }
  .chat-item-button.selected .action-btn { opacity: 0.7; }
  .chat-item-button.selected .action-btn:hover { opacity: 1; }

  .item-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-grow: 1; padding-right: 8px;}
  .file-icon { margin-right: 8px; font-size: 0.9em; }

  .item-actions { display: flex; align-items: center; opacity: 0; transition: opacity 0.2s ease; }
  .item-list li:hover .item-actions { opacity: 1; }
  .chat-list li.selected .item-actions { opacity: 1; }

  .action-btn { background: none; border: none; cursor: pointer; padding: 0.2rem; margin-left: 0.4rem; font-size: 0.9em; color: #555; }
  .action-btn:hover { color: #222; }
  .rename-btn:hover { color: #28a745; }
  .delete-btn:hover { color: #dc3545; }

  .no-items-text { font-size: 0.9em; color: #6c757d; text-align: center; padding: 1rem 0;}
  .loading-text { font-size: 0.9em; color: #6c757d; padding: 0.5rem 0;}
  .error-text { font-size: 0.9em; color: #dc3545; padding: 0.5rem 0; border: 1px dashed #dc3545; border-radius: 0.25rem; margin-top: 0.5rem;}

  .file-input { width: 100%; margin-bottom: 0.75rem; font-size: 0.9em; }
  .file-input:disabled { opacity: 0.7; }

  label { display: block; margin-bottom: 0.6rem; font-size: 0.95em; color: #495057; }
  .checkbox-label { display: flex; align-items: center; font-size: 0.95em; }
  .checkbox-label input[type="checkbox"] { margin-right: 0.5rem; margin-bottom: 0; }

  input[type="range"] { width: 100%; margin-top: 0.25rem; }
  input[type="number"] { width: 100%; padding: 0.4rem; border: 1px solid #ced4da; border-radius: 0.25rem; }
</style>
