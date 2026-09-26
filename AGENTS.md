## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## archify

Architecture diagrams live under `docs/architecture/` (HTML) with sources under `docs/architecture/sources/*.architecture.json`.

Rules:
- Prefer opening an existing diagram over inventing one; regenerate with `node scripts/archify.mjs build` (wraps `archify validate` + `archify deliver` from the installed skill, patches wheel zoom into the HTML, and deletes Archify's `*.visual-check.*` sidecars). Never run `archify visual-check` directly against `docs/architecture/`.
- Nodes/edges must be evidence-based (existing code paths). Do not add Phase 9 / external-AI / auth nodes unless they are in the repo.
- `docs/architecture/README.md` is the index.
