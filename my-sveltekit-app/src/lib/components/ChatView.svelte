<script>
  import { currentChatId, currentChatMessages, isLoadingChat as isLoadingOverall } from '$lib/stores/chatStore.js';
  import { userGreeting, isLoggedIn } from '$lib/stores/userStore.js';
  import { afterUpdate, tick } from 'svelte'; // tick for ensuring DOM update before scroll

  let chatViewEl;
  let autoScrollEnabled = true;

  // Autoscroll to bottom
  afterUpdate(async () => {
    if (autoScrollEnabled && chatViewEl) {
      await tick(); // Wait for DOM to update
      chatViewEl.scrollTop = chatViewEl.scrollHeight;
    }
  });

  function handleScroll() {
    if (chatViewEl) {
      // Disable autoscroll if user scrolls up significantly
      const isScrolledToBottom = chatViewEl.scrollHeight - chatViewEl.scrollTop <= chatViewEl.clientHeight + 50; // 50px tolerance
      autoScrollEnabled = isScrolledToBottom;
    }
  }
</script>

<div class="chat-view-container" bind:this={chatViewEl} on:scroll={handleScroll}>
  {#if !$currentChatId && $isLoggedIn}
    <div class="welcome-message">
      <h2>{$userGreeting || "Welcome to ESI!"}</h2>
      <p>Select a chat from the sidebar or start a new one to begin.</p>
    </div>
  {:else if $currentChatMessages.length === 0 && !$isLoadingOverall && $currentChatId}
    <div class="welcome-message">
      <p>This chat is empty. Send a message to start the conversation!</p>
    </div>
  {:else}
    {#each $currentChatMessages as message (message.id)}
      <div
        class="message {message.role}"
        class:error={message.isError}
        class:streaming={message.isLoading && message.role === 'assistant'}
      >
        <p class="message-sender"><strong>{message.role === 'user' ? 'You' : 'Assistant'}:</strong></p>
        <p class="message-content">
          {#if message.isError}
            <em>{message.content || "An error occurred."}</em>
          {:else}
            {message.content}
          {/if}
          {#if message.isLoading && message.role === 'assistant'}
            <span class="typing-cursor"></span>
          {/if}
        </p>
      </div>
    {/each}
  {/if}

  {#if $isLoadingOverall && $currentChatMessages.length === 0 && $currentChatId}
    <div class="loading-messages">
      <p>Loading messages...</p>
      <!-- Could add a spinner here too -->
    </div>
  {/if}
</div>

<style>
  .chat-view-container {
    flex-grow: 1;
    padding: 1rem 2rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    background-color: #ffffff;
  }

  .message {
    padding: 0.75rem 1.25rem;
    border-radius: 0.75rem;
    max-width: 75%;
    line-height: 1.6;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    word-wrap: break-word;
    display: flex; /* Use flex for sender + content structure */
    flex-direction: column; /* Stack sender and content */
  }

  .message-sender {
    margin-bottom: 0.25rem;
    font-size: 0.85em;
    font-weight: 600;
    color: #555; /* Default for assistant */
  }

  .message-content {
    margin: 0;
    white-space: pre-wrap; /* Respect newlines and spaces */
  }

  .message.user {
    background-color: #007bff;
    color: white;
    align-self: flex-end;
  }
  .message.user .message-sender { color: rgba(255,255,255,0.85); }

  .message.assistant {
    background-color: #e9ecef;
    color: #343a40;
    align-self: flex-start;
  }
  .message.assistant .message-sender { color: #495057; }

  .message.error {
    background-color: #ffebee; /* Light pink/red for error */
    border: 1px solid #e57373; /* Red border for error */
    color: #c62828; /* Darker red text for error */
  }
  .message.error .message-sender { color: #c62828; }

  /* For streaming assistant message */
  .message.streaming {
    /* You might not need specific styles if the cursor is enough, */
    /* but you could add a subtle pulse or background if desired. */
  }

  .typing-cursor::after {
    content: '▋';
    animation: blink 1s step-end infinite;
    display: inline-block; /* Ensure it takes space */
    margin-left: 2px; /* Small space after content */
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  .welcome-message {
    text-align: center;
    margin: auto;
    color: #6c757d;
  }
  .welcome-message h2 { font-weight: 500; margin-bottom: 0.5rem; }

  .loading-messages {
    text-align: center;
    margin: auto;
    color: #6c757d;
    font-style: italic;
  }
</style>
