import { writable } from 'svelte/store';

export const userId = writable(null);
export const isLoggedIn = writable(false);
export const userGreeting = writable('');

export async function initializeUserSession() {
  userGreeting.set('Initializing: Fetching session... (MOCKED)'); // Message 1 - Indicate mocking
  try {
    // --- MOCKING START ---
    console.log("Using MOCKED API response for /api/init");
    // const response = await fetch('/api/init', { method: 'POST' }); // Original fetch commented out

    // Simulate a short delay as if fetch was called
    await new Promise(resolve => setTimeout(resolve, 100));

    const mockJsonResponse = { // This is what response.json() should return
        user_id: 'mock-user-123',
        settings: {
          temperature: 0.7,
          verbosity: 3,
          search_results_count: 5,
          long_term_memory_enabled: true
        },
        greeting: 'Hello from Mock ESI!'
      };

    const mockResponse = {
      ok: true,
      status: 200,
      statusText: 'OK (Mocked)',
      json: async () => mockJsonResponse, // Mock the .json() method to return the predefined JSON
      text: async () => JSON.stringify(mockJsonResponse) // Mock .text() for error cases if needed
    };
    const response = mockResponse; // Use the mock response
    // --- MOCKING END ---

    userGreeting.set('Initializing: Received API response... (MOCKED)'); // Message 2

    if (!response.ok) {
      // This block should ideally not be hit with the current mock if ok: true
      let errorMsg = `API init request failed (${response.status} ${response.statusText})`;
      try {
        const errorData = await response.json(); // Will use mock json if called
        errorMsg += errorData.detail ? ` - ${errorData.detail}` : (JSON.stringify(errorData) ? ` - ${JSON.stringify(errorData)}` : '');
      } catch (e) {
        try {
            const textError = await response.text();
            errorMsg += textError ? ` - Body: ${textError.substring(0,100)}` : '';
        } catch (textE) { /* ignore */ }
      }
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userGreeting.set('Initializing: Parsing session data... (MOCKED)'); // Message 3
    const data = await response.json(); // Will use mock json()

    if (!data || !data.user_id || !data.settings || typeof data.greeting === 'undefined') {
      const errorMsg = 'Invalid data structure received from mock /api/init.';
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userId.set(data.user_id);
    userGreeting.set(data.greeting);
    isLoggedIn.set(true);

    console.log('User session MOCK initialized successfully, isLoggedIn set to true.');
    return data.settings;

  } catch (error) {
    console.error("Failed to initialize MOCK user session:", error.message);
    userGreeting.set(`Init Error (catch MOCKED): ${error.message}.`);
    isLoggedIn.set(false);
    return null;
  }
}
