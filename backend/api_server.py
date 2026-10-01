#!/usr/bin/env python3
"""
TOM Backend API Server
=======================

Flask REST API for TOM - Talk To Me frontend integration.

Special handling:
- Buttons and mood emojis: Uses frontend's nice responses
- Text queries: Uses TOM's backend responses from data.json
- Context memory: Maintains conversation context per session
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from tom_chatbot import TOmChatbot
import uuid
import os
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'tom-secret-key-2024'
CORS(app, supports_credentials=True)  # Enable CORS for frontend connection with credentials

# Get the absolute path to data.json
BACKEND_DIR = Path(__file__).resolve().parent
DATA_PATH = str(BACKEND_DIR / 'data.json')

# Initialize TOM chatbot with explicit data path
tom = TOmChatbot(data_path=DATA_PATH)

# Load data and train model at startup
print("Initializing TOM chatbot...")
if not tom.load_data():
    print("ERROR: Failed to load data!")
    exit(1)

if not tom.train_model():
    print("ERROR: Failed to train model!")
    exit(1)

print("TOM chatbot initialized and ready!")

# Conversation context storage (in-memory, per session)
# Stores last 5 messages per session for context
CONTEXT_MEMORY = {}  # Format: {session_id: [list of last messages]}

# Frontend responses for specific buttons and moods
# These will be used when backend is ON for these specific inputs
FRONTEND_SPECIAL_RESPONSES = {
    # Mood selections (with and without emojis)
    "i'm feeling struggling today": "I hear you. Would you like to tell me more about what's on your mind?",
    "i'm feeling low today": "Thank you for sharing that with me. You're not alone in feeling this way.",
    "i'm feeling okay today": "It takes courage to reach out. How long have you been feeling this way?",
    "i'm feeling good today": "I'm here with you. Let's take this one step at a time.",
    "i'm feeling great today": "I'm here with you. Let's take this one step at a time.",
    
    # Suggestion buttons (exact matches)
    "i'm feeling anxious": "Anxiety can feel overwhelming, but you're doing the right thing by acknowledging it. Let's try a simple breathing exercise: breathe in for 4 counts, hold for 4, breathe out for 6. How does that feel?",
    "i need to talk": "I'm here and I'm listening. This is a safe space — there's no right or wrong way to feel. What would you like to share?",
    "breathing exercise": "Let's do a calming box breath together:\n\n• Breathe in slowly for 4 counts\n• Hold for 4 counts\n• Breathe out for 4 counts\n• Hold for 4 counts\n\nRepeat this 4 times. Take your time — I'm right here with you.",
    "trouble sleeping": "Sleep difficulties are so common, and they can make everything feel harder. A few things that often help: keeping a consistent bedtime, avoiding screens 30 minutes before bed, and a short body-scan meditation. Would you like me to guide you through one?",
    "grounding technique": "A gentle grounding technique: the 5-4-3-2-1 method.\n\n• 5 things you can see\n• 4 things you can physically feel\n• 3 things you can hear\n• 2 things you can smell\n• 1 thing you can taste\n\nThis brings your attention back to the present moment."
}

# Risk level mapping based on intent
def get_risk_level(intent):
    """Determine risk level based on intent"""
    high_risk_intents = ['crisis', 'suicide', 'death', 'depressed', 'depression']
    
    if intent in high_risk_intents:
        return 'high'
    return 'low'

def update_context(session_id, message, response=None):
    """Update conversation context for a session"""
    if session_id not in CONTEXT_MEMORY:
        CONTEXT_MEMORY[session_id] = []
    
    # Add user message to context
    CONTEXT_MEMORY[session_id].append({
        'role': 'user',
        'text': message
    })
    
    # Add bot response to context if provided
    if response:
        CONTEXT_MEMORY[session_id].append({
            'role': 'assistant',
            'text': response
        })
    
    # Keep only last 5 exchanges (10 messages max) to avoid memory bloat
    CONTEXT_MEMORY[session_id] = CONTEXT_MEMORY[session_id][-10:]



@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat API endpoint for frontend.
    
    For buttons and mood emojis: Uses frontend's nice responses
    For text queries: Uses TOM's backend responses with context
    
    Request JSON:
    {
        "message": "user input text",
        "session_id": "optional browser session identifier"
    }
    
    Response JSON:
    {
        "response": "TOM's reply",
        "intent": "detected intent",
        "risk_level": "low" | "high"
    }
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'error': 'Missing message in request',
                'response': "I'm TOM. How can I help you today?",
                'intent': 'none',
                'risk_level': 'low'
            }), 400
        
        user_message = data['message']
        session_id = data.get('session_id')
        
        # Generate or get session ID for context tracking
        if not session_id:
            session_id = session.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
                session['session_id'] = session_id
        
        # Get context summary for this session
        context_summary = get_context_summary(session_id)
        
        # Special handling: Check if message matches buttons or moods
        # Try to match with and without emojis
        message_lower = user_message.lower()
        
        # Remove common emojis for matching
        clean_message = message_lower
        for emoji in ['😔', '😕', '😐', '🙂', '😊']:
            clean_message = clean_message.replace(emoji, '').strip()
        
        # Check if this matches any special response
        for pattern, response_text in FRONTEND_SPECIAL_RESPONSES.items():
            if pattern in clean_message or pattern in message_lower:
                # Update context
                update_context(session_id, user_message, response_text)
                return jsonify({
                    'response': response_text,
                    'intent': 'frontend_special',
                    'risk_level': 'low'
                })
        
        # For all other messages, use TOM's backend responses with context
        # Prepend context in a natural way the model can understand
        message_with_context = user_message
        if session_id in CONTEXT_MEMORY and CONTEXT_MEMORY[session_id]:
            # Get the last user message for context
            last_user_msg = ""
            for msg in reversed(CONTEXT_MEMORY[session_id]):
                if msg['role'] == 'user':
                    last_user_msg = msg['text']
                    break
            if last_user_msg:
                message_with_context = f"Following up on: '{last_user_msg}'. Now: {user_message}"
        
        response = tom.respond(message_with_context)
        intent = tom.predict_intent(user_message)
        risk_level = get_risk_level(intent)
        
        # Update context with this exchange
        update_context(session_id, user_message, response)
        
        return jsonify({
            'response': response,
            'intent': intent,
            'risk_level': risk_level
        })
        
    except Exception as e:
        print(f"Error in /api/chat: {e}")
        return jsonify({
            'error': str(e),
            'response': "I'm having trouble understanding. Could you try again?",
            'intent': 'none',
            'risk_level': 'low'
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'model': 'TOmChatbot (SVM)',
        'intents': len(tom.intents),
        'patterns': len(tom.patterns),
        'message': 'TOM backend is running and ready!'
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("TOM Backend API Server with Context Memory")
    print("="*60)
    print("\nStarting Flask server...")
    print("API will be available at: http://127.0.0.1:8000")
    print("\nEndpoints:")
    print("  POST /api/chat    - Send user messages (with optional session_id)")
    print("  GET  /api/health  - Health check")
    print("\nFeatures:")
    print("  - Mood selections use frontend responses")
    print("  - Suggestion buttons use frontend responses")
    print("  - All other text uses TOM backend responses")
    print("  - Context memory: Remember last 5 exchanges per session")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
