import { writable, get } from 'svelte/store';

// Default values for UI settings
export const llmTemperature = writable(0.7);
export const llmVerbosity = writable(3);
export const searchResultsCount = writable(5);
export const longTermMemoryEnabled = writable(true);

/**
 * Updates the Svelte stores with settings fetched from the server.
 * @param {object} settings - The settings object from the backend.
 */
export function setSettingsFromServer(settings) {
  if (settings) {
    if (typeof settings.temperature === 'number') {
      llmTemperature.set(settings.temperature);
    }
    if (typeof settings.verbosity === 'number') {
      llmVerbosity.set(settings.verbosity);
    }
    if (typeof settings.search_results_count === 'number') {
      searchResultsCount.set(settings.search_results_count);
    }
    if (typeof settings.long_term_memory_enabled === 'boolean') {
      longTermMemoryEnabled.set(settings.long_term_memory_enabled);
    }
    console.log("UI settings updated from server data:", settings);
  } else {
    console.warn("setSettingsFromServer called with null or undefined settings.");
  }
}

/**
 * Sends the current UI settings to the backend to be saved.
 */
export async function updateSettingsOnServer() {
  const currentSettings = {
    temperature: get(llmTemperature),
    verbosity: get(llmVerbosity),
    search_results_count: get(searchResultsCount),
    long_term_memory_enabled: get(longTermMemoryEnabled)
  };

  try {
    const response = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentSettings)
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch(e) { /* no json error body */ }
      console.error("API error response on settings update:", errorData);
      throw new Error(`Failed to update settings: ${response.statusText}${errorData ? ' - ' + (errorData.detail || JSON.stringify(errorData)) : ''}`);
    }

    const updatedSettings = await response.json();
    // Re-set from server response to ensure UI is in sync with the persisted state
    setSettingsFromServer(updatedSettings);
    console.log("Settings updated on server and UI synced.", updatedSettings);

  } catch (error) {
    console.error("Failed to update settings on server:", error);
    // Potentially revert UI changes to their state before the optimistic update,
    // or notify the user more formally.
    // For now, the UI will reflect the attempted change, which might not be ideal.
  }
}

// No automatic subscription update as per self-correction in prompt.
// updateSettingsOnServer should be triggered by user interactions in components.
