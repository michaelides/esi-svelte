<script>
  import '../app.css'; // Global styles
  import { onMount } from 'svelte';
  import { initializeUserSession, userGreeting, isLoggedIn } from '$lib/stores/userStore.js';
  import { setSettingsFromServer } from '$lib/stores/uiStore.js';
  import { loadChatList } from '$lib/stores/chatStore.js'; // Import loadChatList

  onMount(async () => {
    const settingsFromServer = await initializeUserSession();
    // initializeUserSession sets isLoggedIn store value
    if (get(isLoggedIn)) { // Check store value directly after await
      if (settingsFromServer) {
        setSettingsFromServer(settingsFromServer);
      }
      await loadChatList(); // Load chat list if session initialized successfully
    }
    // If initializeUserSession fails, isLoggedIn will be false,
    // and userGreeting will contain an error message from userStore.
  });
</script>

{#if $isLoggedIn}
  <main>
    <slot />
  </main>
{:else}
  <div class="loading-container">
    <!-- Display the greeting/error message from userStore -->
    <p>{$userGreeting || 'Initializing ESI...'}</p>
    <!-- Basic spinner for loading indication -->
    <div class="spinner"></div>
  </div>
{/if}

<style>
  main {
    height: 100vh;
    width: 100vw;
    margin: 0;
    padding: 0;
    display: flex; /* Ensures the slotted page layout can flex correctly */
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100vh;
    width: 100vw;
    background-color: #f0f2f5; /* Optional: background for loading screen */
    color: #333;
  }

  .loading-container p {
    margin-bottom: 1.5rem;
    font-size: 1.2rem;
  }

  .spinner {
    border: 4px solid rgba(0, 0, 0, 0.1);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border-left-color: #007bff; /* Using a common theme color */
    animation: spin 1s linear infinite; /* Changed to linear for smoother spin */
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  /* Global body reset from previous step, ensuring it's here */
  :global(body) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
  }
  :global(*, *::before, *::after) {
    box-sizing: inherit;
  }
</style>
