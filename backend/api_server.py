#!/usr/bin/env python3
"""
TOM Backend API Server
=======================

Flask REST API for TOM - Talk To Me frontend integration.

Features:
- Chat API for frontend-backend communication
- Conversation storage in SQLite database
- Web-based analysis dashboard
- Privacy-first data collection
"""

from flask import Flask, request, jsonify, session, render_template_string
from flask_cors import CORS
from tom_chatbot import TOmChatbot
import sqlite3
import os
from datetime import datetime
import uuid
import json
from collections import Counter
import re
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'tom-secret-key-2024'  # Change this in production!
CORS(app)  # Enable CORS for frontend connection

# Initialize TOM chatbot
tom = TOmChatbot()

# Load data and train model at startup
print("Initializing TOM chatbot...")
if not tom.load_data():
    print("ERROR: Failed to load data!")
    exit(1)

if not tom.train_model():
    print("ERROR: Failed to train model!")
    exit(1)

print("TOM chatbot initialized and ready!")

# Initialize database
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DB_PATH = str(BACKEND_DIR / 'chats.db')

def init_db():
    """Initialize the SQLite database for storing chat conversations"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create chats table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            mood TEXT,
            session_id TEXT NOT NULL,
            intent TEXT,
            risk_level TEXT DEFAULT 'low'
        )
    ''')
    
    # Create consent table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consent (
            session_id TEXT PRIMARY KEY,
            consent_given BOOLEAN NOT NULL,
            timestamp TEXT NOT NULL,
            ip_address TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()
print(f"Database initialized at: {DB_PATH}")

# Frontend responses for specific buttons and moods
FRONTEND_SPECIAL_RESPONSES = {
    "i'm feeling struggling today": "I hear you. Would you like to tell me more about what's on your mind?",
    "i'm feeling low today": "Thank you for sharing that with me. You're not alone in feeling this way.",
    "i'm feeling okay today": "It takes courage to reach out. How long have you been feeling this way?",
    "i'm feeling good today": "I'm here with you. Let's take this one step at a time.",
    "i'm feeling great today": "I'm here with you. Let's take this one step at a time.",
    
    "i'm feeling anxious": "Anxiety can feel overwhelming, but you're doing the right thing by acknowledging it. Let's try a simple breathing exercise: breathe in for 4 counts, hold for 4, breathe out for 6. How does that feel?",
    "i need to talk": "I'm here and I'm listening. This is a safe space — there's no right or wrong way to feel. What would you like to share?",
    "breathing exercise": "Let's do a calming box breath together:\n\n• Breathe in slowly for 4 counts\n• Hold for 4 counts\n• Breathe out for 4 counts\n• Hold for 4 counts\n\nRepeat this 4 times. Take your time — I'm right here with you.",
    "trouble sleeping": "Sleep difficulties are so common, and they can make everything feel harder. A few things that often help: keeping a consistent bedtime, avoiding screens 30 minutes before bed, and a short body-scan meditation. Would you like me to guide you through one?",
    "grounding technique": "A gentle grounding technique: the 5-4-3-2-1 method.\n\n• 5 things you can see\n• 4 things you can physically feel\n• 3 things you can hear\n• 2 things you can smell\n• 1 thing you can taste\n\nThis brings your attention back to the present moment."
}

# Risk level mapping
def get_risk_level(intent):
    """Determine risk level based on intent"""
    high_risk_intents = ['crisis', 'suicide', 'death', 'depressed', 'depression']
    
    if intent in high_risk_intents:
        return 'high'
    return 'low'

# Database helper functions
def store_chat(message, response, mood=None, session_id=None, intent=None, risk_level='low'):
    """Store a chat conversation in the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chats (message, response, timestamp, mood, session_id, intent, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (message, response, datetime.now().isoformat(), mood, session_id, intent, risk_level))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error storing chat: {e}")
        return False

