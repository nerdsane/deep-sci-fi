# Agent-UI Connection Reliability Analysis

## Problem Statement

**Symptom:** Agent says it wrote a story, but UI doesn't show it. Connection feels unstable - sometimes works, sometimes doesn't.

**Root Cause:** Async disconnect between agent actions and UI awareness.

---

## Current Architecture (Broken)

```
User clicks "Write Story" in Canvas
   ↓
Canvas: POST /api/world/:checkpoint/new-story
   ↓
Server: client.agents.messages.create(agentId, { messages: [...] })
   ↓
Returns immediately with: { status: "success", message: "Agent is working..." }
   ↓
UI shows message for 3 seconds, then clears
   ↓
[Meanwhile, agent is still processing...]
   ↓
Agent calls: story_manager({ operation: "create", ... })
   ↓
Tool writes: .dsf/stories/{world}/{story}.json
   ↓
File watcher (maybe) detects change
   ↓
WebSocket (maybe) broadcasts "reload"
   ↓
UI (maybe) receives reload and refetches data
```

**Failure Points:**
1. ❌ **No confirmation tool succeeded** - Agent might call tool, tool fails, agent doesn't know
2. ❌ **No visibility into agent progress** - UI just shows "working..." then gives up
3. ❌ **File watcher unreliable** - Might miss changes, might be slow
4. ❌ **WebSocket might not deliver** - Connection issues, timing issues
5. ❌ **Agent response not streamed** - UI has no idea what agent is doing
6. ❌ **No polling fallback** - If WebSocket fails, UI never updates
7. ❌ **Race conditions** - File might be written before watcher subscribes

---

## Why Agent Says "I Wrote It" But Didn't

**Scenario 1: Tool Call Failed Silently**
```
Agent: "I'll create a story using story_manager"
Agent calls: story_manager({ ... })
Tool returns: { error: "Invalid parameters" }
Agent: "I successfully created the story!" ← WRONG
```

Agent doesn't always check tool return values properly.

**Scenario 2: Agent Hallucinated**
```
Agent: "I've created a story called 'Neural Dreams'"
Reality: Agent never called story_manager at all
```

LLMs sometimes claim to have done things they didn't.

**Scenario 3: Tool Succeeded But File Not Where Expected**
```
Agent: story_manager({ story_id: "neural-dreams", world_checkpoint: "wrong_name" })
Tool writes to: .dsf/stories/wrong_name/neural-dreams.json
UI looking in: .dsf/stories/neural_art_2035/
```

Mismatch in world checkpoint names.

---

## Robust Solution: Multi-Layer Approach

### Layer 1: Stream Agent Responses (Real-Time Visibility)

**What:** Stream agent's response as it generates, showing user exactly what agent is doing.

**How:**
```typescript
// Server: Enable streaming
const stream = await client.agents.messages.create(agentId, {
  messages: [...],
  stream: true  // Enable streaming
});

// Return SSE (Server-Sent Events)
return new Response(stream, {
  headers: {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  }
});

// UI: Listen to stream
const eventSource = new EventSource('/api/continue-stream?story_id=...');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'agent_thinking') {
    showMessage("Agent is thinking...");
  }

  if (data.type === 'tool_call') {
    showMessage(`Agent is using ${data.tool_name}...`);
  }

  if (data.type === 'tool_result') {
    if (data.success) {
      showMessage(`✓ ${data.tool_name} succeeded`);
    } else {
      showError(`✗ ${data.tool_name} failed: ${data.error}`);
    }
  }

  if (data.type === 'done') {
    showMessage("Agent finished!");
    pollForUpdates(); // Trigger Layer 2
  }
};
```

**Benefits:**
- ✅ User sees what agent is doing in real-time
- ✅ Know immediately if tool calls succeed/fail
- ✅ Can show progress: "Calling story_manager..." → "Success!"
- ✅ Detect if agent is stuck or erroring

---

### Layer 2: Active Polling (Reliable Fallback)

**What:** After agent finishes, actively poll the data endpoints to confirm changes appeared.

**How:**
```typescript
async function pollForUpdates(expectedType: 'story' | 'world', maxAttempts = 10) {
  let attempts = 0;
  const interval = 2000; // 2 seconds

  while (attempts < maxAttempts) {
    attempts++;

    // Fetch latest data
    const response = await fetch('/api/stories');
    const stories = await response.json();

    // Check if expected content exists
    if (contentAppearedAsExpected(stories)) {
      console.log(`✓ Content appeared after ${attempts} attempts`);
      reloadUI();
      return true;
    }

    await sleep(interval);
  }

  console.error(`✗ Content did not appear after ${maxAttempts} attempts`);
  showError("Agent finished but content not detected. Try refreshing.");
  return false;
}
```

**Benefits:**
- ✅ Works even if WebSocket fails
- ✅ Confirms content actually appeared
- ✅ Retries automatically
- ✅ Has timeout to prevent infinite waiting

---

### Layer 3: Enhanced File Watching (Reactive Updates)

**What:** More aggressive file watching with specific path monitoring.

**How:**
```typescript
// Server: Watch specific files based on operation
async function watchForStory(storyId: string, worldCheckpoint: string) {
  const storyPath = `.dsf/stories/${worldCheckpoint}/${storyId}.json`;

  const watcher = fs.watch(storyPath, (eventType) => {
    if (eventType === 'change' || eventType === 'rename') {
      console.log(`Story ${storyId} updated!`);
      broadcastToClients({ type: 'story_updated', storyId });
    }
  });

  // Auto-cleanup after 30 seconds
  setTimeout(() => watcher.close(), 30000);
}

// When agent starts working, setup targeted watch
POST /api/continue → watchForStory(story_id, world_checkpoint)
```

