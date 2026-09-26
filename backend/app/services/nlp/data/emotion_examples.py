"""Curated prototype utterances for Phase 3B emotion classification.

Describes expressed affect in a message — NOT a psychiatric diagnosis.
Development/prototype data only; not a clinical dataset.
"""

from __future__ import annotations

EMOTION_LABELS: tuple[str, ...] = (
    "sadness",
    "anxiety",
    "anger",
    "stress",
    "loneliness",
    "happiness",
    "positive",
    "neutral",
    "mixed",
    "uncertain",
)

# Representative examples per emotion (English / Hindi / Hinglish).
# "uncertain" has no prototypes — assigned when confidence is low.
EMOTION_EXAMPLES: dict[str, tuple[str, ...]] = {
    "sadness": (
        "I feel really sad",
        "I feel down today",
        "main bahut udaas hoon",
        "aaj mood bahut kharab hai",
        "I am crying and feel low",
        "mujhe bahut dukh ho raha hai",
    ),
    "anxiety": (
        "I am worried about everything",
        "I feel nervous",
        "I am so nervous and worried all the time",
        "mujhe ghabrahat ho rahi hai",
        "bahut tension ho rahi hai",
        "I am scared about the future",
        "ghabrahat ho rahi hai",
        "constant worry and nervousness",
    ),
    "anger": (
        "I am really angry",
        "this makes me so mad",
        "mujhe bahut gussa aa raha hai",
        "main bahut irritate hoon",
        "I am furious right now",
        "bahut gussa aa raha hai",
    ),
    "stress": (
        "I am under a lot of pressure",
        "everything feels stressful",
        "bahut pressure hai",
        "dimaag bahut stressed hai",
        "I am overwhelmed with work",
        "bahut stress hai",
    ),
    "loneliness": (
        "I feel alone",
        "nobody understands me",
        "mujhe akela lagta hai",
        "I am so lonely",
        "koi nahi hai mere paas",
    ),
    "happiness": (
        "I am really happy today",
        "I feel great",
        "aaj main bahut khush hoon",
        "mood bahut acha hai",
        "I am smiling all day",
        "bahut khushi ho rahi hai",
    ),
    "positive": (
        "I feel hopeful",
        "things are getting better",
        "ab sab better lag raha hai",
        "I feel positive",
        "I am grateful today",
        "sab theek chal raha hai",
    ),
    "neutral": (
        "I have a class tomorrow",
        "my exam is on Monday",
        "kal college jaana hai",
        "I am going to the library",
        "what time is it?",
        "mere paas meeting hai",
    ),
    "mixed": (
        "I am happy but also nervous",
        "I feel excited and scared at once",
        "khushi bhi hai aur tension bhi",
        "I am relieved but still worried",
        "good news yet I feel anxious inside",
        "ek taraf khushi ek taraf darr",
    ),
}
