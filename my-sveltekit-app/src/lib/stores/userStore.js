import { writable } from 'svelte/store';

export const userId = writable(null);
export const isLoggedIn = writable(false);
export const userGreeting = writable(''); // Will be updated with progress/errors

export async function initializeUserSession() {
  userGreeting.set('Initializing: Fetching session...'); // Message 1
  try {
    const response = await fetch('/api/init', { method: 'POST' });

    userGreeting.set('Initializing: Received API response...'); // Message 2 (NEW)

    if (!response.ok) {
      let errorMsg = `API init request failed (${response.status} ${response.statusText})`;
      try {
        const errorData = await response.json(); // Try to parse error body as JSON
        errorMsg += errorData.detail ? ` - ${errorData.detail}` : (JSON.stringify(errorData) ? ` - ${JSON.stringify(errorData)}` : '');
      } catch (e) {
        try { // If error body is not JSON, try to get it as text
            const textError = await response.text();
            // Limit length of textError to avoid overly long messages
            errorMsg += textError ? ` - Body: ${textError.substring(0, 100)}` : '';
        } catch (textE) { /* ignore if reading as text also fails */ }
      }
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userGreeting.set('Initializing: Parsing session data...'); // Message 3
    const data = await response.json(); // This could still fail if body is not JSON despite response.ok

    if (!data || !data.user_id || !data.settings || typeof data.greeting === 'undefined') {
      const errorMsg = 'Invalid data structure received from /api/init.';
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userId.set(data.user_id);
    userGreeting.set(data.greeting); // Set actual greeting from API (will be overridden by chatStore if it also sets one)
    isLoggedIn.set(true);

    // console.log('User session initialized successfully, isLoggedIn set to true.');
    return data.settings;

  } catch (error) {
    // This catch block is for errors like:
    // 1. Network error (fetch itself fails)
    // 2. response.json() fails (if !response.ok and error body wasn't json, or if response.ok but body isn't json)
    // 3. Errors explicitly thrown from the try block.
    console.error("Failed to initialize user session (in catch block):", error.message);

    // If userGreeting was already set to an error message, this might overwrite it.
    // The goal is for userGreeting to hold the *most relevant* error.
    // Errors thrown from within the try block will have already set userGreeting.
    // So, if it's a network error or response.json() failure on a 200 OK, this will set the message.
    // A simple approach: if message contains "Failed to fetch" (network) or "JSON.parse" or "Unexpected token" (json parsing)
    // then this is a good fallback. Otherwise, the specific error was likely already set.
    // For now, using the simpler logic from the prompt's "Corrected target structure":
    userGreeting.set(`Init Error (catch): ${error.message}.`);
    isLoggedIn.set(false);
    return null;
  }
}
