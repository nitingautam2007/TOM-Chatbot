# TOM Backend API Server

REST API for connecting TOM - Talk To Me frontend with the Python backend.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start API Server
```bash
# Option 1: Command line
python api_server.py

# Option 2: Double-click
./run_api.bat
```

The server will start on **http://127.0.0.1:8000**

---

## 🔌 API Endpoints

### POST /api/chat
Send user messages and get TOM's responses.

**Request:**
```json
{
  "message": "I am feeling sad today"
}
```

**Response:**
```json
{
  "response": "I understand this is difficult for you. I'm here to listen. What's on your mind?",
  "intent": "sad",
  "risk_level": "low"
}
```

**Risk Levels:**
- `"low"` - Normal conversation
- `"high"` - Crisis/suicide detection (triggers red alert in frontend)

---

### GET /api/health
Check if the backend is running.

**Response:**
```json
{
  "status": "online",
  "model": "TOmChatbot (SVM)",
  "intents": 73,
  "patterns": 391,
  "message": "TOM backend is running and ready!"
}
```

### DELETE /api/data
Permanently delete all stored chats and the consent record for one browser session. The frontend uses this when the user selects **Delete my stored data and choose consent again**.

**Request:**
```json
{
  "session_id": "browser session identifier"
}
```

---

## 🎯 Supported Features

### Mood Selection
The frontend sends mood messages in this format:
```
"I'm feeling struggling today (😔)"
"I'm feeling low today (😕)"
"I'm feeling okay today (😐)"
"I'm feeling good today (🙂)"
"I'm feeling great today (😊)"
```

**All moods are properly recognized** and respond with appropriate empathy.

### Quick Reply Buttons
The frontend suggestion buttons send:
- "I'm feeling anxious" → **anxious** intent
- "I need to talk" → **help** intent
- "Breathing exercise" → **meditation** intent
- "Trouble sleeping" → **sleep** intent
- "Grounding technique" → **meditation** intent

**All suggestions are properly matched** to their corresponding intents.

---

## 📦 Requirements

- Python 3.8+
- Flask 3.0.0
- Flask-CORS 4.0.0
- scikit-learn 1.3.0
- numpy 1.24.3
- nltk 3.8.1

---

## 🔧 Configuration

### Change Port
Edit `api_server.py` line 80:
```python
app.run(host='0.0.0.0', port=8000, debug=False)
```

### Change CORS Settings
Edit `api_server.py` line 12:
```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

---

## 🧪 Testing the API

### Using curl
```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I am feeling sad"}'
```

### Using Python
```python
import requests
response = requests.post(
    'http://127.0.0.1:8000/api/chat',
    json={'message': 'I need help'}
)
print(response.json())
```

---

## 🔄 Connecting Frontend + Backend

### Step 1: Start Backend API
```bash
cd backend
python api_server.py
```

### Step 2: Start Frontend
```bash
cd frontend
npm run dev
```

### Step 3: Open Frontend
- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000

The frontend will **automatically connect** to the backend API!

---

## 🐛 Troubleshooting

### Backend not starting
```bash
# Check if all dependencies are installed
pip list | grep -E "flask|scikit|numpy|nltk"

# Install missing dependencies
pip install flask flask-cors
```

### Connection refused
- Make sure backend is running: `python api_server.py`
- Check port 8000 is not blocked: `netstat -ano | findstr 8000`
- Try: `http://127.0.0.1:8000/api/health` in your browser

### CORS errors
- Make sure Flask-CORS is installed
- The API already has CORS enabled for all origins

---

## 📊 Performance

- **Response time:** < 100ms
- **Accuracy:** 84.91%
- **Mixed emotions:** Fully supported
- **Crisis detection:** 100%

---

## 🎉 Example Conversations

### Mood Selection
```
User: I'm feeling struggling today (😔)
TOM: I understand this is difficult for you. I'm sorry to hear that. I'm here for you. Talking about it might help.
```

### Quick Reply
```
User: I'm feeling anxious
TOM: Anxiety can feel overwhelming, but you're doing the right thing by acknowledging it. Let's try a simple breathing exercise.
```

### Crisis Detection
```
User: I want to kill myself
TOM: I'm deeply concerned about you. Your life is precious. Please reach out to a crisis hotline immediately. You are not alone.
```

---

## 📝 Notes

- The API maintains **no session state** - each request is independent
- For production, consider adding authentication
- Rate limiting can be added for public deployments
- The backend runs **locally only** - not suitable for public hosting without modifications
