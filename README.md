# 💙 TOM — Talk To Me (Local Edition)

> **A 100% Offline, Privacy-Preserving AI Mental Health Companion powered by Ollama and Theory of Mind (ToM).**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2%3A3b-black?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite 6](https://img.shields.io/badge/Vite-6.2-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![TailwindCSS v4](https://img.shields.io/badge/Tailwind_CSS-v4.0-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Privacy First](https://img.shields.io/badge/Privacy-100%25_Local-success?style=for-the-badge&logo=shield&logoColor=white)](#-privacy--safety)

---

## 🎯 About Local TOM

**TOM (Talk To Me)** is a lightweight, local-first mental health companion designed specifically for students and individuals seeking a safe, judgment-free space to unpack thoughts and emotions.

While traditional conversational agents rely on third-party cloud APIs (posing privacy concerns for sensitive disclosures), **Local TOM runs entirely on your own machine**. It combines a **statistical Theory of Mind (ToM) mental state classifier** with **local LLM generation via Ollama** and a deterministic crisis interception pipeline.

---

## 🌟 Key Features

* 🧠 **Theory of Mind (ToM) State Inference**: Automatically detects underlying distress states (`exam_stress`, `family_pressure`, `loneliness`, `anxiety`, `sadness`) from code-mixed English and Hinglish text using character-level n-gram TF-IDF and Logistic Regression.
* 🦙 **Local LLM Intelligence (Ollama)**: Dynamic, empathetic, context-aware student support powered locally by `llama3.2:3b`.
* 🛡️ **Zero-Data-Leakage Architecture**: No messages, mood logs, or embeddings ever leave your device.
* 🚨 **Deterministic Crisis Guardrails**: Bypasses the LLM during self-harm or emergency disclosures, immediately surfacing verified regional helplines (**Tele-MANAS: 14416**, **KIRAN: 1800-599-0019**, **112**).
* 🌿 **Instant Wellness & Grounding Modules**: Built-in deterministic guides for **Box Breathing (4-4-4-4)**, **5-4-3-2-1 Sensory Grounding**, **Mindful Minutes**, and coping toolkits.
* 🗣️ **Native Hinglish & English Code-Switching**: Recognizes and responds to colloquial student expressions (e.g., *"syllabus khatam nahi hua"*, *"bahut tension ho rahi hai"*, *"ghar waale taane marte hain"*).
* 🎨 **Glassmorphic React 19 Interface**: Calming, modern UI built with React, Vite, and Tailwind CSS v4, featuring mood trackers and interactive resources.

---

## 🏗️ System Architecture

```
[ User Input (English / Hinglish) ]
                 │
                 ├──► [ 1. Crisis Interceptor (Regex Engine) ]
                 │         │ (Matched)
                 │         ▼
                 │    [ Immediate Verified Helpline Card ]
                 │    (Tele-MANAS 14416 / KIRAN / 112)
                 │
                 ├──► [ 2. Deterministic Wellness Triggers ]
                 │         │ (e.g., "breathing exercise", "5-4-3-2-1")
                 │         ▼
                 │    [ Instant Grounding Guidance (0ms Latency) ]
                 │
                 └──► [ 3. Theory of Mind Classifier (model.pkl) ]
                           │
                           ├──► [ Log timestamped mood to mood_log.csv ]
                           │
                           ▼ (Inferred State Context)
                      [ 4. Dynamic Prompt Augmentation ]
                           │
                           ▼
                      [ 5. Local Ollama Engine (llama3.2:3b) ]
                           │
                           ▼
                      [ 6. Glassmorphism Web App (Port 5173) ]
```

---

## 📁 Repository Structure

```
Local TOM/
├── server.py              # ASGI Backend API (Starlette + Uvicorn + Ollama bridge)
├── train.py               # ML Training script for Theory of Mind state classifier
├── data.csv               # Hinglish & English student distress dataset
├── model.pkl              # Serialized character n-gram TF-IDF + Logistic Regression pipeline
├── mood_log.csv           # Local session mood history log
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
│
└── Frontend/              # React 19 + TypeScript + Vite 6 Web Application
    ├── src/
    │   ├── App.tsx        # Main chat and wellbeing interface
    │   ├── LandingPage.tsx# Welcoming glassmorphic landing hero
    │   ├── api.ts         # Backend API client with offline recovery
    │   ├── safety.ts      # Regional crisis helpline directory
    │   └── types.ts       # TypeScript schemas and data models
    ├── package.json       # Node.js dependencies
    └── vite.config.ts     # Vite configuration with Tailwind CSS v4
```

---

## 🚀 Quick Start Guide

### Prerequisites
* **Python**: 3.11+
* **Node.js**: 20.0+ (`npm` included)
* **Ollama**: [Download & install Ollama](https://ollama.ai)

---

### Step 1: Start Ollama & Download the Model

Open your terminal and ensure the Ollama daemon is running:

```bash
# 1. Start Ollama service (if not already running)
ollama serve

# 2. Pull the lightweight 3B model (one-time download, ~2.0 GB)
ollama pull llama3.2:3b
```

---

### Step 2: Start the Local Backend Server

In a new terminal window:

```bash
# 1. Navigate to the project root
cd "/home/nitin/Projects/Local TOM"

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start the backend server
python3 server.py
```

The backend server will spin up on **`http://127.0.0.1:8000`** with live connection to Ollama.

---

### Step 3: Start the React Frontend

In another terminal window:

```bash
# 1. Navigate to the Frontend directory
cd "/home/nitin/Projects/Local TOM/Frontend"

# 2. Install frontend dependencies
npm install

# 3. Run the Vite development server
npm run dev
```

Open your browser and navigate to **`http://localhost:5173`** to begin chatting with TOM.

---

## 🧘 Instant Wellness Triggers

TOM includes built-in instant triggers that deliver pre-calibrated grounding techniques without LLM latency:

| What You Type | Delivered Technique |
| :--- | :--- |
| `Breathing exercise` | Guided **Box Breathing (4-4-4-4)** sequence |
| `Grounding technique` or `5-4-3-2-1` | **5-4-3-2-1 Sensory Grounding** technique |
| `Meditation` | 60-Second **Mindful Minute** breath focus |
| `Coping strategies` | Practical multi-step self-care action steps |

---

## 🧠 Retraining the Mental State Classifier

The Theory of Mind classifier translates colloquial and code-mixed student expressions into structured emotional contexts.

1. Open [`data.csv`](data.csv) and add your custom phrases:
   ```csv
   text,label
   aaj padhai mein man nahi lag raha,exam_stress
   parents compare me with my peers,family_pressure
   lagta hai mera koi dost nahi,loneliness
   ```
2. Run the training script:
   ```bash
   python3 train.py
   ```
3. A new [`model.pkl`](model.pkl) will be evaluated and exported automatically.

---

## 🔌 API Reference

### Health Check
`GET /api/health`
```json
{
  "status": "ok",
  "model": "llama3.2:3b"
}
```

### Chat Completion
`POST /api/chat`
* **Request:**
  ```json
  {
    "message": "Exams are near and I feel overwhelmed",
    "session_id": "session-123",
    "region": "IN"
  }
  ```
* **Response:**
  ```json
  {
    "response": "I hear you. Exam stress can feel heavy. Let's take it one step at a time...",
    "intent": "exam_stress",
    "risk_level": "low",
    "resources": [],
    "session_id": "session-123",
    "confidence": 0.88,
    "source": "ollama"
  }
  ```

### Reset Session
`POST /api/session/reset`
```json
{
  "session_id": "session-123"
}
```

---

## ⚠️ Safety & Ethical Disclaimer

> **TOM is an educational AI wellbeing companion and is NOT a licensed healthcare professional, therapist, or emergency medical service.**
> It cannot provide medical diagnoses, clinical treatment, or prescriptions.

If you or someone you know is going through a crisis or experiencing suicidal ideation, please reach out to professional emergency resources immediately:

* 🇮🇳 **India**:
  * **Tele-MANAS**: `14416` (Toll-Free, 24/7)
  * **KIRAN Helpline**: `1800-599-0019`
  * **National Emergency**: `112`
* 🇺🇸 **United States / Canada**:
  * **Suicide & Crisis Lifeline**: Call or text `988`
  * **Crisis Text Line**: Text `HOME` to `741741`
* 🇬🇧 **United Kingdom**:
  * **Samaritans**: `116 123`
  * **Shout**: Text `SHOUT` to `85258`
* 🌍 **International**:
  * Find resources in your country at [findahelpline.com](https://findahelpline.com) or [befrienders.org](https://www.befrienders.org).

---

## 📄 License

This project is open-source and intended for educational, research, and personal wellbeing purposes.
