"""Curated local response library (Phase 6).

Student-oriented supportive copy for English / Hindi (Devanagari) / Hinglish
(Roman Hindi + English). No diagnosis, no therapist persona, no clinical
claims. Kept as plain data so variants stay easy to edit without a matrix
of intent × emotion combinations.

Keys: intent label (Phase 3B) or emotion label; language codes en / hi /
hinglish. Each language maps to a small tuple of variants — selection picks
one (context-aware rotation avoids immediate repeats).
"""

from __future__ import annotations

from app.services.nlp.types import LanguageCode

# Response language buckets (unknown is handled by the selector → en).
LANGS: tuple[LanguageCode, ...] = ("en", "hi", "hinglish")

# One representative embedding text per intent (first EN variant is used for
# semantic retrieval per language in the selector — see selector._build_index).

INTENT_RESPONSES: dict[str, dict[str, tuple[str, ...]]] = {
    "greeting": {
        "en": (
            "Hello! I'm TOM — a private, local space to talk things through. How has your day been?",
            "Hi there! Good to see you. What's on your mind today?",
            "Hey! I'm here to listen. How are you feeling right now?",
        ),
        "hi": (
            "नमस्ते! मैं TOM हूँ — आपकी बातें सुनने के लिए यहाँ हूँ। आज का दिन कैसा रहा?",
            "हैलो! खुशी हुई आपसे बात करके। अभी आप कैसा महसूस कर रहे हैं?",
            "नमस्कार! मैं सुनने के लिए तैयार हूँ। आज मन कैसा है?",
        ),
        "hinglish": (
            "Hello! Main TOM hoon — private jagah hai, baat karo. Din kaisa raha?",
            "Hi! Khushi hui tumse baat karke. Abhi mood kaisa hai?",
            "Hey! Main sunne ke liye hoon. Feel kaisa kar rahe ho?",
        ),
    },
    "goodbye": {
        "en": (
            "Take care of yourself. I'm here whenever you want to talk again.",
            "Goodbye for now — checking in with yourself is a good habit. See you next time.",
        ),
        "hi": (
            "अपना ख्याल रखिए। जब भी बात करनी हो, मैं यहाँ हूँ।",
            "अलविदा! खुद पर ध्यान देते रहिए। फिर मिलेंगे।",
        ),
        "hinglish": (
            "Apna khayal rakhna. Jab baat karni ho, main yahin hoon.",
            "Bye! Khud ka khayal rakhte raho. Phir milte hain.",
        ),
    },
    "general_conversation": {
        "en": (
            "Thanks for sharing that. Tell me a bit more — what's been the strongest part of your day?",
            "I hear you. What would you like to explore further about that?",
        ),
        "hi": (
            "आपने जो बताया उसके लिए धन्यवाद। थोड़ा और बताइए — दिन में सबसे अच्छा क्या रहा?",
            "समझ रहा हूँ। इस बारे में और क्या जानना चाहेंगे?",
        ),
        "hinglish": (
            "Batane ke liye thanks. Thoda aur batao — din ka best part kya raha?",
            "Samajh raha hoon. Aur kya explore karna chahoge?",
        ),
    },
    "emotional_support": {
        "en": (
            "That sounds heavy — I'm glad you're talking about it. What part feels hardest right now?",
            "You don't have to carry this alone. I'm here to listen as long as you need.",
        ),
        "hi": (
            "यह भारी लगता है — आपने बाँटने के लिए धन्यवाद। अभी सबसे कठिन क्या लग रहा है?",
            "आपको यह अकेले उठाना ज़रूरी नहीं है। मैं तब तक सुन सकता हूँ जब तक आप चाहें।",
        ),
        "hinglish": (
            "Ye bhari lag raha hai — share karne ke liye thanks. Abhi sabse hard kya lag raha hai?",
            "Akela uthana zaroori nahi hai. Jab tak chaaho, main sun sakta hoon.",
        ),
    },
    "stress": {
        "en": (
            "Stress can pile up fast. What's one small thing you could take off your plate today?",
            "That sounds exhausting. Naming the biggest stressor sometimes helps — what is it right now?",
        ),
        "hi": (
            "तनाव जल्दी बढ़ सकता है। आज चीज़ों में से एक छोटी बात आप किस तरह हल्की कर सकते हैं?",
            "थकान स्वाभाविक है। सबसे बड़ा तनाव क्या है — नाम देने से मदद मिल सकती है।",
        ),
        "hinglish": (
            "Stress jaldi badh jaata hai. Aaj ek chhoti cheez kaise halki kar sakte ho?",
            "Exhausting lag raha hai. Sabse bada stressor abhi kya hai — naam lo na?",
        ),
    },
    "anxiety": {
        "en": (
            "Worry can feel constant. What's one thing that feels most uncertain to you right now?",
            "Anxious thoughts are loud sometimes. Want to slow down and unpack what's triggering them?",
        ),
        "hi": (
            "चिंता लगातार महसूस हो सकती है। अभी सबसे अनिश्चित क्या लग रहा है?",
            "घबराहट के विचार कभी-कभी बहुत शोर करते हैं। क्या इसे धीरे-धीरे समझें?",
        ),
        "hinglish": (
            "Worry constant lag sakti hai. Abhi sabse uncertain kya lag raha hai?",
            "Anxious thoughts zyada shor karte hain. Slow ho ke trigger samjhein?",
        ),
    },
    "sadness": {
        "en": (
            "I'm sorry you're feeling this way. What's been weighing on you the most?",
            "Low days are hard. Is there something small that usually lifts you a little?",
        ),
        "hi": (
            "आप ऐसा महसूस कर रहे हैं, यह सुनकर अफ़सोस हुआ। सबसे ज़्यादा क्या भारी लग रहा है?",
            "कम मन वाले दिन कठिन होते हैं। कोई छोटी चीज़ जो थोड़ा राहत देती है?",
        ),
        "hinglish": (
            "Ye feel karna mushkil hai. Sabse zyada kya bhaari lag raha hai?",
            "Low days hard hote hain. Koi chhoti cheez jo thoda uplift karti hai?",
        ),
    },
    "loneliness": {
        "en": (
            "Feeling alone is painful. Who is one person you might reach out to this week?",
            "Isolation can be heavy. Would describing what connection means to you help a little?",
        ),
        "hi": (
            "अकेलापन दुखदायी हो सकता है। इस हफ़्ते आप किससे संपर्क कर सकते हैं?",
            "अकेलापन भारी लग सकता है। जुड़ाव का मतलब बताने से थोड़ी मदद मिलेगी?",
        ),
        "hinglish": (
            "Akela lagna painful hai. Is week kis se reach out kar sakte ho?",
            "Isolation heavy lag sakta hai. Connection ka matlab batana help karega?",
        ),
    },
    "academic_pressure": {
        "en": (
            "College pressure can feel endless. What's the single most urgent task on your list?",
            "When everything feels urgent, breaking work into tiny steps helps. Which task comes first?",
        ),
        "hi": (
            "पढ़ाई का दबाव अंतहीन लग सकता है। सूची में सबसे ज़रूरी काम कौन-सा है?",
            "जब सब ज़रूरी लगे, काम को छोटे हिस्सों में बाँटना मदद करता है। पहले कौन-सा काम?",
        ),
        "hinglish": (
            "College ka pressure endless lag sakta hai. List mein sabse urgent task kaunsa hai?",
            "Sab urgent lage toh kaam chhote steps mein todo. Pehle kaunsa task?",
        ),
    },
    "relationship_issue": {
        "en": (
            "Relationships can get complicated. What's the main thing that feels stuck right now?",
            "It helps to name what you need in this situation. What would feel fair to you?",
        ),
        "hi": (
            "रिश्ते कभी-कभी जटिल हो जाते हैं। अभी सबसे अटकी हुई बात क्या है?",
            "इस स्थिति में आपको क्या चाहिए — यह कहने से मदद मिलती है। आपके लिए क्या उचित होगा?",
        ),
        "hinglish": (
            "Relationships complicated ho sakti hain. Abhi sabse atki hui baat kya hai?",
            "Is situation mein tumhe kya chahiye — ye bolne se help milti hai. Tumhare liye kya fair hoga?",
        ),
    },
    "sleep_concern": {
        "en": (
            "Trouble sleeping is rough. How does your wind-down routine look an hour before bed?",
            "Sleep affects everything else. Is it racing thoughts, screen time, or something else keeping you up?",
        ),
        "hi": (
            "नींद न आना कठिन होता है। सोने से एक घंटा पहले आपकी दिनचर्या कैसी होती है?",
            "नींद सब कुछ प्रभावित करती है। जागे रखने के लिए विचार, स्क्रीन या कुछ और?",
        ),
        "hinglish": (
            "Neend na aana rough hai. Sone se 1 ghanta pehle routine kaisa hota hai?",
            "Neend sab affect karti hai. Racing thoughts, screen, ya kuch aur jaag rakh raha hai?",
        ),
    },
    "self_confidence": {
        "en": (
            "Self-doubt can be loud. What's one thing you handled better than you give yourself credit for?",
            "Confidence grows from small wins. What's a tiny win you could claim today?",
        ),
        "hi": (
            "आत्म-संदेह ज़ोर से सुनाई दे सकता है। ऐसी कौन-सी एक बात जो आपने इससे बेहतर संभाली?",
            "आत्मविश्वास छोटी जीत से बढ़ता है। आज की एक छोटी जीत क्या हो सकती है?",
        ),
        "hinglish": (
            "Self-doubt loud hota hai. Ek achi cheez jo tumne isse better handle ki — kaunsi?",
            "Confidence small wins se badhta hai. Aaj ka ek chhota win kya ho sakta hai?",
        ),
    },
    "coping_help": {
        "en": (
            "Coping looks different for everyone. What has helped you even a little in tough moments?",
            "A simple next step can be a short walk, slow breathing, or texting one friend. What feels doable?",
        ),
        "hi": (
            "हर किसी के लिए सामना करने का तरीका अलग होता है। कठिन पलों में थोड़ी मदद क्या रही है?",
            "एक छोटा कदम — थोड़ा टहलना, धीमी साँस, या किसी एक को मैसेज — कौन-सा आसान लगता है?",
        ),
        "hinglish": (
            "Coping har kisi ka alag hota hai. Tough moments mein thodi help kya rahi hai?",
            "Ek simple step — thoda walk, slow breathing, ya kisi ko message — kya doable lagta hai?",
        ),
    },
    "help_seeking": {
        "en": (
            "Reaching out is a solid first step. Is there a trusted person or resource you could contact this week?",
            "Asking for help takes courage. What kind of support would feel most useful right now?",
        ),
        "hi": (
            "मदद माँगना एक अच्छा पहला कदम है। इस हफ़्ते किस भरोसेमंद व्यक्ति या संसाधन से संपर्क कर सकते हैं?",
            "मदद माँगने में हिम्मत चाहिए। अभी किस तरह की मदद सबसे उपयोगी लगेगी?",
        ),
        "hinglish": (
            "Help maangna solid first step hai. Is week kis bharosemand insaan ya resource se contact kar sakte ho?",
            "Help maangne mein courage lagta hai. Abhi kis tarah ki support sabse useful lagegi?",
        ),
    },
    "unknown": {
        "en": (
            "I'm following along. Could you say a little more about how you're feeling?",
            "Thanks for writing. What part of this feels most important to talk through?",
        ),
        "hi": (
            "मैं समझ रहा हूँ। थोड़ा और बताइए — अभी आप कैसा महसूस कर रहे हैं?",
            "लिखने के लिए धन्यवाद। इसमें से बात करने लायक सबसे ज़रूरी क्या है?",
        ),
        "hinglish": (
            "Main follow kar raha hoon. Thoda aur batao — abhi kaisa feel ho raha hai?",
            "Likhne ke liye thanks. Baat karne mein sabse important kya hai?",
        ),
    },
}

