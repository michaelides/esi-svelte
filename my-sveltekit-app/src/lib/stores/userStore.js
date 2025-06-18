import { writable } from 'svelte/store'; // 'get' is not needed for this updated version

export const userId = writable(null);
export const isLoggedIn = writable(false);
export const userGreeting = writable(''); // Will be updated with progress/errors

export async function initializeUserSession() {
  userGreeting.set('Initializing: Fetching session...');
  try {
    const response = await fetch('/api/init', { method: 'POST' });

    if (!response.ok) {
      let errorMsg = `API init request failed (${response.status} ${response.statusText})`;
      try {
        const errorData = await response.json();
        errorMsg += errorData.detail ? ` - ${errorData.detail}` : '';
      } catch (e) { /* no json error body */ }
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userGreeting.set('Initializing: Parsing session data...');
    const data = await response.json();

    if (!data || !data.user_id || !data.settings || typeof data.greeting === 'undefined') {
      const errorMsg = 'Invalid data structure received from /api/init.';
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userId.set(data.user_id);
    // userGreeting will be set by data.greeting if successful, or by loadChatList's progress.
    // For now, let's set it to the API greeting. If loadChatList starts, it will override.
    userGreeting.set(data.greeting);
    isLoggedIn.set(true);

    // console.log('User session initialized successfully, isLoggedIn set to true.'); // Keep for local debugging
    return data.settings;

  } catch (error) {
    console.error("Failed to initialize user session:", error.message);
    // If userGreeting wasn't set by a more specific error above, this is a fallback.
    // Example: Network error before fetch even starts, or JSON parsing of response failed.
    // The more specific error messages inside try block are preferred.
    // This ensures *an* error message is set if one wasn't already.
    // Check if a specific error was already set by inspecting the error message itself
    // or if the greeting still shows an "Initializing..." message.
    // For simplicity here, we just overwrite if an error is caught at this level.
    userGreeting.set(`Init Error: ${error.message}. Please check network and backend service.`);
    isLoggedIn.set(false);
    return null;
  }
}