def get_chat_stats():
    """Get statistics about collected chat data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute("SELECT COUNT(*) FROM chats")
        total_chats = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM chats")
        unique_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM chats")
        date_range = cursor.fetchone()
        
        # Message length analysis
        cursor.execute("SELECT message FROM chats")
        messages = [row[0] for row in cursor.fetchall()]
        message_lengths = [len(msg) for msg in messages]
        avg_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
        
        # Intent distribution
        cursor.execute("SELECT intent, COUNT(*) FROM chats WHERE intent IS NOT NULL GROUP BY intent")
        intents = dict(cursor.fetchall())
        
        # Mood distribution
        cursor.execute("SELECT mood, COUNT(*) FROM chats WHERE mood IS NOT NULL GROUP BY mood")
        moods = dict(cursor.fetchall())
        
        # Risk level distribution
        cursor.execute("SELECT risk_level, COUNT(*) FROM chats GROUP BY risk_level")
        risk_levels = dict(cursor.fetchall())
        
        # Most common words
        all_words = []
        for msg in messages:
            words = re.findall(r'\b\w+\b', msg.lower())
            all_words.extend(words)
        word_counts = Counter(all_words)
        top_words = word_counts.most_common(10)
        
        conn.close()
        
        return {
            'total_chats': total_chats,
            'unique_sessions': unique_sessions,
            'date_range': date_range,
            'avg_message_length': round(avg_length, 1),
            'message_length_distribution': {
                'short': len([l for l in message_lengths if l < 20]),
                'medium': len([l for l in message_lengths if 20 <= l < 50]),
                'long': len([l for l in message_lengths if l >= 50])
            },
            'intents': intents,
            'moods': moods,
            'risk_levels': risk_levels,
            'top_words': [{'word': word, 'count': count} for word, count in top_words]
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {}

def get_recent_chats(limit=50):
    """Get recent chat conversations"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, message, response, timestamp, mood, intent, risk_level FROM chats ORDER BY timestamp DESC LIMIT ?", (limit,))
        chats = []
        for row in cursor.fetchall():
            chats.append({
                'id': row[0],
                'message': row[1],
                'response': row[2],
                'timestamp': row[3],
                'mood': row[4],
                'intent': row[5],
                'risk_level': row[6]
            })
        conn.close()
        return chats
    except Exception as e:
        print(f"Error getting recent chats: {e}")
        return []

def store_consent(session_id, consent_given):
    """Store user consent for data collection"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO consent (session_id, consent_given, timestamp)
            VALUES (?, ?, ?)
        ''', (session_id, consent_given, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error storing consent: {e}")
        return False

def has_consented(session_id):
    """Check if a session has given consent"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT consent_given FROM consent WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else False
    except Exception as e:
        print(f"Error checking consent: {e}")
        return False

