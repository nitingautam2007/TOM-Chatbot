import datetime, os, re, joblib, ollama, uvicorn
import pandas as pd
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

MODEL = "llama3.2:3b"
SYSTEM = (
    "You are TOM (Talk To Me), a warm, empathetic mental health companion for students. "
    "Listen attentively and meet the student where they are. Do NOT assume or project emotions "
    "(like anxiety, loneliness, or depression) onto the user unless they explicitly share them. "
    "If the user says 'hi', 'hello', or casual remarks, greet them naturally and warmly, asking how their day is going. "
    "Reply in the same language the student uses (English or Hinglish). Keep responses concise (under 60 words). "
    "You are a supportive friend, not a doctor; never diagnose."
)

CRISIS_REGEX = re.compile(
    r"\b(kill\s+myself|end\s+my\s+life|suicid(e|al)|want\s+to\s+die|self[-\s]?harm|cut\s+myself|"
    r"marna\s+chahta|marna\s+chahti|mar\s+jaana|jeena\s+nahi|khud\s+ko\s+khatam|zindagi\s+khatam)\b",
    re.IGNORECASE,
)

CRISIS_RESPONSE = (
    "I'm really glad you told me. I want to make sure you're safe right now. "
    "If you are in immediate danger, please reach out to local emergency services or a trusted person. "
    "You deserve support from a real person right now."
)

CRISIS_RESOURCES = [
    {
        "label": "Tele-MANAS (India, 24/7)",
        "description": "Free, confidential national mental health helpline.",
        "tel": "14416",
    },
    {
        "label": "KIRAN Helpline",
        "description": "24/7 national mental health rehabilitation helpline.",
        "tel": "1800-599-0019",
    },
    {
        "label": "National Emergency Services",
        "description": "Call immediately if you are in danger.",
        "tel": "112",
    },
]

GREETING_WORDS = {
    "hi", "hello", "hey", "sup", "yo", "good morning", "good evening",
    "good afternoon", "howdy", "namaste", "kem cho", "kaise ho"
}

# Quick-reply triggers → deterministic guided responses (no Ollama needed)
QUICK_REPLIES: dict[str, str] = {
    "breathing exercise": (
        "Let's do a calming box breath together 🌬️\n\n"
        "• Breathe in slowly through your nose for 4 counts\n"
        "• Hold for 4 counts\n"
        "• Breathe out gently through your mouth for 4 counts\n"
        "• Hold empty for 4 counts\n\n"
        "Repeat this 4 times. Take your time — I'm right here with you."
    ),
    "grounding technique": (
        "Let's try the 5-4-3-2-1 Grounding technique 🌿\n\n"
        "👁️  Name 5 things you can see\n"
        "✋  Name 4 things you can physically touch\n"
        "👂  Name 3 things you can hear\n"
        "👃  Name 2 things you can smell\n"
        "👅  Name 1 thing you can taste\n\n"
        "Take your time with each one. Feel your feet on the floor. You are safe."
    ),
    "5-4-3-2-1": (
        "Let's try the 5-4-3-2-1 Grounding technique 🌿\n\n"
        "👁️  Name 5 things you can see\n"
        "✋  Name 4 things you can physically touch\n"
        "👂  Name 3 things you can hear\n"
        "👃  Name 2 things you can smell\n"
        "👅  Name 1 thing you can taste\n\n"
        "Take your time with each one. Feel your feet on the floor. You are safe."
    ),
    "meditation": (
        "Let's try a quick mindful minute 🧘\n\n"
        "Close your eyes and take a slow breath in... and out.\n\n"
        "Focus only on the feeling of your breath — the air entering your nose, "
        "filling your chest, and leaving slowly.\n\n"
        "If a thought pops up, just notice it gently and let it drift away like a cloud.\n\n"
        "Even 60 seconds of this can calm your mind."
    ),
    "coping strategies": (
        "Here are some gentle coping strategies:\n\n"
        "🌬️  Box breathing — slow your nervous system\n"
        "🚶  Short walk — even 5 minutes outside helps\n"
        "📓  Journaling — write what's on your mind freely\n"
        "🎵  Music — a comforting playlist can shift your mood\n"
        "💬  Talk — to a friend, family member, or me!\n\n"
        "Which of these sounds most doable for you right now?"
    ),
}

clf = joblib.load("model.pkl") if os.path.exists("model.pkl") else None
sessions: dict[str, list[dict]] = {}


def classify_message(text: str) -> tuple[str, float]:
    clean = text.lower().strip("!.,? ")
    if clean in GREETING_WORDS or (len(clean.split()) <= 2 and any(w in clean.split() for w in GREETING_WORDS)):
        return "greeting", 1.0

    if not clf:
        return "general", 0.5

    probs = clf.predict_proba([text])[0]
    max_p = max(probs)
    # 0.25 is well above the random 0.20 baseline for 5 classes
    if max_p >= 0.25 and not any(neg in clean for neg in ["not ", "nhi ", "nahi "]):
        return clf.classes_[probs.argmax()], round(float(max_p), 2)
    return "general", round(float(max_p), 2)