**Benefits:**
- ✅ More targeted than watching entire directories
- ✅ Faster detection of specific changes
- ✅ Can include metadata (which story changed)

---

### Layer 4: Tool Call Verification (Catch Failures Early)

**What:** After agent completes, verify tools actually succeeded by checking files.

**How:**
```typescript
async function verifyToolExecution(agentResponse: any) {
  // Parse agent's tool calls from response
  const toolCalls = extractToolCalls(agentResponse);

  for (const call of toolCalls) {
    if (call.tool === 'story_manager' && call.operation === 'create') {
      const storyId = call.params.story_id;
      const worldCheckpoint = call.params.world_checkpoint;

      // Verify file exists
      const storyPath = `.dsf/stories/${worldCheckpoint}/${storyId}.json`;
      if (!fs.existsSync(storyPath)) {
        console.error(`✗ Tool claimed success but file not found: ${storyPath}`);
        return { success: false, error: 'Story file not created' };
      }

      // Verify file has content
      const content = JSON.parse(fs.readFileSync(storyPath, 'utf-8'));
      if (!content.segments || content.segments.length === 0) {
        console.error(`✗ Story file exists but has no segments`);
        return { success: false, error: 'Story has no content' };
      }

      console.log(`✓ Verified: ${storyId} exists with ${content.segments.length} segments`);
    }
  }

  return { success: true };
}
```

**Benefits:**
- ✅ Catches agent hallucinations ("I did X" but didn't)
- ✅ Catches tool failures (tool returned error but agent ignored)
- ✅ Can provide specific error messages to user

---

## Complete Flow (Robust)

```
User clicks "Write Story"
   ↓
Canvas: POST /api/world/:checkpoint/new-story-stream (streaming endpoint)
   ↓
Server: Start streaming agent response
   │
   ├─> UI receives: { type: 'agent_thinking' }
   │   UI shows: "Agent is thinking..."
   │
   ├─> UI receives: { type: 'tool_call', tool: 'story_manager' }
   │   UI shows: "Creating story..."
   │
   ├─> Server: Tool executes, returns result
   │
   ├─> UI receives: { type: 'tool_result', success: true }
   │   UI shows: "✓ Story created!"
   │
   └─> UI receives: { type: 'done' }
       UI shows: "Agent finished!"

   ↓
Server: Verify tool execution (Layer 4)
   - Check if .dsf/stories/{world}/{story}.json exists
   - Check if it has content

   ↓
UI: Start polling (Layer 2)
   - Fetch /api/stories every 2 seconds
   - Check if new story appears
   - Stop after 10 attempts or success

   ↓
File Watcher: Detects change (Layer 3)
   - Broadcasts to WebSocket
   - UI receives reload notification

   ↓
UI: Reloads data, shows new story
```

**Redundancy:**
- If streaming fails → polling catches it
- If polling fails → file watcher catches it
- If file watcher fails → manual refresh works
- If tool fails → verification catches it

---

## Implementation Priority

### Phase 1: Add Polling (Quick Win - 30 min)
- Simplest, most reliable improvement
- Add polling after agent responses
- Will immediately improve reliability

### Phase 2: Add Streaming (Better UX - 2 hours)
- Stream agent responses to UI
- Show real-time progress
- Much better user experience

### Phase 3: Tool Verification (Robustness - 1 hour)
- Verify tools actually executed
- Catch failures and hallucinations
- Return specific errors to user

### Phase 4: Enhanced Watching (Polish - 30 min)
- Targeted file watches
- Faster reactive updates
- Nice-to-have optimization

---

## Minimal Viable Fix (Phase 1)

**Add polling right now:**

```typescript
// In canvas/app.tsx

async function waitForContentUpdate(
  checkFn: () => Promise<boolean>,
  timeoutMs = 20000
): Promise<boolean> {
  const startTime = Date.now();
  const interval = 2000;

  while (Date.now() - startTime < timeoutMs) {
    if (await checkFn()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  return false;
}

// In handleContinue()
async function handleContinue() {
  setContinuingStory(true);
  setContinueMessage("Agent is writing...");

  const initialSegmentCount = story.segments.length;

  try {
    const response = await fetch('/api/continue', { ... });
    const result = await response.json();

    setContinueMessage("Waiting for new segment...");

    // POLL for updates
    const success = await waitForContentUpdate(async () => {
      const updatedStory = await loadStory(story.id);
      return updatedStory.segments.length > initialSegmentCount;
    });

    if (success) {
      setContinueMessage("✓ New segment added!");
      loadData(); // Reload UI
    } else {
      setContinueMessage("⚠ Agent finished but segment not detected. Try refreshing.");
    }

  } catch (error) {
    setContinueMessage(`Error: ${error}`);
  } finally {
    setTimeout(() => {
      setContinuingStory(false);
      setContinueMessage(null);
    }, 3000);
  }
}
```

**This alone will make things much more reliable.**

---

## Long-Term Vision

Eventually, we want:

1. **Real-time streaming UI** - Watch agent work like you watch a terminal
2. **Tool execution graph** - Visual diagram of which tools ran, what they did
3. **Retry mechanism** - If tool fails, agent can retry with corrections
4. **Undo/redo** - If agent creates wrong content, user can rollback
5. **Manual tool invocation** - User can directly call tools from UI

But for now, **Phase 1 (polling) will fix the immediate reliability issue**.

---

## Recommendation

**Implement Phase 1 now (30 min)** - Add polling to all three operations:
- Continue Story
- Write New Story
- Develop World

This will immediately improve reliability by 90%+.

Then **test thoroughly** to confirm it works consistently.

After that works, we can add streaming (Phase 2) for better UX.
