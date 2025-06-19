<script>
  import Sidebar from '$lib/components/Sidebar.svelte';
  import ChatView from '$lib/components/ChatView.svelte';
  import ChatInput from '$lib/components/ChatInput.svelte';
</script>

<div class="app-layout">
  <Sidebar />
  <div class="main-content">
    <ChatView />
    <ChatInput />
  </div>
</div>

<style>
  .app-layout {
    display: flex;
    height: 100vh; /* Make app-layout take full viewport height */
    width: 100vw;  /* Make app-layout take full viewport width */
    overflow: hidden; /* Prevent scrollbars on the body itself if content is perfectly sized */
  }

  .main-content {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    /* height: 100vh; */ /* This was in the prompt, but redundant if .app-layout has height: 100vh and this flex-grows */
    overflow: hidden; /* Prevent this container from scrolling; scrolling is handled by ChatView */
  }

  /*
    Using :global can be powerful but also break encapsulation if not used carefully.
    Here, it's used to control the flex behavior of direct children of .main-content.
    An alternative would be to pass classes or use props to control child component sizing,
    or ensure ChatView and ChatInput intrinsically handle their flex sizing.
    For this step, sticking to the prompt's structure.
  */
  :global(.main-content > .chat-view) { /* Targeting ChatView's root element if it's a direct child */
    flex-grow: 1;
    overflow-y: auto;
    /*
      The calc(100vh - ...) approach can be brittle if ChatInput height changes.
      A pure flexbox approach where ChatInput has flex-shrink: 0 and ChatView has flex-grow: 1
      inside main-content (which is a flex column) usually works better without fixed heights.
      However, the ChatInput has a fixed height in its own style (70px).
      So, main-content (flex column) contains ChatView (flex-grow:1) and ChatInput (fixed height).
    */
    height: calc(100vh - 70px); /* 70px is ChatInput's height from its own styles */
  }

  :global(.main-content > .chat-input-area) { /* Targeting ChatInput's root element */
    flex-shrink: 0; /* Prevent chat input from shrinking */
    /* Height is already defined in ChatInput.svelte as 70px */
  }
</style>