EMOTION_RESPONSES: dict[str, dict[str, tuple[str, ...]]] = {
    "sadness": {
        "en": (
            "I'm sorry you're feeling down. What would help a little right now — talking it through or a small break?",
        ),
        "hi": (
            "मन उतरा हुआ लग रहा है — थोड़ी राहत के लिए अभी क्या मदद करेगा: बात करना या छोटा आराम?",
        ),
        "hinglish": (
            "Mood down lag raha hai — thodi relief ke liye abhi kya help karega: baat karna ya chhota break?",
        ),
    },
    "anxiety": {
        "en": (
            "It sounds like worry is high. Want to name the thought that keeps looping?",
        ),
        "hi": (
            "लगता है चिंता ज़्यादा है। क्या उस विचार का नाम लें जो बार-बार घूम रहा है?",
        ),
        "hinglish": (
            "Lagta hai worry zyada hai. Us thought ka naam lo jo baar-baar ghoom raha hai?",
        ),
    },
    "anger": {
        "en": (
            "That frustration makes sense. What set it off — and what would feel like a fair next step?",
        ),
        "hi": (
            "यह झुँझलाहट समझ में आती है। इसकी वजह क्या थी — और आगे का उचित कदम क्या होगा?",
        ),
        "hinglish": (
            "Ye frustration sense banti hai. Iski wajah kya thi — aur aage ka fair step kya hoga?",
        ),
    },
    "stress": {
        "en": (
            "You seem stretched thin. Which one thing could wait until tomorrow?",
        ),
        "hi": (
            "लगता है आप पर बहुत बोझ है। कौन-सी एक बात कल तक टाली जा सकती है?",
        ),
        "hinglish": (
            "Lagta hai tum over ho. Kaunsi ek cheez kal tak postpone ho sakti hai?",
        ),
    },
    "loneliness": {
        "en": (
            "Loneliness stings. Is there one person you could message, even briefly, today?",
        ),
        "hi": (
            "अकेलापन चुभता है। आज कोई एक व्यक्ति जिसे छोटा सा मैसेज भेज सकते हैं?",
        ),
        "hinglish": (
            "Loneliness stings hai. Aaj ek insaan ko chhota message bhej sakte ho?",
        ),
    },
    "happiness": {
        "en": (
            "Glad to hear some lightness. What's contributing to the good mood?",
            "That's really nice — savoring moments like that helps. What made today feel good?",
            "Love that energy. What's one highlight you'd want to remember from this?",
        ),
        "hi": (
            "खुशी की बात सुनकर अच्छा लगा। अच्छे मूड में क्या योगदान दे रहा है?",
            "यह सुनकर खुशी हुई — ऐसे पलों को संजोना चाहिए। आज का दिन अच्छा क्यों लगा?",
            "बढ़िया बात है। आज से याद रखने लायक एक पल क्या था?",
        ),
        "hinglish": (
            "Achha lag raha hai kuch lightness hai. Good mood mein kya contribute kar raha hai?",
            "Ye sunke achha laga — aise moments ko sambhal ke rakhna chahiye. Aaj din achha kyun lag raha hai?",
            "Badhiya vibe hai. Aaj se yaad rakhne layak ek highlight kya tha?",
        ),
    },
    "positive": {
        "en": (
            "That's good to hear. What's one thing you'd like to carry into tomorrow?",
            "Really glad you shared that. What's keeping the good energy going?",
            "Nice — positives count. What's one small win from today?",
        ),
        "hi": (
            "यह अच्छी बात है। कल तक ले जाने लायक एक बात क्या हो सकती है?",
            "खुशी हुई यह जानकर। अच्छी एनर्जी बनाए रखने में क्या मदद कर रहा है?",
            "बढ़िया — छोटी जीत भी गिनती में आती हैं। आज की एक छोटी जीत क्या थी?",
        ),
        "hinglish": (
            "Ye achhi baat hai. Kal tak carry karne layak ek cheez kya ho sakti hai?",
            "Ye jaanke khushi hui. Good energy banaye rakhne mein kya help kar raha hai?",
            "Nice — chhoti jeet bhi count hoti hai. Aaj ka ek chhota win kya tha?",
        ),
    },
    "neutral": {
        "en": (
            "Thanks for checking in. Anything in particular you'd like to talk about?",
        ),
        "hi": (
            "अपडेट देने के लिए धन्यवाद। किसी खास बात पर बात करनी है?",
        ),
        "hinglish": (
            "Update dene ke liye thanks. Kisi khaas baat pe baat karni hai?",
        ),
    },
    "mixed": {
        "en": (
            "Mixed feelings are normal. Which thread do you want to pull on first?",
        ),
        "hi": (
            "मिश्रित भावनाएँ सामान्य हैं। पहले किस ओर ध्यान देना चाहेंगे?",
        ),
        "hinglish": (
            "Mixed feelings normal hain. Pehle kis thread pe focus karna chahoge?",
        ),
    },
    "uncertain": {
        "en": (
            "It's okay if it's hard to name. What's one word for how today has felt?",
        ),
        "hi": (
            "नाम देना कठिन हो तो चलेगा। आज का दिन कैसा रहा — एक शब्द में?",
        ),
        "hinglish": (
            "Naam dena mushkil ho toh chalega. Aaj ka din kaisa raha — ek word mein?",
        ),
    },
}

FALLBACK_RESPONSES: dict[str, tuple[str, ...]] = {
    "en": (
        "I'm here with you. Tell me more about what's going on.",
        "Thanks for sharing. What feels most important to talk about right now?",
        "I hear you. How long has it been feeling this way?",
    ),
    "hi": (
        "मैं यहाँ हूँ। जो चल रहा है, उसके बारे में और बताइए।",
        "बताने के लिए धन्यवाद। अभी बात करने लायक सबसे ज़रूरी क्या है?",
        "मैं सुन रहा हूँ। ऐसा कब से महसूस हो रहा है?",
    ),
    "hinglish": (
        "Main yahin hoon. Jo chal raha hai, uske baare mein aur batao.",
        "Share karne ke liye thanks. Abhi baat karne layak sabse important kya hai?",
        "Sun raha hoon. Aisa kab se lag raha hai?",
    ),
}
