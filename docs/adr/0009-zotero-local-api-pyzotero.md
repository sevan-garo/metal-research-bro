# 0009 — pyzotero against Zotero's local API, not zotero-mcp or the Web API

## Context

The spec allowed either `zotero-mcp` (an existing MCP server wrapping
pyzotero) or `pyzotero` directly as a fallback. Two separate choices were
actually involved:

1. **Transport**: talk to Zotero's Web API (network, needs an API key from
   zotero.org) vs. Zotero desktop's local API (`http://localhost:23119/api`,
   no key, but only reachable while the app is running).
2. **Integration path**: go through the `zotero-mcp` server over the MCP
   protocol, or call `pyzotero` directly in-process.

## Decision

- **Local API** (`zotero.Zotero(library_id="0", library_type="user",
  local=True)`). Requires enabling Zotero > Settings > Advanced > "Allow other
  applications on this computer to communicate with Zotero". No API key to
  provision or leak, and library data never leaves the machine — consistent
  with the local-first stance already taken for the LLM (ADR 0003) and
  embeddings.
- **pyzotero directly**, not `zotero-mcp`. This is a single-process LangGraph
  application; `zotero-mcp` exists to expose Zotero to *external* MCP clients
  (Claude Desktop, Claude Code, etc.) over stdio/JSON-RPC. Going through it
  here would mean spawning a subprocess and speaking MCP to reach a library
  that pyzotero can already call as a plain Python function — extra protocol
  overhead with no capability gained, for a tool that only this process uses.

## Consequences

- `tools/zotero_tool.py` has no credentials to manage at all for the POC.
  Trade-off: it only works while the Zotero desktop app is running, which is
  an acceptable constraint for a single-user local tool but would need
  revisiting (Web API + stored key) for any server-side/always-on deployment.
- **Local API quirk found empirically**: the Web API's boolean `itemType`
  syntax (`itemType=-attachment && -note`) does *not* filter on the local
  API — a live test returned attachments unfiltered with the combined
  expression, but filtered correctly with a single `itemType=-attachment`.
  `search_zotero` uses the single-exclusion form and filters out notes
  client-side instead of relying on the local API to combine both. Worth
  re-checking if a future Zotero version changes local API parity with the
  Web API.
- If `zotero-mcp` (or any other MCP tool) needs to be exposed to Claude Code
  or another MCP client for interactive exploration of this same library,
  that can be configured independently later — it's an orthogonal concern
  from this application's own `search_zotero` tool.
