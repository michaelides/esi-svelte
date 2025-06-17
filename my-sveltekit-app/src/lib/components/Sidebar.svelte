<script>
  import {
    llmTemperature,
    llmVerbosity,
    searchResultsCount,
    longTermMemoryEnabled,
    updateSettingsOnServer
  } from '$lib/stores/uiStore.js';

  import {
    chatHistoryMetadata,
    currentChatId,
    isLoadingChatList, // To show loading state for chat list
    createNewChat,
    selectChat,
    renameChat,
    deleteChat
  } from '$lib/stores/chatStore.js';

  import { slide } from 'svelte/transition'; // For item animation (optional)
  import { flip } from 'svelte/animate'; // For list animation (optional)

  let chatToRenameId = null;
  let newChatNameInput = "";

  function handleNewChat() {
    createNewChat();
  }

  function handleSelectChat(chatId) {
    if (get(currentChatId) !== chatId) {
      selectChat(chatId);
    }
  }

  function promptRename(chat) {
    chatToRenameId = chat.chat_id;
    newChatNameInput = chat.name;
    // In a real app, you'd use a modal here instead of prompt
    const newName = prompt(`Enter new name for "${chat.name}":`, chat.name);
    if (newName && newName.trim() !== "" && newName !== chat.name) {
      renameChat(chat.chat_id, newName.trim());
    }
    chatToRenameId = null; // Reset
  }

  function confirmDelete(chatId, chatName) {
    if (confirm(`Are you sure you want to delete chat "${chatName}"?`)) {
      deleteChat(chatId);
    }
  }

  let debounceTimeout;
  function debouncedUpdateSettings() {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      updateSettingsOnServer();
    }, 500);
  }
</script>

<aside class="sidebar">
  <section class="chat-history-section">
    <div class="section-header">
      <h3>Chat History</h3>
      <button on:click={handleNewChat} title="Create New Chat">+</button>
    </div>
    {#if $isLoadingChatList}
      <p>Loading chats...</p>
    {:else if $chatHistoryMetadata.length === 0}
      <p class="no-chats">No chats yet. Start a new one!</p>
    {:else}
      <ul class="chat-list">
        {#each $chatHistoryMetadata as chat (chat.chat_id)}
          <li
            class:selected={$currentChatId === chat.chat_id}
            on:click={() => handleSelectChat(chat.chat_id)}
            title={chat.name}
            transition:slide|local={{ duration: 200 }}
            animate:flip={{ duration: 200 }}
          >
            <span class="chat-name">{chat.name}</span>
            <div class="chat-actions">
              <button class="action-btn rename-btn" on:click|stopPropagation={() => promptRename(chat)} title="Rename">✏️</button>
              <button class="action-btn delete-btn" on:click|stopPropagation={() => confirmDelete(chat.chat_id, chat.name)} title="Delete">🗑️</button>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <section class="settings-section">
    <h3>LLM Settings</h3>
    <div>
      <label class="checkbox-label">
        <input
          type="checkbox"
          bind:checked={$longTermMemoryEnabled}
          on:change={updateSettingsOnServer}
        />
        Enable Long-term Memory
      </label>
    </div>
    <div>
      <label for="temperature_sidebar">Temperature: {$llmTemperature.toFixed(1)}</label>
      <input
        type="range"
        id="temperature_sidebar"
        bind:value={$llmTemperature}
        on:input={debouncedUpdateSettings}
        min="0" max="2" step="0.1"
      />
    </div>
    <div>
      <label for="verbosity_sidebar">Verbosity: {$llmVerbosity}</label>
      <input
        type="number"
        id="verbosity_sidebar"
        bind:value={$llmVerbosity}
        on:change={updateSettingsOnServer}
        min="1" max="5" step="1"
      />
    </div>
    <div>
      <label for="searchResultsCount_sidebar">Search Results: {$searchResultsCount}</label>
      <input
        type="number"
        id="searchResultsCount_sidebar"
        bind:value={$searchResultsCount}
        on:change={updateSettingsOnServer}
        min="1" max="10" step="1"
      />
    </div>
  </section>

  <section class="file-upload-section">
    <h3>Upload Files (Future)</h3>
    <input type="file" disabled />
    <ul>
      <li>file1.pdf (placeholder)</li>
    </ul>
  </section>

  <section class="about-section">
    <h3>About ESI</h3>
    <p>ESI Scholarly Instructor - SvelteKit Edition</p>
  </section>
</aside>

<style>
  .sidebar {
    width: 280px; padding: 1rem; border-right: 1px solid #ccc; height: 100vh;
    display: flex; flex-direction: column; gap: 1rem; overflow-y: auto; background-color: #f8f9fa; /* Lighter grey */
  }
  .sidebar section { border-bottom: 1px solid #e9ecef; padding-bottom: 1rem; }
  .sidebar section:last-child { border-bottom: none; padding-bottom: 0; }

  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
  h3 { margin-top: 0; margin-bottom: 0; font-size: 1.1em; color: #343a40; }

  .section-header button {
    background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #007bff; padding: 0.2rem; line-height: 1;
  }
  .section-header button:hover { color: #0056b3; }

  .chat-list { list-style: none; padding-left: 0; margin: 0; max-height: 200px; overflow-y: auto; /* Scroll if many chats */ }
  .chat-list li {
    padding: 0.6rem 0.5rem; margin-bottom: 0.25rem; border-radius: 0.25rem; cursor: pointer;
    display: flex; justify-content: space-between; align-items: center;
    transition: background-color 0.2s ease;
  }
  .chat-list li:hover { background-color: #e9ecef; }
  .chat-list li.selected { background-color: #007bff; color: white; }
  .chat-list li.selected .chat-name { font-weight: bold; }
  .chat-list li.selected .action-btn { color: white; opacity: 0.7; }
  .chat-list li.selected .action-btn:hover { opacity: 1; }


  .chat-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-grow: 1; padding-right: 5px;}
  .chat-actions { display: flex; align-items: center; opacity: 0; transition: opacity 0.2s ease; }
  .chat-list li:hover .chat-actions { opacity: 1; }
  .chat-list li.selected .chat-actions { opacity: 1; } /* Always show for selected */


  .action-btn { background: none; border: none; cursor: pointer; padding: 0.2rem; margin-left: 0.3rem; font-size: 0.9em; color: #6c757d; }
  .action-btn:hover { color: #343a40; }
  .rename-btn:hover { color: #28a745; } /* Green for rename */
  .delete-btn:hover { color: #dc3545; } /* Red for delete */

  .no-chats { font-size: 0.9em; color: #6c757d; text-align: center; padding: 1rem 0;}

  label { display: block; margin-bottom: 0.5rem; font-size: 0.95em; color: #495057; }
  .checkbox-label { display: flex; align-items: center; font-size: 0.95em; }
  .checkbox-label input[type="checkbox"] { margin-right: 0.5rem; margin-bottom: 0; }

  input[type="range"] { width: 100%; margin-top: 0.25rem; }
  input[type="number"] { width: 100%; padding: 0.3rem; border: 1px solid #ced4da; border-radius: 0.2rem; }

  input[type="file"] { font-size: 0.9em; margin-top: 0.5rem; }
  .settings-section ul { list-style: none; padding-left: 0; font-size: 0.9em; } /* For file list if any */
  .settings-section ul li { padding: 0.25rem 0; }
</style>
