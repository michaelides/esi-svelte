import { writable, get } from 'svelte/store';
import { userGreeting } from '$lib/stores/userStore.js'; // Import for error reporting


// --- State ---
export const chatHistoryMetadata = writable([]); // List of { chat_id, name, last_updated }
export const currentChatId = writable(null);
export const currentChatMessages = writable([]); // List of { id, role, content, isLoading?, isError? }
export const isLoadingChat = writable(false); // For loading messages or waiting for assistant response
export const isLoadingChatList = writable(false); // For loading the list of chats

// --- Helper ---
function _updateMetadataTimestamp(chatId, timestamp = null) {
  chatHistoryMetadata.update(metadataList => {
    const chatIndex = metadataList.findIndex(m => m.chat_id === chatId);
    if (chatIndex !== -1) {
      metadataList[chatIndex].last_updated = timestamp || new Date().toISOString();
      metadataList.sort((a, b) => new Date(b.last_updated) - new Date(a.last_updated));
    }
    return [...metadataList]; // Ensure reactivity
  });
}

// --- Functions ---
export async function loadChatList() {
  isLoadingChatList.set(true);
  userGreeting.set('Initializing: Loading chat list...'); // Update greeting during this phase
  try {
    const response = await fetch('/api/chats');
    if (!response.ok) {
      let errorMsg = `API chat list request failed (${response.status} ${response.statusText})`;
      try {
        const errorData = await response.json();
        errorMsg += errorData.detail ? ` - ${errorData.detail}` : '';
      } catch (e) { /* no json error body */ }
      userGreeting.set(`Error: ${errorMsg}`);
      throw new Error(errorMsg);
    }

    userGreeting.set('Initializing: Parsing chat list...');
    const data = await response.json(); // Expects ListChatsResponse -> { chats: List[ChatMetadata] }

    if (!data || !Array.isArray(data.chats)) {
        const errorMsg = 'Invalid data structure received from /api/chats.';
        userGreeting.set(`Error: ${errorMsg}`);
        throw new Error(errorMsg);
    }

    const sortedChats = data.chats.sort((a, b) => new Date(b.last_updated) - new Date(a.last_updated));
    chatHistoryMetadata.set(sortedChats);
    // Set a final success message or clear it. If userGreeting was set by API, that should prevail.
    // This message might be overwritten if initializeUserSession's greeting is set last.
    // For now, let's indicate this specific step is done.
    userGreeting.set('Initialization complete. Ready.');

  } catch (error) {
    console.error("Failed to load chat list:", error.message);
    // userGreeting might have been set by a more specific error above.
    // If not, this is a fallback.
    // To avoid complex checks, just set it. Last error wins.
    userGreeting.set(`ChatList Error: ${error.message}. Please try refreshing.`);
    chatHistoryMetadata.set([]); // Clear chat list on error
  } finally {
    isLoadingChatList.set(false);
  }
}

export async function selectChat(chatId) {
  if (!chatId) {
    currentChatId.set(null);
    currentChatMessages.set([]);
    return;
  }
  currentChatId.set(chatId);
  isLoadingChat.set(true);
  currentChatMessages.set([]);
  try {
    const response = await fetch(`/api/chats/${chatId}`);
    if (!response.ok) throw new Error(`Failed to fetch messages for chat ${chatId}: ${response.statusText}`);
    const chatSession = await response.json();
    currentChatMessages.set(chatSession.messages.map(m => ({...m, id: `${m.role}-${Date.now()}-${Math.random()}` })) || []);
  } catch (error) {
    console.error(`Error selecting chat ${chatId}:`, error);
    currentChatMessages.set([{ role: 'assistant', content: `Error loading chat: ${error.message}`, id: 'err-load' }]);
  } finally {
    isLoadingChat.set(false);
  }
}

