import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, writeFileSync } from "node:fs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TreeNode {
  entry: Record<string, unknown>;
  children: TreeNode[];
}

type CleanupAction = "keep" | "summarize" | "discard";

interface CleanupDecision {
  id: string;
  action: CleanupAction;
  summary?: string;
}

// ---------------------------------------------------------------------------
// Helpers — file I/O, tree walking
// ---------------------------------------------------------------------------

function readSessionFile(path: string): Record<string, unknown>[] {
  const raw = readFileSync(path, "utf-8");
  return raw.trim().split("\n").filter(Boolean).map(line => JSON.parse(line));
}

function writeSessionFile(path: string, entries: Record<string, unknown>[]): void {
  const content = entries.map(e => JSON.stringify(e)).join("\n") + "\n";
  writeFileSync(path, content, "utf-8");
}

/** Build a tree from flat entry list. Returns roots and an id→node map. */
function buildTree(entries: Record<string, unknown>[]): {
  roots: TreeNode[];
  map: Map<string, TreeNode>;
} {
  const map = new Map<string, TreeNode>();

  for (const entry of entries) {
    if (entry.type === "session") continue; // header
    map.set(entry.id, { entry, children: [] });
  }

  const roots: TreeNode[] = [];
  for (const [id, node] of map) {
    const parentId = (node.entry.parentId ?? null) as string | null;
    if (!parentId || !map.has(parentId)) {
      roots.push(node);
    } else {
      map.get(parentId)!.children.push(node);
    }
  }

  return { roots, map };
}

/** Collect all descendant ids including self */
function collectDescendantIds(node: TreeNode): Set<string> {
  const ids = new Set<string>();
  function walk(n: TreeNode) {
    ids.add(n.entry.id);
    for (const c of n.children) walk(c);
  }
  walk(node);
  return ids;
}

/** Format an entry as human-readable text */
function formatEntry(entry: Record<string, unknown>, maxLen = 100): string {
  switch (entry.type) {
    case "message": {
      const msg = entry.message as Record<string, unknown>;
      const role = (msg.role ?? "?").toString();
      let content = "";
      if (typeof msg.content === "string") {
        content = msg.content.slice(0, maxLen).replace(/\n/g, " ");
      } else if (Array.isArray(msg.content)) {
        for (const block of msg.content as any[]) {
          if (block?.type === "text" && typeof block.text === "string") {
            content += block.text.slice(0, Math.max(maxLen - content.length, 1));
            break;
          }
        }
      }
      // Include tool call info from assistant messages
      if (role === "assistant" && Array.isArray(msg.content)) {
        const tools = (msg.content as any[]).filter((c: any) => c?.type === "toolCall");
        for (const tc of tools) {
          const argsShort = JSON.stringify(tc.arguments ?? {}).slice(0, 60);
          content += `\n    → ${tc.name}(${argsShort})`;
        }
      }
      return `${role}: ${(content || "[empty]").slice(0, maxLen)}${maxLen < 120 ? "" : "…"} `;
    }
    case "compaction":
      return `[id:${entry.id.slice(0, 8)}] 📦 compaction (${(entry as any).tokensBefore ?? "?"} tokens)`;
    case "branch_summary":
      return `[id:${entry.id.slice(0, 8)}] ↪ branch summary from ${(entry as any).fromId?.toString().slice(0, 6)}`;
    case "custom_message":
      return `[id:${entry.id.slice(0, 8)}] ✉️ custom-msg (${entry.customType})`;
    case "custom":
      return `[id:${entry.id.slice(0, 8)}] ⚙️ custom (${entry.customType})`;
    case "label":
      return `[id:${entry.id.slice(0, 8)}] 🏷️ "${String(entry.label || "")}" → ${(entry.targetId ?? "").toString().slice(0, 6)}`;
    case "model_change": {
      const p = (entry.provider ?? "?").toString();
      const m = String((entry.modelId ?? "?")).slice(0, 20);
      return `[id:${entry.id.slice(0, 8)}] 🔄 model: ${p}/${m}`;
    }
    case "thinking_level_change":
      return `[id:${entry.id.slice(0, 8)}] 💭 thinking: ${(entry as any).thinkingLevel}`;
    case "session_info":
      return `[id:${entry.id.slice(0, 8)}] ℹ️ name: "${(entry as any).name || ""}"`;
    default:
      return `[${String(entry.id ?? "").slice(0, 6)}] ${entry.type}`;
  }
}

