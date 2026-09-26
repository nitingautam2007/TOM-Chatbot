# Frontend — TOM

React + Vite + Tailwind CSS client for TOM.

## Run

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

## Build

```powershell
npm run build      # outputs to dist/
npm run preview
```

## Test

```powershell
npm test           # vitest + @testing-library/react (jsdom)
```

## Configuration

The API base URL defaults to `http://127.0.0.1:8000` and can be overridden:

```powershell
# frontend/.env.local
VITE_API_URL=http://localhost:8000
```

## Structure

- `pages/` — route-level composition (Home, Chat, Screening, Exercises, Dashboard)
- `components/common` — Button, Card, LoadingIndicator, EmptyState, ErrorBanner, SectionLabel, StatusBadge
- `components/layout` — Layout, Navbar, Footer
- `components/chat` — ChatWindow, ChatMessage, ChatInput
- `components/exercises` — ExerciseCard, ExercisePlayer, ExerciseFeedback (Phase 10)
- `data/exercises.js` — static exercise content (no API, no storage)
- `services/api.js` — **all** HTTP communication (Axios), including
  `sendChatMessage(message, conversationId)` and conversation endpoints
- `hooks/` — `useChat` keeps `conversation_id`, restores persisted history
  after refresh, recovers from a stale id (404 → fresh conversation), and
  owns loading/error state
- `test/` — vitest setup + component tests (chat, IME input, Dashboard, exercises)