// createNewChat should primarily set up the chat session.
// The first message from user will be sent via sendMessage.
export async function createNewChat(firstUserQueryForName = null) {
  isLoadingChatList.set(true); // Indicate activity in chat list area
  try {
    const payload = firstUserQueryForName ? { first_query: firstUserQueryForName } : {};
    const response = await fetch('/api/chats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`Failed to create new chat: ${response.statusText}`);
    const newChatSession = await response.json();

    // Add to metadata and sort
    chatHistoryMetadata.update(list =>
        [newChatSession, ...list].sort((a,b) => new Date(b.last_updated) - new Date(a.last_updated))
    );

    // Select the new chat. It will contain an initial greeting from the backend.
    currentChatId.set(newChatSession.chat_id);
    currentChatMessages.set(newChatSession.messages.map(m => ({...m, id: `${m.role}-${Date.now()}-${Math.random()}` })) || []);

    return newChatSession.chat_id; // Return new chat ID
  } catch (error) {
    console.error("Error creating new chat:", error);
    // Consider setting an error message in a global notification store or similar
    return null;
  } finally {
    isLoadingChatList.set(false);
  }
}


export async function sendMessage(query) {
  if (!query || !query.trim()) return;

  let activeChatId = get(currentChatId);

  // Add user message optimistically
  const userMessageId = `user-${Date.now()}-${Math.random()}`;
  const userMessage = { role: 'user', content: query, id: userMessageId };
  currentChatMessages.update(msgs => [...msgs, userMessage]);

  isLoadingChat.set(true); // Set loading true after user message is shown

  // If no chat is active, create one. The name might be based on this first query.
  if (!activeChatId) {
    try {
      activeChatId = await createNewChat(query); // Pass query for potential naming
      if (!activeChatId) {
        throw new Error("Chat creation failed, cannot send message.");
      }
      // createNewChat now sets currentChatId and loads initial messages (greeting).
      // The user's first message is already added optimistically above.
      // Now proceed to get assistant's response to *this* first user message.
    } catch (error) {
      console.error("Error in sendMessage during new chat creation:", error);
      currentChatMessages.update(msgs =>
        msgs.filter(m => m.id !== userMessageId) // Revert optimistic user message
          .concat([{ role: 'assistant', content: `Error: ${error.message}`, id: 'err-send', isError: true }])
      );
      isLoadingChat.set(false);
      return;
    }
  }

  const assistantMessageId = `assistant-${Date.now()}-${Math.random()}`;
  const assistantPlaceholder = {
    role: 'assistant', content: '', id: assistantMessageId, isLoading: true, isError: false
  };
  currentChatMessages.update(msgs => [...msgs, assistantPlaceholder]);

  try {
    const response = await fetch(`/api/chats/${activeChatId}/message_stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, history: [] }) // Backend loads history by chat_id
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error ${response.status}: ${response.statusText}. Details: ${errorText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalContent = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) {
            // This break is for when the stream itself ends without an 'eos' message.
            // 'eos' type event should handle final state.
            currentChatMessages.update(msgs =>
                msgs.map(m => m.id === assistantMessageId ? { ...m, isLoading: false, content: finalContent } : m)
            );
            _updateMetadataTimestamp(activeChatId); // Update timestamp with final message time
            isLoadingChat.set(false); // Ensure loading is false
            break;
        }

        buffer += decoder.decode(value, { stream: true });
        let eolIndex;
        while ((eolIndex = buffer.indexOf('\n\n')) >= 0) {
            const line = buffer.slice(0, eolIndex).trim();
            buffer = buffer.slice(eolIndex + '\n\n'.length);

            if (line.startsWith("data:")) {
                const jsonData = line.substring("data:".length).trim();
                try {
                    const eventData = JSON.parse(jsonData);
                    if (eventData.type === 'token') {
                        finalContent += eventData.content;
                        currentChatMessages.update(msgs =>
                            msgs.map(m => m.id === assistantMessageId ? { ...m, content: finalContent, isLoading: true } : m)
                        );
                    } else if (eventData.type === 'eos') {
                        currentChatMessages.update(msgs =>
                            msgs.map(m => m.id === assistantMessageId ? { ...m, isLoading: false, content: finalContent } : m)
                        );
                        _updateMetadataTimestamp(activeChatId); // Update timestamp on EOS
                        isLoadingChat.set(false);
                        // loadChatList(); // Refresh chat list for updated timestamps - already done by _updateMetadataTimestamp sort
                        return; // Exit processing loop, stream handled.
                    } else if (eventData.type === 'error') {
                         throw new Error(`Stream error from backend: ${eventData.content}`);
                    }
                } catch (e) {
                    console.warn("Error parsing SSE event JSON or processing event:", e, "Raw data:", jsonData);
                }
            }
        }
    }
  } catch (error) {
    console.error("Streaming sendMessage error:", error);
    currentChatMessages.update(msgs =>
        msgs.map(m => m.id === assistantMessageId ? { ...m, content: `Error: ${error.message}`, isLoading: false, isError: true } : m)
    );
    isLoadingChat.set(false); // Ensure loading is false on error
  }
  // isLoadingChat should be set to false by EOS or error handling.
  // If loop finishes without EOS (e.g. network drop), it's handled by the 'done' block or outer finally.
}


export async function renameChat(chatId, newName) {
  if (!chatId || !newName || !newName.trim()) return;
  try {
    const response = await fetch(`/api/chats/${chatId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_name: newName })
    });
    if (!response.ok) throw new Error(`Failed to rename chat: ${response.statusText}`);
    const updatedMetadata = await response.json();
    chatHistoryMetadata.update(list =>
      list.map(c => c.chat_id === chatId ? updatedMetadata : c)
          .sort((a,b) => new Date(b.last_updated) - new Date(a.last_updated))
    );
  } catch (error) {
    console.error(`Error renaming chat ${chatId}:`, error);
    // await loadChatList(); // Force reload for consistency on error
  }
}

export async function deleteChat(chatId) {
  if (!chatId) return;
  try {
    const response = await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`Failed to delete chat: ${response.statusText}`);

    await loadChatList(); // Refresh list from server
    if (get(currentChatId) === chatId) {
      currentChatId.set(null);
      currentChatMessages.set([]);
      // Optionally select first chat in list if available
      const newChatList = get(chatHistoryMetadata);
      if (newChatList.length > 0) {
        // selectChat(newChatList[0].chat_id); // This would auto-load its messages
      }
    }
  } catch (error) {
    console.error(`Error deleting chat ${chatId}:`, error);
    // await loadChatList(); // Force reload for consistency on error
  }
}