/** Render a tree to text for display */
function renderTree(nodes: TreeNode[], prefix = "", isLast = true): string {
  let out = "";
  const conn = isLast ? "└── " : "├── ";
  const cont = isLast ? "    " : "│   ";

  for (const node of nodes) {
    const formatted = formatEntry(node.entry);
    if (formatted.length > 120 && !formatted.includes("→")) {
      out += `${prefix}${conn}${formatted.slice(0, 115)}…\n`;
    } else {
      out += `${prefix}${conn}${formatted}\n`;
    }
    if (node.children.length > 0) {
      out += renderTree(node.children, prefix + cont, false);
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Pruning logic
// ---------------------------------------------------------------------------

/** Remove entries whose ids are in toRemove. Reparent orphans to null. */
function pruneEntries(entries: Record<string, unknown>[], toRemove: Set<string>): Record<string, unknown>[] {
  const result: Record<string, unknown>[] = [];

  for (const entry of entries) {
    // Header always kept
    if (entry.type === "session") {
      result.push(entry as any);
      continue;
    }

    // Skip pruned entries
    if (toRemove.has(entry.id)) continue;

    // Check if parent was removed — reparent to null
    const parentId = (entry.parentId ?? null) as string | null;
    let newEntry = entry;
    if (parentId && toRemove.has(parentId)) {
      newEntry = { ...entry, parentId: null };
    }

    result.push(newEntry as any);
  }

  return result;
}

// ---------------------------------------------------------------------------
// Summarization prompt template
// ---------------------------------------------------------------------------

const SUMMARIZE_INSTRUCTIONS = `You are a session cleanup assistant analyzing a Pi coding agent conversation.

## Goal
Review the entries below and decide what should be kept, summarized, or discarded from the active context window.

## Decision Rules
- **KEEP**: Critical requirements, architectural decisions with rationale, final agreed plans, key code patterns, unresolved issues/blockers
- **SUMMARIZE**: Back-and-forth discussions, iterative exploration/trial-error sequences, tool call chains where only outcomes matter, multiple responses on same topic → merge into single summary
- **DISCARD**: Trivial acknowledgments ("OK", "Got it"), duplicate questions already answered, repetitive tool calls without new info, very short exchanges adding nothing

## Output Format
Return ONLY valid JSON — no markdown fencing, no explanation:

[
  {"id": "<entry-id>", "action": "keep"|"summarize"|"discard"},
  {"id": "<entry-id>", "action": "summarize", "summary": "one-line summary"}
]

For summarize actions, provide a concise one-line summary. For keep/discard, omit the summary field.`;

// ---------------------------------------------------------------------------
// Extension factory
// ---------------------------------------------------------------------------

export default function (pi: ExtensionAPI) {
  // ==========================================================================
  // /session-prune — Remove abandoned branches from session tree
  // ==========================================================================
  pi.registerCommand("session-prune", {
    description: "Remove an abandoned branch from the current session tree",
    handler: async (args, ctx) => {
      const sm = ctx.sessionManager;
      await ctx.waitForIdle();

      const entries = sm.getEntries();
      if (entries.length <= 2) {
        return "Nothing to prune — session is linear or empty (header + ≤1 entry).";
      }

      // Build tree and find candidate nodes for pruning
      const { roots, map } = buildTree(entries);
      const allNodes: TreeNode[] = [];
      function collectAll(nodes: TreeNode[]) {
        for (const n of nodes) {
          // Include branch points (>1 child) and individual messages
          if (n.children.length > 1 || n.entry.type === "message") {
            allNodes.push(n);
          }
          collectAll(n.children);
        }
      }
      collectAll(roots);

      if (allNodes.length <= 1) {
        return "Nothing to prune — session has no branches.";
      }

      // Parse optional index argument from args or follow-up message
      let selectedIndex = -1;
      const trimmedArgs = String(args ?? "").trim();
      const numMatch = trimmedArgs.match(/^(\d+)$/);
      if (numMatch) {
        selectedIndex = parseInt(numMatch[1]) - 1; // convert 1-based to 0-based
      } else if (/^[-#]?\d+$/.test(trimmedArgs)) {
        // Accept #N or -N format too
        const dashNum = trimmedArgs.replace(/^[-#]/, "");
        const parsed = parseInt(dashNum);
        if (!isNaN(parsed)) selectedIndex = parsed - 1;
      }

      // Build display lines with numbered options
      const optionLines: string[] = [];
      for (let i = 0; i < allNodes.length; i++) {
        const n = allNodes[i];
        const text = formatEntry(n.entry).slice(45); // skip [id:] prefix in options
        const childCount = n.children.length;
        const marker = `  ${String(i + 1).padStart(2)}.`;
        optionLines.push(`${marker} [${n.entry.id.slice(0, 6)}] ${text}${childCount > 0 ? ` (+${childCount} children)` : ``}`);
      }

      // Build tree preview for context (first root only, truncated)
      const treePreview = renderTree(roots).split("\n").slice(0, 20).join("\n");

      if (selectedIndex < 0) {
        // No index provided — show options and ask user to reply with a number
        return [
          "=== Session Prune ===",
          "",
          "Available branches/messages:",
          ...optionLines,
          "",
          `Total: ${entries.length} entries | ${allNodes.length} candidates`,
          "",
          "Session structure (top levels):",
          treePreview.split("\n").length > 18 ? treePreview.slice(0, 700) + "…" : treePreview,
          "",
          "--- How to prune ---",
          "Reply to this message with the NUMBER of the entry you want to prune.",
          "Example: type \`3\` or \"/session-prune 3\" in your next message.",
          "This removes that node and all its descendants from the session file.",
        ].join("\n");
      }

      // Index provided — validate and proceed
      if (selectedIndex < 0 || selectedIndex >= allNodes.length) {
        return `Invalid index ${selectedIndex + 1}. Must be between 1 and ${allNodes.length}.`;
      }

      const selectedNode = allNodes[selectedIndex];
      const descendantIds = collectDescendantIds(selectedNode);

      // Preview what will be removed
      const previewLines: string[] = [];
      for (const id of Array.from(descendantIds).slice(0, 8)) {
        const n = map.get(id);
        if (n) previewLines.push(`    [${id}] ${formatEntry(n.entry).slice(45)}`);
      }
      const remaining = descendantIds.size - previewLines.length;

      ctx.ui.setStatus("session-cleanup", `Pruning ${descendantIds.size} entries…`);

      const confirmed = await ctx.ui.confirm(
        "Confirm prune",
        `Remove ${descendantIds.size} entry/entries?\n\nWill remove:\n${previewLines.join("\n")}${remaining > 0 ? `\n…and ${remaining} more` : ""}`,
      );

      if (!confirmed) {
        return "Prune cancelled by user.";
      }

      // Apply pruning to file
      try {
        const sessionFile = sm.getSessionFile();
        if (!sessionFile) throw new Error("No persisted session");

        const rawEntries = readSessionFile(sessionFile);
        const pruned = pruneEntries(rawEntries, descendantIds);
        writeSessionFile(sessionFile, pruned);

        ctx.ui.setStatus("session-cleanup", `✓ Removed ${descendantIds.size} entries`);
        setTimeout(() => ctx.ui.setStatus("session-cleanup"), 4000);
        return [
          `Removed ${descendantIds.size} entry/entries. Session file updated.`,
          "Note: restart pi session to load the cleaned-up state.",
        ].join("\n");
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return `Error during pruning: ${msg}`;
      }
    },
  });

  // ==========================================================================
  // /session-summarize — LLM-driven selective compaction
  // ==========================================================================
  pi.registerCommand("session-summarize", {
    description: "Send session to LLM for intelligent analysis and selective compacting",
    handler: async (_args, ctx) => {
      const sm = ctx.sessionManager;
      await ctx.waitForIdle();

      const entries = sm.getEntries();
      if (entries.length === 0) {
        return "No entries in session.";
      }

      // Count message types
      let userCount = 0, assistCount = 0, toolResultCount = 0;
      let firstUserText = "";
      for (const e of entries) {
        if (e.type !== "message") continue;
        const msg = (e as any).message;
        switch (msg?.role) {
          case "user":
            userCount++;
            if (!firstUserText && typeof msg.content === "string") firstUserText = msg.content.slice(0, 120);
            break;
          case "assistant": assistCount++; break;
          case "toolResult": toolResultCount++; break;
        }
      }

      // Serialize messages for LLM analysis
      let serialized = "";
      const messageEntries = entries.filter(e => e.type === "message");
      const maxShow = Math.min(messageEntries.length, 300); // cap to avoid overflow

      for (let i = 0; i < maxShow; i++) {
        const entry = messageEntries[i];
        if (!entry) continue;
        const msg = entry.message as Record<string, unknown>;
        const id = String(entry.id).slice(0, 8);
        const role = msg.role ?? "?";
        let content: string;

        if (typeof msg.content === "string") {
          content = msg.content.slice(0, 250).replace(/\n/g, " ");
        } else if (Array.isArray(msg.content)) {
          // Extract text blocks and tool calls separately
          const textBlocks = msg.content.filter((c: any) => c?.type === "text").map((c: any) => c.text).join(" ").slice(0, 250);
          const toolCalls = msg.content.filter((c: any) => c?.type === "toolCall");
          let tcs = "";
          for (const tc of toolCalls as any[]) {
            const argsStr = JSON.stringify(tc.arguments ?? {}).slice(0, 100);
            tcs += `\n    [${tc.name}](${argsStr})`;
          }
          content = textBlocks || `[no text]${tcs}`;
        } else {
          content = "[complex content]";
        }

        serialized += `${id} [${role}]: ${content}\n`;
      }

      if (messageEntries.length > maxShow) {
        serialized += `\n[... and ${messageEntries.length - maxShow} more entries]\n`;
      }

      ctx.ui.setStatus("session-cleanup", `Analyzing ${messageEntries.length} messages…`);

      // Build the analysis prompt with session context + serialized entries
      const analysisPrompt = `${SUMMARIZE_INSTRUCTIONS}\n\n--- SESSION ANALYSIS REQUEST ---\nSession has:\n  User messages: ${userCount}\n  Assistant responses: ${assistCount}\n  Tool results: ${toolResultCount}\n${firstUserText ? `\nFirst user message: "${firstUserText.slice(0, 120)}"\n` : ""}\nSerialized entries (id [role]: content):\n${serialized}\n--- END SESSION DATA ---`;

      try {
        await ctx.sendUserMessage(analysisPrompt);

        // Wait for agent to settle
        while (!ctx.isIdle()) {
          await new Promise(r => setTimeout(r, 500));
        }

        // Get the last assistant response text by scanning all entries
        let lastAssistantText = "";
        for (const entry of sm.getEntries()) {
          if (entry.type !== "message") continue;
          const msg = entry.message as Record<string, unknown>;
          if (msg.role !== "assistant") continue;
          if (typeof msg.content === "string") lastAssistantText = msg.content;
          else if (Array.isArray(msg.content)) {
            const tb = msg.content.find((c: any) => c?.type === "text");
            if (tb?.text) lastAssistantText = tb.text;
          }
        }

        // Try to extract JSON from the LLM response
        let jsonStr = lastAssistantText;
        const match = lastAssistantText.match(/```(?:json)?\s*\n([\s\S]*?)\n```/);
        if (match) jsonStr = match[1];

        let decisions: CleanupDecision[] | null = null;
        try {
          decisions = JSON.parse(jsonStr.trim());
        } catch {
          ctx.ui.notify("LLM returned non-JSON. Review manually.", "warning");
          return `Analysis complete.\n\n${lastAssistantText.slice(0, 3000)}\n\n(Could not parse as JSON for automatic application.)`;
        }

        if (!Array.isArray(decisions)) {
          return "Invalid decision format from LLM.";
        }

        // Categorize
        const keepIds = new Set<string>();
        const summarizeEntries: CleanupDecision[] = [];
        const discardIds = new Set<string>();

        for (const d of decisions) {
          switch (d.action) {
            case "keep": keepIds.add(d.id); break;
            case "summarize": summarizeEntries.push(d); if (d.summary) keepIds.add(d.id); else summarizeEntries.pop(); break;
            case "discard": discardIds.add(d.id); break;
          }
        }

        ctx.ui.setStatus("session-cleanup", `${keepIds.size} keep | ${summarizeEntries.length} summarize | ${discardIds.size} discard`);

        const confirmed = await ctx.ui.confirm(
          "Apply session cleanup?",
          `LLM analysis:\n  Keep:      ${keepIds.size}\n  Summarize: ${summarizeEntries.length}\n  Discard:   ${discardIds.size}\n\nProceed with these changes?`,
        );

        if (!confirmed) return "Cleanup cancelled.";

        // Apply decisions to the file
        try {
          const sf = sm.getSessionFile();
          if (!sf) throw new Error("No persisted session");

          // Re-read current state; appended analysis/LLM entries have no matching IDs and default to 'keep'
          const allEntries = readSessionFile(sf);
          const decisionMap = new Map(decisions.map(d => [d.id, d]));
          let removedCount = 0;
          const result: Record<string, unknown>[] = [];

          for (const entry of allEntries) {
            if (entry.type === "session") {
              result.push(entry as any);
              continue;
            }

            const action = decisionMap.get(entry.id)?.action ?? "keep";

            if (action === "discard") {
              removedCount++;
              continue;
            }

            if (action === "summarize" && entry.type === "message") {
              // Replace message with a compacted version
              const origMsg = (entry as any).message;
              const summaryDec = decisions.find(d => d.id === entry.id);
              const replacement: Record<string, unknown> = {
                type: "compaction",
                id: `${entry.id}-compact`,
                parentId: entry.parentId,
                timestamp: Date.now(),
                summary: `Summarized: ${summaryDec?.summary || "[no summary]"}`,
                tokensBefore: 100,
                details: {},
              };

              if (origMsg?.usage) replacement.usage = origMsg.usage;
              result.push(replacement as any);
            } else {
              result.push(entry as any);
            }
          }

          writeSessionFile(sf, result);

          ctx.ui.setStatus("session-cleanup", `✓ Applied (${removedCount} removed), restart session to load changes`);
          setTimeout(() => ctx.ui.setStatus("session-cleanup"), 4000);
          return `Cleanup applied: ${discardIds.size} discarded, ${summarizeEntries.length} summarized.`;
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          return `Error applying cleanup: ${msg}`;
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return `Analysis failed: ${msg}`;
      }
    },
  });

  // ==========================================================================
  // /session-compact-focused — Wrapper around pi's built-in compact
  // ==========================================================================
  pi.registerCommand("session-compact-focused", {
    description: "Compact session with custom focus instructions for selective summarization",
    handler: async (_args, ctx) => {
      const sm = ctx.sessionManager;
      await ctx.waitForIdle();

      const entries = sm.getEntries();
      let userCount = 0, assistCount = 0;
      for (const e of entries) {
        if (e.type !== "message") continue;
        const role = ((e as any).message?.role ?? "") as string;
        if (role === "user") userCount++;
        else if (role === "assistant") assistCount++;
      }

      // Prompt user for compact focus instructions
      ctx.ui.setStatus("session-cleanup", "Enter compact focus instructions…");

      const instructions = await ctx.ui.input(
        "Compact Focus Instructions",
        `Session has ${entries.length} entries (${userCount} user, ${assistCount} assistant).\nWhat should the summary prioritize?`,
      );

      ctx.ui.setStatus("session-cleanup");

      if (!instructions) return "Compact cancelled.";

      try {
        await ctx.sendUserMessage(`/compact ${instructions}`);

        while (!ctx.isIdle()) {
          await new Promise(r => setTimeout(r, 500));
        }

        const name = sm.getSessionName() || "(unnamed)";
        return `Compacted session "${name}" with focus: "${instructions.slice(0, 120)}"`;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return `Compact failed: ${msg}`;
      }
    },
  });

  // ==========================================================================
  // /session-stats — Session statistics overview
  // ==========================================================================
  pi.registerCommand("session-stats", {
    description: "Show detailed session statistics and structure overview",
    handler: async (_args, ctx) => {
      const sm = ctx.sessionManager;
      await ctx.waitForIdle();

      const entries = sm.getEntries();
      const header = sm.getHeader() as Record<string, unknown>;
      const name = sm.getSessionName();
      const leafEntry = sm.getLeafEntry();

      let userMsgs = 0, assistMsgs = 0, toolResultMsgs = 0;
      let compactionCount = 0, branchSummaryCount = 0;

      for (const e of entries) {
        switch (e.type) {
          case "message": {
            const role = ((e as any).message?.role ?? "") as string;
            if (role === "user") userMsgs++;
            else if (role === "assistant") assistMsgs++;
            else if (role === "toolResult") toolResultMsgs++;
            break;
          }
          case "compaction": compactionCount++; break;
          case "branch_summary": branchSummaryCount++; break;
        }
      }

      // Count total tokens from usage data
      let totalTokens = 0;
      for (const e of entries) {
        if (e.type === "message" && (e as any).message?.usage) {
          totalTokens += ((e as any).message.usage.totalTokens ?? 0);
        }
      }

      return [
        `Session: ${name || "(unnamed)"}`,
        `ID: ${(header as any)?.id ?? "?"}`,
        `File: ${sm.getSessionFile() ?? "ephemeral"}`,
        `Leaf: ${leafEntry?.id.slice(0, 8) || "(none)"}`,
        "",
        `Entries:    ${entries.length} total`,
        `  Messages:   ${userMsgs + assistMsgs + toolResultMsgs} (U:${userMsgs} A:${assistMsgs} TR:${toolResultMsgs})`,
        `  Compactions:     ${compactionCount}`,
        `  Branch summaries:${branchSummaryCount}`,
        `  Total tokens:    ${totalTokens.toLocaleString()}`,
      ].join("\n");
    },
  });

  // ==========================================================================
  // Cleanup on shutdown
  // ==========================================================================
  pi.on("session_shutdown", (_event, ctx) => {
    try {
      ctx.ui.setWidget("session-cleanup", undefined);
      ctx.ui.setStatus("session-cleanup");
    } catch { /* ignore during shutdown */ }
  });
}
