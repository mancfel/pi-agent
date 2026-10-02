# Session Cleanup Extension

Pi extensions that help manage and clean up long-running sessions — pruning abandoned branches, selective compaction via LLM analysis, and session statistics.

## Commands

### `/session-prune` — Remove an abandoned branch

Interactively select a node in the session tree and remove it along with all descendants from the session file.

**Use case**: You explored approach A in detail but switched to B. The entire A-branch is now dead weight taking up context window space.

**Steps**:
1. Runs `buildTree()` on current session entries
2. Displays full tree structure in a widget above editor
3. Presents numbered list of selectable nodes (branch points + messages)
4. User selects which subtree to prune
5. Shows preview of entries that will be removed
6. Asks for confirmation before writing
7. Rewrites JSONL file, removing pruned entries and reparenting orphans
8. Reports success — user should restart/reload session to pick up changes

### `/session-summarize` — LLM-driven selective compaction

Sends the entire session to the LLM with instructions to analyze every entry and decide whether it should be kept, summarized, or discarded. The LLM returns structured JSON decisions which are then applied automatically after user approval.

**Use case**: Session has grown very long (hundreds of turns) with lots of exploration and back-and-forth. Want to compress without losing important context.

**Steps**:
1. Serializes all message entries (capped at 300 for safety)
2. Sends analysis prompt to LLM via `sendUserMessage()`
3. Waits for agent to settle
4. Extracts LLM response text from session entries
5. Parses JSON decisions array
6. Shows summary counts: keep / summarize / discard
7. Asks for confirmation before applying changes
8. Rewrites file — replaces discarded messages, converts summarized ones to compaction entries

### `/session-compact-focused` — Focused built-in compact

Wrapper around pi's native `/compact` command with custom focus instructions. Lets you guide what the LLM should prioritize in its summary.

**Use case**: Want quick compaction without full analysis, but with focused instructions about what matters most (e.g., "focus on code patterns and architectural decisions").

**Steps**:
1. Prompts user for free-text focus instructions
2. Sends `/compact <instructions>` via `sendUserMessage()`
3. Waits for agent to settle
4. Reports success

### `/session-stats` — Session statistics overview

Displays a structured report of current session: entry counts by type, message breakdown (user/assistant/toolResult), total tokens used, leaf position.

## How It Works

### Pruning Algorithm

1. **Build tree**: Parse flat JSONL entries into parent-child hierarchy using `id`/`parentId` fields
2. **Select node**: User picks which subtree to remove
3. **Collect descendants**: DFS from selected node gathers all ids in the subtree
4. **Filter file**: Rewrite JSONL keeping only non-descendant entries
5. **Reparent orphans**: Entries whose parent was pruned get `parentId: null` so they remain valid standalone nodes instead of broken references

### Summarization Prompt

The LLM receives a serialized view of every message with format:
```
<8-char-id> [role]: content...
    → toolName({"arg": "value"})  // for assistant messages with tools
```

Plus session metadata (message counts, first user text). The prompt instructs the LLM to return JSON decisions per entry:
- `"keep"` — preserve verbatim
- `"summarize"` — replace with compaction-style summary  
- `"discard"` — remove entirely

Applied decisions are written directly to the JSONL file. Discarded entries are omitted; summarized entries become `compaction` type entries.

## Session Reload Note

After pruning or summarizing, the JSONL file is modified on disk but the in-memory `SessionManager` instance still holds stale data. Pi does not provide a way to reload a session file into an existing runtime without triggering shutdown/startup lifecycle events. 

**Workaround**: After running `/session-prune` or `/session-summarize`, restart your pi session (`/new`) and resume from the cleaned-up state. The first user message will be available for continuation.

## Extension Lifecycle

- **Auto-discovered** from `~/.pi/agent/extensions/session-cleanup/index.ts`
- **Hot-reloadable** via `/reload` command (changes take effect after reload)
- **Cleanup on shutdown**: Clears widget/status bar entries on `session_shutdown` event