def delete_session_data(session_id):
    """Permanently remove all stored data associated with one session."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chats WHERE session_id = ?", (session_id,))
        chats_deleted = cursor.rowcount
        cursor.execute("DELETE FROM consent WHERE session_id = ?", (session_id,))
        consent_records_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return chats_deleted, consent_records_deleted
    except Exception as e:
        print(f"Error deleting session data: {e}")
        raise

# API Endpoints
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat API endpoint for frontend.
    
    For buttons and mood emojis: Uses frontend's nice responses
    For text queries: Uses TOM's backend responses
    
    Request JSON:
    {
        "message": "user input text",
        "session_id": "optional session identifier",
        "mood": "optional mood selection"
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
        session_id = data.get('session_id') or session.get('session_id')
        mood = data.get('mood')
        
        # Generate session ID if not exists
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Check if user has consented to data collection
        consent_given = has_consented(session_id)
        
        # Special handling: Check if message matches buttons or moods
        message_lower = user_message.lower()
        
        # Remove common emojis for matching
        clean_message = message_lower
        for emoji in ['😔', '😕', '😐', '🙂', '😊']:
            clean_message = clean_message.replace(emoji, '').strip()
        
        # Check if this matches any special response
        for pattern, response_text in FRONTEND_SPECIAL_RESPONSES.items():
            if pattern in clean_message or pattern in message_lower:
                response = response_text
                intent = 'frontend_special'
                risk_level = 'low'
                
                # Store chat if consent given
                if consent_given:
                    store_chat(
                        message=user_message,
                        response=response,
                        mood=mood,
                        session_id=session_id,
                        intent=intent,
                        risk_level=risk_level
                    )
                
                return jsonify({
                    'response': response,
                    'intent': intent,
                    'risk_level': risk_level
                })
        
        # For all other messages, use TOM's backend responses
        response = tom.respond(user_message)
        intent = tom.predict_intent(user_message)
        risk_level = get_risk_level(intent)
        
        # Store chat if consent given
        if consent_given:
            store_chat(
                message=user_message,
                response=response,
                mood=mood,
                session_id=session_id,
                intent=intent,
                risk_level=risk_level
            )
        
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

@app.route('/api/consent', methods=['POST'])
def consent():
    """
    Store user consent for data collection.
    
    Request JSON:
    {
        "session_id": "session identifier",
        "consent_given": true | false
    }
    
    Response JSON:
    {
        "status": "stored",
        "consent_given": true | false
    }
    """
    try:
        data = request.get_json()
        if not data or 'session_id' not in data or 'consent_given' not in data:
            return jsonify({'error': 'Missing session_id or consent_given'}), 400
        
        session_id = data['session_id']
        consent_given = data['consent_given']
        
        store_consent(session_id, consent_given)
        
        return jsonify({
            'status': 'stored',
            'consent_given': consent_given
        })
    except Exception as e:
        print(f"Error in /api/consent: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/consent/check', methods=['GET'])
def check_consent():
    """
    Check if a session has given consent.
    
    Query params:
    - session_id: Session identifier
    
    Response JSON:
    {
        "consent_given": true | false
    }
    """
    try:
        session_id = request.args.get('session_id', '')
        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400
        
        consent_given = has_consented(session_id)
        
        return jsonify({
            'consent_given': consent_given
        })
    except Exception as e:
        print(f"Error in /api/consent/check: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data', methods=['DELETE'])
def delete_data():
    """Delete all chats and consent records for the supplied browser session."""
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400

        chats_deleted, consent_records_deleted = delete_session_data(session_id)
        if session.get('session_id') == session_id:
            session.pop('session_id', None)

        return jsonify({
            'status': 'deleted',
            'chats_deleted': chats_deleted,
            'consent_records_deleted': consent_records_deleted
        })
    except Exception as e:
        print(f"Error in /api/data DELETE: {e}")
        return jsonify({'error': 'Unable to delete stored data'}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """
    Get chat data statistics for analysis dashboard.
    
    Response JSON:
    {
        "total_chats": 100,
        "unique_sessions": 25,
        "date_range": ["2024-01-01", "2024-01-10"],
        "avg_message_length": 45.2,
        "message_length_distribution": {...},
        "intents": {...},
        "moods": {...},
        "risk_levels": {...},
        "top_words": [...]
    }
    """
    try:
        stats_data = get_chat_stats()
        return jsonify(stats_data)
    except Exception as e:
        print(f"Error in /api/stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chats', methods=['GET'])
def get_chats():
    """
    Get recent chat conversations for analysis.
    
    Query params:
    - limit: Number of chats to return (default: 50)
    
    Response JSON:
    {
        "chats": [
            {
                "id": 1,
                "message": "...",
                "response": "...",
                "timestamp": "...",
                "mood": "...",
                "intent": "...",
                "risk_level": "..."
            },
            ...
        ]
    }
    """
    try:
        limit = int(request.args.get('limit', 50))
        chats = get_recent_chats(limit)
        return jsonify({'chats': chats})
    except Exception as e:
        print(f"Error in /api/chats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Get chat stats
        stats = get_chat_stats()
        return jsonify({
            'status': 'online',
            'model': 'TOmChatbot (SVM)',
            'intents': len(tom.intents),
            'patterns': len(tom.patterns),
            'total_chats_stored': stats.get('total_chats', 0),
            'unique_users': stats.get('unique_sessions', 0),
            'message': 'TOM backend is running and ready!'
        })
    except Exception:
        return jsonify({
            'status': 'online',
            'model': 'TOmChatbot (SVM)',
            'intents': len(tom.intents),
            'patterns': len(tom.patterns),
            'message': 'TOM backend is running and ready!'
        })

# HTML for Analysis Dashboard
ANALYSIS_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TOM - Data Analysis Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --bg-light: #21262d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent: #58a6ff;
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .header {
            background-color: var(--bg-card);
            border-bottom: 1px solid #30363d;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header h1 {
            font-size: 18px;
            font-weight: 600;
        }
        
        .dashboard {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background-color: var(--bg-card);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
        }
        
        .stat-card h3 {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-card .value {
            font-size: 28px;
            font-weight: 600;
        }
        
        .chart-container {
            background-color: var(--bg-card);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
        }
        
        .chart-container h2 {
            font-size: 16px;
            margin-bottom: 16px;
        }
        
        .bar-chart {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .bar-item {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .bar-item .label {
            width: 120px;
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .bar-item .bar-container {
            flex: 1;
            background-color: var(--bg-light);
            border-radius: 4px;
            height: 24px;
            overflow: hidden;
        }
        
        .bar-item .bar {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .bar-color-low { background-color: var(--success); }
        .bar-color-medium { background-color: var(--accent); }
        .bar-color-high { background-color: var(--danger); }
        
        .bar-item .count {
            width: 50px;
            text-align: right;
            font-size: 12px;
            color: var(--text-muted);
        }
        
        .chat-list {
            background-color: var(--bg-card);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .chat-item {
            padding: 12px;
            border-bottom: 1px solid #30363d;
        }
        
        .chat-item:last-child {
            border-bottom: none;
        }
        
        .chat-item .user {
            color: var(--accent);
            margin-bottom: 4px;
        }
        
        .chat-item .bot {
            color: var(--text-secondary);
        }
        
        .chat-item .meta {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        
        .refresh-btn {
            background-color: var(--bg-light);
            border: 1px solid #30363d;
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        
        .refresh-btn:hover {
            background-color: #30363d;
        }
        
        .loading {
            color: var(--text-muted);
            font-style: italic;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>TOM - Data Analysis Dashboard</h1>
    </div>
    
    <div class="dashboard">
        <button class="refresh-btn" onclick="loadData()">🔄 Refresh Data</button>
        
        <div id="loading" class="loading">Loading data...</div>
        
        <div id="stats" style="display: none;">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Conversations</h3>
                    <div class="value" id="total-chats">0</div>
                </div>
                <div class="stat-card">
                    <h3>Unique Users</h3>
                    <div class="value" id="unique-users">0</div>
                </div>
                <div class="stat-card">
                    <h3>Avg Message Length</h3>
                    <div class="value" id="avg-length">0</div>
                </div>
                <div class="stat-card">
                    <h3>Date Range</h3>
                    <div class="value" id="date-range" style="font-size: 14px;">-</div>
                </div>
            </div>
            
            <div class="chart-container">
                <h2>Intent Distribution</h2>
                <div id="intent-chart" class="bar-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>Mood Distribution</h2>
                <div id="mood-chart" class="bar-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>Risk Level Distribution</h2>
                <div id="risk-chart" class="bar-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>Top 10 Words</h2>
                <div id="words-chart" class="bar-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>Recent Chats</h2>
                <div id="recent-chats" class="chat-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('stats').style.display = 'none';
            
            try {
                // Load stats
                const statsResponse = await fetch('/api/stats');
                const stats = await statsResponse.json();
                
                // Load recent chats
                const chatsResponse = await fetch('/api/chats?limit=20');
                const chatsData = await chatsResponse.json();
                
                // Update stats
                document.getElementById('total-chats').textContent = stats.total_chats || 0;
                document.getElementById('unique-users').textContent = stats.unique_sessions || 0;
                document.getElementById('avg-length').textContent = stats.avg_message_length || 0;
                document.getElementById('date-range').textContent = 
                    stats.date_range ? stats.date_range[0].split('T')[0] + ' - ' + stats.date_range[1].split('T')[0] : '-';
                
                // Render charts
                renderBarChart('intent-chart', stats.intents || {}, 'Intent');
                renderBarChart('mood-chart', stats.moods || {}, 'Mood');
                renderBarChart('risk-chart', stats.risk_levels || {}, 'Risk Level');
                renderBarChart('words-chart', stats.top_words || [], 'Word');
                
                // Render recent chats
                renderRecentChats(chatsData.chats || []);
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('stats').style.display = 'block';
                
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('loading').textContent = 'Error loading data. Check if backend is running.';
            }
        }
        
        function renderBarChart(elementId, data, labelType) {
            const container = document.getElementById(elementId);
            container.innerHTML = '';
            
            if (Object.keys(data).length === 0) {
                container.innerHTML = '<div class="no-data">No data available</div>';
                return;
            }
            
            const maxValue = Math.max(...Object.values(data));
            
            for (const [key, value] of Object.entries(data)) {
                const percentage = (value / maxValue) * 100;
                const barItem = document.createElement('div');
                barItem.className = 'bar-item';
                
                // Determine color based on label type
                let colorClass = '';
                if (labelType === 'Risk Level') {
                    colorClass = value === 'high' ? 'bar-color-high' : 'bar-color-low';
                } else {
                    colorClass = 'bar-color-medium';
                }
                
                barItem.innerHTML = `
                    <span class="label">${key}</span>
                    <div class="bar-container">
                        <div class="bar ${colorClass}" style="width: ${percentage}%">
                            <span class="sr-only">${value}</span>
                        </div>
                    </div>
                    <span class="count">${value}</span>
                `;
                container.appendChild(barItem);
            }
        }
        
        function renderRecentChats(chats) {
            const container = document.getElementById('recent-chats');
            container.innerHTML = '';
            
            if (chats.length === 0) {
                container.innerHTML = '<div class="no-data">No chats yet</div>';
                return;
            }
            
            chats.forEach(chat => {
                const chatItem = document.createElement('div');
                chatItem.className = 'chat-item';
                
                const timestamp = new Date(chat.timestamp).toLocaleString();
                const moodDisplay = chat.mood ? ` | Mood: ${chat.mood}` : '';
                const intentDisplay = chat.intent ? ` | Intent: ${chat.intent}` : '';
                const riskDisplay = chat.risk_level === 'high' ? ' | ⚠️ HIGH RISK' : '';
                
                chatItem.innerHTML = `
                    <div class="user">👤 ${chat.message}</div>
                    <div class="bot">🤖 ${chat.response}</div>
                    <div class="meta">${timestamp}${moodDisplay}${intentDisplay}${riskDisplay}</div>
                `;
                container.appendChild(chatItem);
            });
        }
        
        // Load data on page load
        loadData();
    </script>
</body>
</html>
'''

@app.route('/dashboard')
def dashboard():
    """Web-based analysis dashboard"""
    return ANALYSIS_DASHBOARD_HTML

@app.route('/privacy')
def privacy_policy():
    """Render the project privacy policy as a readable HTML page."""
    content = """
        <section>
            <h2>What TOM stores</h2>
            <p>When you choose <strong>I Agree</strong>, TOM stores the following in the local SQLite database on the machine running the backend:</p>
            <ul>
                <li>Your messages and TOM's replies</li>
                <li>Chat timestamps, selected mood, detected intent, and risk level when available</li>
                <li>A random browser session ID</li>
                <li>Your consent decision and when it was recorded</li>
            </ul>
            <p>TOM does not intentionally store your name, email address, location, IP address, browser fingerprint, or device information.</p>
        </section>

        <section>
            <h2>Your choice and deletion</h2>
            <p>Data collection is optional. Choosing <strong>No Thanks</strong> lets you continue with local fallback replies without sending chats to the backend.</p>
            <p>If you consent and later change your mind, select <strong>Delete my stored data and choose consent again</strong> in the chat screen. This permanently deletes chats and the consent record for the current browser session, clears the local session ID, and reopens the consent prompt.</p>
        </section>

        <section>
            <h2>How stored chats are used</h2>
            <p>The project team may review stored chats to evaluate and improve TOM for this educational project. TOM does not sell or share individual conversations with third parties.</p>
        </section>

        <section>
            <h2>Storage and security</h2>
            <p>Data is stored locally in <code>backend/chats.db</code>. This version does not encrypt the database, so do not share information that you would not want stored on that machine.</p>
        </section>

        <section>
            <h2>Crisis support</h2>
            <p>TOM is not a replacement for professional mental-health care. If you may harm yourself or someone else, contact local emergency services or a crisis service immediately. In the United States and Canada, call or text <strong>988</strong>.</p>
        </section>

        <section>
            <h2>Contact and updates</h2>
            <p>For questions about this project or data handling, contact the project maintainer at <a href="mailto:nitingautam2007@gmail.com">nitingautam2007@gmail.com</a>. This policy may change as the project changes.</p>
        </section>
    """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TOM - Privacy Policy</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-primary);
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        h1, h2, h3 {{
            color: var(--text-primary);
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        
        h1 {{ font-size: 2em; }}
        h2 {{ font-size: 1.5em; }}
        h3 {{ font-size: 1.25em; }}
        
        p, ul, ol {{
            color: var(--text-secondary);
            margin-bottom: 1em;
        }}

        section {{
            margin-bottom: 2.25rem;
        }}

        ul {{
            padding-left: 1.25rem;
        }}

        code {{
            background: var(--bg-card);
            border-radius: 4px;
            padding: 2px 5px;
        }}
        
        a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        pre {{
            background-color: var(--bg-card);
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        
        blockquote {{
            border-left: 3px solid var(--accent);
            padding-left: 16px;
            margin-left: 0;
            color: var(--text-secondary);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 2em;
            border-bottom: 1px solid #30363d;
            padding-bottom: 1em;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 3em;
            padding-top: 1em;
            border-top: 1px solid #30363d;
            font-size: 0.85em;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TOM - Talk To Me Privacy Policy</h1>
        <p>Effective Date: September 29, 2026</p>
    </div>
    
    <div class="content">
        {content}
    </div>
    
    <div class="footer">
        <p>Last updated: September 29, 2026</p>
        <p><a href="http://127.0.0.1:5173">Back to TOM Chatbot</a></p>
    </div>
</body>
</html>"""
        
    return html_content

if __name__ == '__main__':
    print("\n" + "="*60)
    print("TOM Backend API Server with Data Collection")
    print("="*60)
    print("\nStarting Flask server...")
    print("API will be available at: http://127.0.0.1:8000")
    print("\nEndpoints:")
    print("  POST /api/chat          - Send user messages")
    print("  POST /api/consent        - Store user consent")
    print("  GET  /api/consent/check  - Check consent status")
    print("  DELETE /api/data          - Delete a session's stored data")
    print("  GET  /api/stats          - Get chat statistics")
    print("  GET  /api/chats          - Get recent chats")
    print("  GET  /api/health         - Health check")
    print("  GET  /dashboard          - Data analysis dashboard")
    print("  GET  /privacy           - Privacy policy")
    print("\nDatabase:")
    print(f"  Location: {DB_PATH}")
    print("\nData Collection:")
    print("  ✓ Conversations stored in SQLite")
    print("  ✓ User consent required")
    print("  ✓ Stored locally with a random browser session ID")
    print("  ✓ Delete available from the chat screen")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
