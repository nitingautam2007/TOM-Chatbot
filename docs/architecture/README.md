# TOM Architecture Diagrams

Seven diagrams. The tech-stack overview is hand-written and self-contained; the six
detailed diagrams are Archify-generated with sources under `sources/` as the source of
truth. Regenerate those through the project-local wrapper:

```bash
node scripts/archify.mjs build          # validate + deliver all six, patch wheel zoom, drop sidecars
node scripts/archify.mjs verify         # headless-Chrome check of wheel zoom / drag pan / reset
node scripts/archify.mjs visual-check   # browser containment evidence on temp copies (nothing lands here)
```

The wrapper exists because Archify has no option to keep its `visual-check` sidecars
(`*.visual-check.*.png`, `*.visual-check.html`, `*.visual-check.json`) out of the output
directory. It deletes them after every build, so `archify visual-check` should never be run
directly against this directory. The installed skill itself is never modified.

Install it once if it is missing:

```bash
npx -y skills add tt-a1i/archify --skill archify --agent opencode --global --copy --yes
```

Only `README.md`, `sources/*.architecture.json`, the six Archify `.architecture.html`
files, and the hand-written `tom-tech-stack.architecture.html` belong in this directory.

| Diagram | HTML | Source |
|---------|------|--------|
| ⭐ **Tech stack overview** | [tom-tech-stack.architecture.html](tom-tech-stack.architecture.html) | this repository (hand-written, no `sources/` entry) |
| High-level architecture | [tom-highlevel.architecture.html](tom-highlevel.architecture.html) | [sources/tom-highlevel.architecture.json](sources/tom-highlevel.architecture.json) |
| Chat request flow | [tom-chatflow.architecture.html](tom-chatflow.architecture.html) | [sources/tom-chatflow.architecture.json](sources/tom-chatflow.architecture.json) |
| PHQ-9 screening flow | [tom-phq9.architecture.html](tom-phq9.architecture.html) | [sources/tom-phq9.architecture.json](sources/tom-phq9.architecture.json) |
| Safety detection pipeline | [tom-safety.architecture.html](tom-safety.architecture.html) | [sources/tom-safety.architecture.json](sources/tom-safety.architecture.json) |
| Local NLP pipeline | [tom-nlp.architecture.html](tom-nlp.architecture.html) | [sources/tom-nlp.architecture.json](sources/tom-nlp.architecture.json) |
| Data flow & persistence | [tom-dataflow.architecture.html](tom-dataflow.architecture.html) | [sources/tom-dataflow.architecture.json](sources/tom-dataflow.architecture.json) |

## Viewer controls

Each diagram is a self-contained HTML file. Open it in any browser:

- **Zoom in / out** — toolbar buttons, mouse wheel over the canvas, or `+` / `-`
- **Pan** — click and drag once zoomed past 100%
- **Reset / fit to screen** — the reset button or `0`
- **Theme, style, guide, find** — `T`, `S`, `?`, `/`

Wheel scroll over the canvas zooms instead of scrolling the page; the diagram stays
inside the viewport and large diagrams pan rather than growing the page.

### Tech stack overview controls

`tom-tech-stack.architecture.html` is hand-written, so its controls differ slightly:

- **Click any box** — opens the detail drawer (purpose, version, repo files, inputs/outputs,
  connections, dependencies, runtime vs development tooling)
- **Click empty canvas** or `Esc` — closes the drawer
- **Zoom** — toolbar `+` / `-`, mouse wheel (scroll up zooms in), or `+` / `-` keys
- **Pan** — click and drag
- **Fit / reset** — `FIT` / `RESET` buttons, or `F` / `0`

Nodes and edges are evidence-based (repo file paths / code paths). PLANNED work (auth, external AI APIs, mood tracking) is intentionally omitted.