async def health(request):
    return JSONResponse({"status": "ok", "model": MODEL})


async def chat(request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    user_msg = (data.get("message") or "").strip()
    session_id = str(data.get("session_id") or "default")

    if not user_msg:
        return JSONResponse({"response": "Please tell me what's on your mind."}, status_code=400)

    # 1. Deterministic Safety Assessment
    if CRISIS_REGEX.search(user_msg):
        return JSONResponse(
            {
                "response": CRISIS_RESPONSE,
                "intent": "crisis",
                "risk_level": "high",
                "resources": CRISIS_RESOURCES,
                "session_id": session_id,
                "confidence": 1.0,
                "source": "safety",
            }
        )

    # 2. Quick-reply triggers (deterministic, no Ollama)
    quick_key = user_msg.lower().strip("!.,? ")
    if quick_key in QUICK_REPLIES:
        bot_text = QUICK_REPLIES[quick_key]
        history = sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": bot_text})
        return JSONResponse({
            "response": bot_text,
            "intent": "grounding",
            "risk_level": "low",
            "resources": [],
            "session_id": session_id,
            "confidence": 1.0,
            "source": "quick_reply",
        })

    # 3. State classification & Mood Logging
    label, confidence = classify_message(user_msg)
    if label not in ("greeting", "general"):
        pd.DataFrame([[datetime.datetime.now(), label]], columns=["time", "label"]).to_csv(
            "mood_log.csv", mode="a", index=False, header=not os.path.exists("mood_log.csv")
        )

    # 3. Dynamic Prompting with Ollama
    history = sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": user_msg})
    recent_msgs = history[-8:]

    if label not in ("greeting", "general"):
        prompt_system = f"{SYSTEM} Context clue: The user may be discussing {label.replace('_', ' ')}."
    else:
        prompt_system = SYSTEM

    chat_messages = [{"role": "system", "content": prompt_system}] + recent_msgs

    try:
        ollama_res = ollama.chat(model=MODEL, messages=chat_messages)
        bot_text = ollama_res["message"]["content"]
    except Exception:
        bot_text = (
            "I'm having trouble connecting to my local Ollama brain right now. "
            "Please make sure `ollama serve` is running and `llama3.2:3b` is pulled!"
        )

    history.append({"role": "assistant", "content": bot_text})

    return JSONResponse(
        {
            "response": bot_text,
            "intent": label,
            "risk_level": "low",
            "resources": [],
            "session_id": session_id,
            "confidence": confidence,
            "source": "ollama",
        }
    )


async def mood_stats(request):
    if not os.path.exists("mood_log.csv"):
        return JSONResponse({
            "total": 0,
            "counts": {},
            "recent": [],
            "top_emotion": "None",
            "streak_days": 0,
        })

    try:
        df = pd.read_csv("mood_log.csv")
        if df.empty or "label" not in df.columns:
            return JSONResponse({
                "total": 0,
                "counts": {},
                "recent": [],
                "top_emotion": "None",
                "streak_days": 0,
            })

        counts = df["label"].value_counts().to_dict()
        top_emotion = str(df["label"].mode()[0]) if not df["label"].empty else "None"

        recent = []
        for _, row in df.tail(30).iloc[::-1].iterrows():
            recent.append({
                "time": str(row.get("time", ""))[:19],
                "label": str(row.get("label", "")),
            })

        days = set()
        for t in df["time"]:
            try:
                days.add(str(t)[:10])
            except Exception:
                pass

        return JSONResponse({
            "total": len(df),
            "counts": counts,
            "recent": recent,
            "top_emotion": top_emotion,
            "streak_days": len(days),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def reset_session(request):
    try:
        data = await request.json()
        session_id = str(data.get("session_id") or "")
        sessions.pop(session_id, None)
    except Exception:
        pass
    return JSONResponse({"status": "cleared"})


async def delete_all_data(request):
    try:
        data = await request.json()
        session_id = str(data.get("session_id") or "")
        sessions.pop(session_id, None)
    except Exception:
        pass
    try:
        with open("mood_log.csv", "w", encoding="utf-8") as f:
            f.write("time,label\n")
    except Exception:
        pass
    return JSONResponse({"status": "deleted"})


routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/chat", chat, methods=["POST"]),
    Route("/api/mood/stats", mood_stats, methods=["GET"]),
    Route("/api/session/reset", reset_session, methods=["POST"]),
    Route("/api/data", delete_all_data, methods=["DELETE"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware)

if __name__ == "__main__":
    print("💙 TOM Backend API running at http://127.0.0.1:8000 (connected to Ollama)")
    uvicorn.run(app, host="127.0.0.1", port=8000)
