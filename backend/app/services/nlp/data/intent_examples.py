"""Curated prototype utterances for Phase 3B intent classification.

Development/prototype data only — not a clinical dataset and not labeled
for diagnosis. Future phases may replace these with a trained supervised
classifier while keeping the same label taxonomy.
"""

from __future__ import annotations

INTENT_LABELS: tuple[str, ...] = (
    "greeting",
    "goodbye",
    "general_conversation",
    "emotional_support",
    "stress",
    "anxiety",
    "sadness",
    "loneliness",
    "academic_pressure",
    "relationship_issue",
    "sleep_concern",
    "self_confidence",
    "coping_help",
    "help_seeking",
    "unknown",
)

# Representative examples per intent (English / Hindi / Hinglish where useful).
# "unknown" has no prototypes — it is assigned when confidence is low.
INTENT_EXAMPLES: dict[str, tuple[str, ...]] = {
    "greeting": (
        "hi",
        "hello",
        "hey",
        "namaste",
        "hii",
        "good morning",
        "hello there",
        "namaskar",
    ),
    "goodbye": (
        "bye",
        "goodbye",
        "see you later",
        "phir milte hain",
        "good night",
        "ok bye",
        "goodnight",
    ),
    "general_conversation": (
        "What are you doing?",
        "Tell me something",
        "aaj kya chal raha hai?",
        "how are you?",
        "what is your name?",
        "kya haal hai?",
    ),
    "emotional_support": (
        "I feel emotionally exhausted",
        "I need someone to talk to",
        "mujhe kisi se baat karni hai",
        "mujhe emotional support chahiye",
        "I just need to vent",
        "please listen to me",
        "mujhe sunne wala chahiye",
    ),
    "stress": (
        "I am very stressed",
        "I have too much stress",
        "I am very stressed about everything",
        "mujhe bahut stress ho raha hai",
        "yaar main bahut stressed hoon",
        "everything feels overwhelming",
        "bahut pressure hai",
        "stressed about work and life",
    ),
    "anxiety": (
        "I feel anxious",
        "I am constantly worrying",
        "mujhe bahut ghabrahat ho rahi hai",
        "future ko lekar anxiety ho rahi hai",
        "I am nervous all the time",
        "bahut tension ho rahi hai",
    ),
    "sadness": (
        "I feel sad",
        "I have been feeling low",
        "main bahut udaas hoon",
        "aaj mood bahut down hai",
        "I feel down today",
        "mujhe dukh ho raha hai",
    ),
    "loneliness": (
        "I feel lonely",
        "I have nobody to talk to",
        "mujhe bahut akela lagta hai",
        "mere paas baat karne ke liye koi nahi hai",
        "I am all alone",
        "koi samajh nahi",
    ),
    "academic_pressure": (
        "My exams are stressing me out",
        "I am worried about my studies",
        "padhai ka bahut pressure hai",
        "college ki wajah se stress ho raha hai",
        "I am stressed about my exams",
        "mujhe pariksha ki chinta hai",
    ),
    "relationship_issue": (
        "I am having problems with my relationship",
        "my girlfriend and I are fighting",
        "relationship mein problem chal rahi hai",
        "meri relationship kharab ho rahi hai",
        "we keep arguing",
        "mere dost se jhagra ho gaya",
    ),
    "sleep_concern": (
        "I cannot sleep properly",
        "I keep waking up at night",
        "mujhe raat ko neend nahi aati",
        "sleep schedule kharab ho gaya hai",
        "I have insomnia",
        "neend nahi aa rahi",
    ),
    "self_confidence": (
        "I don't believe in myself",
        "I feel like I am not good enough",
        "mujhe khud par confidence nahi hai",
        "main apne aap ko lekar insecure hoon",
        "I have low self esteem",
        "main khud pe bharosa nahi karta",
    ),
    "coping_help": (
        "How can I deal with stress?",
        "What can I do to feel better?",
        "stress ko kaise handle karun?",
        "main is situation ko kaise cope karun?",
        "give me coping strategies",
        "tension kaise kam karun?",
    ),
    "help_seeking": (
        "Can you help me?",
        "I need some advice",
        "mujhe help chahiye",
        "kya tum meri help kar sakte ho?",
        "I need guidance",
        "meri madad karo",
    ),
}
