import { writable } from 'svelte/store';

export const userId = writable(null);
export const isLoggedIn = writable(false); // Represents if the session has been initialized
export const userGreeting = writable(''); // To store the greeting message from backend

export async function initializeUserSession() {
  try {
    // Ensure this path is correct based on how the SvelteKit app is served
    // relative to the FastAPI backend. If they are on different ports during dev,
    // a proxy is needed (handled in vite.config.js).
    const response = await fetch('/api/init', {
      method: 'POST',
      headers: {
        // Cookies are automatically sent by the browser, so no explicit 'credentials: include'
        // is typically needed unless dealing with complex cross-origin scenarios not covered by simple proxy.
      }
    });

    if (!response.ok) {
      // Attempt to get more specific error message from backend if available
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        // Backend didn't send JSON or other error
      }
      console.error("Initialization API error response:", errorData);
      throw new Error(`Initialization failed: ${response.statusText}${errorData ? ' - ' + (errorData.detail || JSON.stringify(errorData)) : ''}`);
    }

    const data = await response.json();

    userId.set(data.user_id);
    userGreeting.set(data.greeting);
    isLoggedIn.set(true); // Indicate session is initialized and successful

    console.log("User session initialized:", data);
    // Return settings to be set in uiStore
    return data.settings;
  } catch (error) {
    console.error("Failed to initialize user session:", error);
    isLoggedIn.set(false);
    // Set a user-friendly error message
    userGreeting.set("Failed to connect to the ESI service. Please try again later.");
    return null; // Indicate failure or return default settings
  }
}
