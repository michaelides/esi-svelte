<script>
  import { sendMessage, isLoadingChat } from '$lib/stores/chatStore.js';
  import { currentChatId } from '$lib/stores/chatStore.js'; // Optional: for placeholder logic

  let inputValue = '';

  async function handleSend() {
    if (inputValue.trim() && !$isLoadingChat) {
      const messageToSend = inputValue;
      inputValue = ''; // Clear input immediately (optimistic)
      await sendMessage(messageToSend);
    }
  }
</script>

<div class="chat-input-area">
  <textarea
    bind:value={inputValue}
    placeholder={$currentChatId ? "Type your message..." : "Select or start a new chat to begin"}
    on:keypress={(e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); // Prevent newline on Enter unless Shift is pressed
        handleSend();
      }
    }}
    disabled={$isLoadingChat || !$currentChatId}
    rows="1"
  ></textarea>
  <button on:click={handleSend} disabled={$isLoadingChat || !inputValue.trim() || !$currentChatId}>
    {#if $isLoadingChat}
      Sending...
    {:else}
      Send
    {/if}
  </button>
</div>

<style>
  .chat-input-area {
    display: flex;
    padding: 1rem;
    border-top: 1px solid #ccc;
    background-color: #f9f9f9;
    height: auto; /* Allow dynamic height based on textarea */
    min-height: 70px; /* Keep a minimum height */
    box-sizing: border-box;
    align-items: flex-start; /* Align items to the start for multi-line textarea */
  }

  textarea {
    flex-grow: 1;
    padding: 0.75rem;
    border: 1px solid #ccc;
    border-radius: 0.35rem;
    margin-right: 0.75rem;
    font-size: 1rem;
    resize: none; /* Disable manual resize by user */
    line-height: 1.5;
    min-height: 40px; /* Start with a decent height */
    max-height: 120px; /* Prevent excessive height */
    overflow-y: auto; /* Allow scrolling within textarea if content exceeds max-height */
  }

  textarea:disabled {
    background-color: #e9ecef;
  }

  button {
    padding: 0.75rem 1.25rem;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 0.35rem;
    cursor: pointer;
    font-size: 1rem;
    align-self: flex-end; /* Align button to bottom if textarea grows */
    height: 40px; /* Match initial textarea height if single line */
    transition: background-color 0.2s ease;
  }

  button:hover:not(:disabled) {
    background-color: #0056b3;
  }

  button:disabled {
    background-color: #a0cfff; /* Lighter blue when disabled */
    cursor: not-allowed;
  }
</style>
