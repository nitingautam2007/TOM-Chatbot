"""Non-clinical crisis response copy (Phase 4).

No phone numbers or URLs are invented here — operators must set
``TOM_SAFETY_EMERGENCY_NUMBER`` / ``TOM_SAFETY_CRISIS_RESOURCE_URL`` in
backend/.env. When unset, only the generic guidance lines are returned.

TOM is not a clinician or emergency service. These messages redirect to
human help; they never claim to assess or treat crisis risk.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.safety.types import RiskLevel


def _resource_lines(language: str) -> list[str]:
    lines: list[str] = []
    number = (settings.safety_emergency_number or "").strip()
    url = (settings.safety_crisis_resource_url or "").strip()

    if language == "hi":
        if number:
            lines.append(f"तुरंत मदद के लिए आपातकालीन नंबर पर कॉल करें: {number}")
        if url:
            lines.append(f"सहायता संसाधन यहाँ देखें: {url}")
        if not number and not url:
            lines.append("कृपया अपने स्थानीय आपातकालीन नंबर या भरोसेमंद व्यक्ति से संपर्क करें।")
        return lines

    if language == "hinglish":
        if number:
            lines.append(f"Turant madad ke liye emergency number par call karein: {number}")
        if url:
            lines.append(f"Madad ke resources yahan dekhein: {url}")
        if not number and not url:
            lines.append("Apne local emergency number ya kisi bharosemand insaan se baat karein.")
        return lines

    # English (default)
    if number:
        lines.append(f"Call your local emergency number right now: {number}")
    if url:
        lines.append(f"Crisis resources: {url}")
    if not number and not url:
        lines.append(
            "Please contact your local emergency number or a trusted person near you right now."
        )
    return lines


def crisis_response(risk_level: RiskLevel, language: str) -> str:
    """Return a short, supportive, non-clinical safety reply."""
    lines: list[str] = []

    if language == "hi":
        lines.append(
            "जो आपने लिखा है उससे लगता है कि आप बहुत कठिन समय से गुजर रहे हैं। "
            "मैं एक ऐप हूँ और आपातकालीन सेवा नहीं — पर आप अकेले नहीं हैं।"
        )
        lines.append(
            "कृपया अभी किसी ऐसे व्यक्ति से बात करें जिन पर आप भरोसा करते हैं, "
            "या तुरंत स्थानीय मदद लें।"
        )
        lines.extend(_resource_lines("hi"))
        return "\n\n".join(lines)

    if language == "hinglish":
        lines.append(
            "Jo aapne likha hai, usse lagta hai ki aap bahut mushkil time se "
            "gujar rahe ho. Main ek app hoon, emergency service nahi — par aap "
            "akele nahi ho."
        )
        lines.append(
            "Please abhi kisi bharosemand insaan se baat karo, ya turant local "
            "help lo."
        )
        lines.extend(_resource_lines("hinglish"))
        return "\n\n".join(lines)

    # English — HIGH vs IMMINENT share supportive framing; imminent adds urgency.
    lines.append(
        "I'm really sorry you're going through this. What you shared sounds "
        "serious, and your safety matters right now."
    )
    if risk_level == "imminent":
        lines.append(
            "Please reach out to emergency services or someone physically with "
            "you immediately — don't stay alone with this."
        )
    else:
        lines.append(
            "I'm an app, not an emergency service, and I can't keep you safe "
            "on my own. Please talk to someone you trust right now, or contact "
            "local emergency help."
        )
    lines.extend(_resource_lines("en"))
    lines.append(
        "If you can, also consider speaking with a mental-health professional "
        "when things are safer. I'm still here if you want to keep talking."
    )
    return "\n\n".join(lines)
