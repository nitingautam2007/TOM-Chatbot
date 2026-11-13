# TOM - Talk To Me

> **TOM (Talk To Me)** - A mental health support AI chatbot companion. A safe, judgment-free space for emotional support and wellbeing conversations.

---

## 🎯 About TOM

TOM is a **mental health companion chatbot** built with:
- **Backend:** Python + Flask + Scikit-learn (SVM classifier)
- **Frontend:** React + TypeScript + Vite
- **Features:** Context-aware conversations, mood tracking, support resources

### Key Features
✅ Natural language understanding with SVM
✅ Short-lived session context with automatic expiry
✅ Mood-based responses (Struggling, Low, Okay, Good, Great)
✅ Grounding exercises and coping strategies
✅ Deterministic crisis handling with regional support information
✅ Consent, privacy, and data-deletion controls
✅ Offline recovery with a local crisis fallback
✅ Beautiful glass-morphism UI design

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 22+ (required for the frontend test command; Vite 8 needs a modern Node release)
- pip & npm

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python api_server.py
```

Backend runs at: `http://127.0.0.1:8000`

### Frontend Setup
```bash
cd Frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## 📁 Project Structure

```
TOM/
├── backend/
│   ├── api_server.py      # Flask API server with context memory
│   ├── config.py          # Environment-driven production settings
│   ├── observability.py   # JSON request logging and request IDs
│   ├── wsgi.py            # Gunicorn entrypoint
│   ├── gunicorn.conf.py   # Single-worker, threaded production config
│   ├── tom_chatbot.py     # SVM-based chatbot engine
│   ├── data.json          # Training data and responses
│   ├── tests/             # Backend unittest suite
│   └── requirements.txt   # Python dependencies
│
├── Frontend/
│   ├── src/
│   │   ├── App.tsx        # Main chat application
│   │   └── ...
│   ├── vite.config.ts     # Vite configuration
│   ├── vercel.json        # Vercel static deployment config
│   └── package.json       # Frontend dependencies
│
├── .github/workflows/ci.yml # Backend and frontend CI
├── DEPLOYMENT.md          # Render + Vercel deployment guide
├── render.yaml            # Render backend blueprint
├── README.md              # This file
└── .gitignore
```

---

## 🎨 Features in Detail

### 💬 Conversation Context
TOM keeps a short-lived server-side session cache (up to 10 messages) in memory only. It expires after 30 minutes of inactivity, is cleared when you start a new conversation or delete your data, and is never written to disk. The app does not keep a durable chat archive.

```
You: "I'm feeling anxious"
TOM: "Anxiety can feel overwhelming... let's try breathing..."

You: "What should I do?"
TOM: "I hear you. Let's find a coping step that feels manageable right now."
```

### 😊 Mood Selection
Start your conversation by selecting how you feel:
- 😔 Struggling
- 😕 Low
- 😐 Okay
- 🙂 Good
- 😊 Great

### 🧘 Wellbeing Resources
- Grounding techniques (5-4-3-2-1 method)
- Breathing exercises (Box breathing)
- Crisis support contacts
- Self-care suggestions

### 🎭 UI Design
- Glass-morphism card design
- Smooth animations
- Responsive layout
- Dark/light theme ready

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send messages and get responses |
| POST | `/api/session/reset` | Forget one session's context |
| DELETE | `/api/data` | Delete one session's server-side data |
| GET | `/api/health` | Health check and model metrics |
| GET | `/api/ready` | Readiness check (503 until the model is loaded) |

### Chat Request Format
```json
{
  "message": "Your message here",
  "session_id": "optional-anonymous-session-id",
  "region": "IN"
}
```

`region` is one of `IN`, `US_CA`, `UK`, or `INTL`.

### Chat Response Format
```json
{
  "response": "TOM's reply",
  "intent": "sadness",
  "risk_level": "low",
  "resources": [],
  "region": "IN",
  "session_id": "anonymous-session-id",
  "confidence": 0.61,
  "source": "classifier"
}
```

Crisis responses add `risk_reasons` and regional `resources`. See
[`backend/API_README.md`](backend/API_README.md) for the full contract, error
codes, rate limits, and session lifetimes.

---

## 📦 Adding New Training Data

Edit `backend/data.json` to add new conversation patterns:

```json
{
  "tag": "new_intent",
  "patterns": ["user message 1", "user message 2"],
  "responses": ["bot reply 1", "bot reply 2"]
}
```

Tags are canonicalised in code, so prefer one canonical tag (for example
`anxiety`) instead of adding near-duplicates such as `anxious`. Synthetic
`followup_*` intents are excluded from training, and factual `fact-*` /
`*_info` intents belong in the FAQ index rather than the classifier.

---

## 🛠️ Customization

### Change Port
Set `TOM_PORT` before starting the backend:
```bash
TOM_PORT=9000 python api_server.py
```

### Change API URL (Frontend)
Create `.env` in the Frontend folder:
```
VITE_TOM_API_URL=http://your-backend-url:port
```

---

## 🏠 Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
python api_server.py
```

### Frontend
```bash
cd Frontend
npm install
npm run dev
```

### Tests
```bash
cd backend
.venv/bin/python -m unittest discover -s tests -v

cd ../Frontend
npm test
npx tsc --noEmit
npm run build
```

---

## 🚀 Deployment

TOM is configured for a Render backend and a Vercel frontend:

- `render.yaml` deploys the API with gunicorn.
- `Frontend/vercel.json` deploys the static frontend with security headers.
- `.github/workflows/ci.yml` runs backend and frontend checks on every pull
  request.

Production requires `TOM_ENV=production`, a random `TOM_SECRET_KEY` of at least
32 characters, and an explicit `TOM_CORS_ORIGINS` allowlist. The server refuses
to start if those values are missing or unsafe.

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the full setup, environment variables,
verification steps, rollback, and scaling limits. Session context and rate
limits are in process memory, so the production configuration runs one gunicorn
worker with threads.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available for educational use.

---

## 🙏 Acknowledgments

- Built with Flask, React, and Scikit-learn
- Inspired by mental health support principles
- Designed for educational and personal wellbeing use

---

**TOM is not a substitute for professional mental health care.**

If you or someone you know is in crisis, please contact:
- **USA/Canada:** Call or text 988 (Suicide & Crisis Lifeline)
- **UK:** Text SHOUT to 85258
- **International:** Find a crisis line at befrienders.org

---