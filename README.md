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
✅ Context memory - remembers conversation history
✅ Mood-based responses (Struggling, Low, Okay, Good, Great)
✅ Grounding exercises and coping strategies
✅ Crisis resources and support information
✅ Beautiful glass-morphism UI design

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
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
Final Chatbot/
├── backend/
│   ├── api_server.py      # Flask API server with context memory
│   ├── tom_chatbot.py     # SVM-based chatbot engine
│   ├── data.json          # Training data and responses
│   └── requirements.txt   # Python dependencies
│
├── Frontend/
│   ├── src/
│   │   ├── App.tsx        # Main chat application
│   │   └── ...
│   ├── vite.config.ts     # Vite configuration
│   └── package.json       # Frontend dependencies
│
├── README.md             # This file
└── .gitignore
```

---

## 🎨 Features in Detail

### 💬 Conversation Context
TOM remembers the last 5 exchanges in your conversation, making responses more relevant:

```
You: "I'm feeling anxious"
TOM: "Anxiety can feel overwhelming... let's try breathing..."

You: "What should I do?"
TOM: "I understand you want more ways to cope with anxiety..." ✅
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
| GET | `/api/health` | Health check |

### Chat Request Format
```json
{
  "message": "Your message here",
  "session_id": "optional-browser-session-id"
}
```

### Chat Response Format
```json
{
  "response": "TOM's reply",
  "intent": "detected_intent",
  "risk_level": "low" | "high"
}
```

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

For **context-aware** responses, use this format:
```json
{
  "tag": "followup_new_intent",
  "patterns": [
    "Following up on: 'previous message'. Now: current question"
  ],
  "responses": ["context-aware reply"]
}
```

---

## 🛠️ Customization

### Change Port
Edit `api_server.py` line:
```python
app.run(host='0.0.0.0', port=8000, debug=False)
```

### Change API URL (Frontend)
Create `.env` in Frontend folder:
```
VITE_API_BASE_URL=http://your-backend-url:port
```

---

## 🚀 Deployment

### Backend (Render.com)
1. Create new Web Service
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python api_server.py`
5. Deploy!

### Frontend (Vercel)
1. Import project from GitHub
2. Set environment variable: `VITE_API_BASE_URL=https://your-render-url.onrender.com`
3. Deploy!

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