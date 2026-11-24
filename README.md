# <img src="assets/logo.png" alt="TOM Logo" width="22" height="22" /> TOM — Talk To Me (Local Edition)

> **A 100% offline, privacy-first AI mental health companion powered by Ollama and Theory of Mind (ToM) state classification.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2%3A3b-black?style=flat-square&logo=ollama&logoColor=white)](https://ollama.ai)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite 6](https://img.shields.io/badge/Vite-6.2-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4.0-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Privacy 100% Local](https://img.shields.io/badge/Privacy-100%25_Offline-2ea44f?style=flat-square&logo=shield&logoColor=white)](#-safety--ethical-disclaimer)

---

## 💡 Overview

University and daily student life often come with high academic stress, loneliness, and pressure from family or peers. While speaking with someone helps, many students hesitate to share personal thoughts due to privacy concerns, judgment, or social stigma.

**TOM (Talk To Me)** is a lightweight, local-first companion created to offer a safe, supportive space right on your computer.

- **100% Offline & Private:** No messages, chats, or personal mood logs ever leave your machine.
- **Theory of Mind (ToM) Inferred Context:** Detects subtle emotional states (`exam_stress`, `family_pressure`, `loneliness`, `anxiety`, `sadness`) from English and Hinglish expressions.
- **Empathetic Local Intelligence:** Powered by `llama3.2:3b` running entirely via Ollama on your device.
- **Built-in Safety Guardrails:** Instant deterministic routing for crisis disclosures, connecting users directly with verified regional support lines.

---

## ✨ Features

- **🧠 State Classification (ToM):** Character-level n-gram TF-IDF + Logistic Regression trained on code-mixed student conversations.
- **🦙 Local LLM Generation:** Warm, concise, and non-judgmental conversational responses via Ollama.
- **📊 Mood Analytics Dashboard:** Interactive breakdown of daily emotional check-ins, trends, and self-care recommendations.
- **💬 Multi-Session Chat:** Start fresh topics, switch sessions seamlessly, or delete your data with one click.
- **🌿 Instant Grounding Tools:** Instant guides for Box Breathing (4-4-4-4), 5-4-3-2-1 Sensory Grounding, and Mindful Minutes.
- **🗣️ Natural English & Hinglish:** Understands conversational phrasing (e.g., *"syllabus nahi ho raha"*, *"feeling left out"*, *"ghar wale expect kar rahe hain"*).
- **🚨 Verified Safety Fallback:** Bypasses LLM generation during crisis disclosures, immediately displaying verified crisis helplines.

---

## 🛠️ How It Works

```text
User Message (English / Hinglish)
   │
   ├─► [1] Crisis Regex Filter ──► Verified Emergency Helplines (Immediate)
   │
   ├─► [2] Grounding Triggers   ──► Instant Guided Breathing / Grounding
   │
   └─► [3] Theory of Mind ML    ──► Updates Local Mood Stats
            │
            ▼ (Inferred Context Clue)
       [4] Local Ollama Engine (llama3.2:3b)
            │
            ▼
       [5] Friendly Response in React 19 UI
```

---

## 📁 Project Structure

```text
Local TOM/
├── assets/
│   └── logo.png              # Project logo & icon
├── backend/                  # Local ASGI API & Machine Learning
│   ├── server.py             # Starlette server + Ollama & ML bridge
│   ├── train.py              # ML retraining script
│   ├── data.csv              # Student distress training dataset
│   ├── model.pkl             # Serialized classifier pipeline
│   ├── mood_log.csv          # Local private mood logs (git-ignored)
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Modern React 19 + TypeScript web app
│   ├── src/
│   │   ├── App.tsx           # Chat layout, sidebar, & session manager
│   │   ├── MoodDashboard.tsx # Wellbeing analytics dashboard
│   │   ├── LandingPage.tsx   # Welcome screen
│   │   ├── api.ts            # Local backend client & health monitor
│   │   └── types.ts          # Shared TypeScript definitions
│   ├── package.json          # Frontend dependencies
│   └── vite.config.ts        # Vite configuration
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 20+** & **npm**
- **Ollama**: [Download Ollama](https://ollama.ai)

---

### Step 1: Start Ollama

Open a terminal and start the Ollama service:

```bash
ollama serve
```

In a separate terminal, pull the 3B model (one-time download, ~2.0 GB):

```bash
ollama pull llama3.2:3b
```

---

### Step 2: Start the Backend

```bash
cd backend
pip install -r requirements.txt
python3 server.py
```

The backend starts at `http://127.0.0.1:8000`.  
*(Tip: You can also start it directly from the project root using `python3 backend/server.py`).*

---

### Step 3: Start the Frontend

In a new terminal window:

```bash
cd frontend
npm install
npm run dev
```

Open your browser at **`http://localhost:5173`**.

---

## 🧘 Quick Wellness Triggers

Type any of these commands in the chat for immediate, zero-latency grounding:

| Phrase | Action |
| :--- | :--- |
| `Breathing exercise` | Guided Box Breathing (4-4-4-4) |
| `Grounding technique` or `5-4-3-2-1` | 5-4-3-2-1 Sensory Grounding exercise |
| `Meditation` | 60-Second Mindful Minute |
| `Coping strategies` | Practical everyday wellbeing steps |

---

## 🧠 Retraining the State Classifier

To customize or expand the mental state dataset:

1. Add your phrases to `backend/data.csv`:
   ```csv
   text,label
   aaj padhai mein man nahi lag raha,exam_stress
   feeling so disconnected from everyone,loneliness
   ```
2. Run the training script:
   ```bash
   cd backend
   python3 train.py
   ```
   A refreshed `backend/model.pkl` will be exported with an updated classification report.

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health status and loaded Ollama model |
| `POST` | `/api/chat` | Send user message (`{ message, session_id, mood_label? }`) |
| `GET` | `/api/mood/stats` | Retrieve local check-in statistics and top emotion |
| `POST` | `/api/mood/reset` | Clear stored mood check-ins |

---

## ⚠️ Safety & Ethical Disclaimer

> **TOM is an educational AI wellbeing companion and is NOT a medical device, therapist, or emergency helpline.**  
> It does not diagnose, treat, or replace professional mental health care.

If you or someone you know is in distress or having thoughts of self-harm, please reach out to trusted people or professional emergency support:

- 🇮🇳 **India:** Tele-MANAS (`14416` — 24/7 Toll-Free) | KIRAN (`1800-599-0019`) | National Emergency (`112`)
- 🇺🇸 / 🇨🇦 **US & Canada:** Suicide & Crisis Lifeline (`988`) | Crisis Text Line (Text `HOME` to `741741`)
- 🇬🇧 **UK:** Samaritans (`116 123`) | Shout (Text `SHOUT` to `85258`)
- 🌍 **International:** [findahelpline.com](https://findahelpline.com) or [befrienders.org](https://www.befrienders.org)

---

## 📄 License

Open-source under the MIT License for educational and personal wellbeing use.
