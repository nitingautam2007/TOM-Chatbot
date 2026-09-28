#!/usr/bin/env python3
"""
TOM - Talk To Me
================

A mental health support AI chatbot using TF-IDF + SVM classifier.
Your personal companion for emotional support and mental wellness.

Created for BTech AI/ML 3rd year project
"""

import json
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
import nltk
from nltk.stem import WordNetLemmatizer
import os
import sys
import re

# Download NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/wordnet')
except LookupError:
    print("Downloading NLTK data (first time setup)...")
    try:
        nltk.download('punkt')
        nltk.download('punkt_tab')
        nltk.download('wordnet')
    except:
        # Fallback: download all
        nltk.download('popular')


class TOmChatbot:
    """TOM - Talk To Me: ML-based mental health support chatbot using SVM"""
    
    def __init__(self, data_path='data.json'):
        """Initialize TOM with training data"""
        self.data_path = data_path
        try:
            self.lemmatizer = WordNetLemmatizer()
        except:
            # Fallback if wordnet not available
            self.lemmatizer = None
        self.intents = {}
        self.tags = []
        self.patterns = []
        self.responses = {}
        self.model = None
        self.pattern_tags = []
        self.model_trained = False
        self.conversation_history = []
        self.last_intent = None
        
    def _preprocess_text(self, text):
        """Preprocess and lemmatize text"""
        import re
        # Tokenize using simple regex (fallback if NLTK not available)
        try:
            tokens = nltk.word_tokenize(text.lower())
        except:
            # Simple word tokenization
            tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Lemmatize
        try:
            if self.lemmatizer:
                lemmatized = [self.lemmatizer.lemmatize(token) for token in tokens]
                return lemmatized
        except:
            pass
        return tokens

    def load_data(self):
        """Load training data from JSON file"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.intents = data['intents']
            
            # Prepare data for training
            for intent in self.intents:
                tag = intent['tag']
                self.tags.append(tag)
                patterns = intent['patterns']
                self.patterns.extend(patterns)
                self.responses[tag] = intent['responses']
                # Store tag for each pattern (for classifier training)
                self.pattern_tags.extend([tag] * len(patterns))
            
            print(f"Loaded {len(self.intents)} intents with {len(self.patterns)} patterns")
            return True
            
        except FileNotFoundError:
            print(f"Error: Data file '{self.data_path}' not found!")
            return False
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in '{self.data_path}'")
            return False
    
    def train_model(self):
        """Train the ML model (TF-IDF + SVM pipeline)"""
        if not self.patterns:
            print("No training data loaded. Call load_data() first.")
            return False
        
        print("Training TOM's brain (TF-IDF + SVM)...")
        
        # Create pipeline: TF-IDF vectorizer -> SVM classifier
        # Using linear kernel for text classification (works well with high-dimensional sparse data)
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(tokenizer=self._preprocess_text, stop_words='english')),
            ('clf', SVC(
                kernel='linear',      # Linear kernel works best for text classification
                C=1.0,               # Regularization parameter
                random_state=42,     # For reproducibility
                probability=False    # We don't need probability estimates
            ))
        ])
        
        # Train on all patterns with their tags
        self.model.fit(self.patterns, self.pattern_tags)
        
        self.model_trained = True
        print(f"TOM's brain trained with {len(self.patterns)} training samples")
        print(f"TOM can understand {len(self.model.classes_)} different intents")
        return True
    
    def _get_response(self, tag, user_input=""):
        """Get a response for a given tag with conversation context"""
        if tag in self.responses:
            responses = self.responses[tag]
            # For emotion tags, add engaging follow-up questions
            emotion_tags = ['sad', 'happy', 'stressed', 'anxious', 'depressed', 
                          'sadness', 'stress', 'anxiety', 'depression', 'mixed-feelings']
            if tag in emotion_tags:
                # Add engaging follow-up to the response
                base_response = random.choice(responses)
                follow_ups = [
                    " Can you tell me more about that?",
                    " How long have you been feeling this way?",
                    " What do you think is causing this?",
                    " Would you like to talk more about it?",
                    " That's completely valid. What else is on your mind?",
                ]
                # Only add follow-up if response doesn't already end with a question
                if not base_response.strip().endswith('?'):
                    return base_response + random.choice(follow_ups)
                return base_response
            return random.choice(responses)
        return random.choice(self.responses.get('none', ["I'm here to listen. How can I help?"]))
    
    def _get_engaging_response(self, intent, user_input):
        """Get an engaging response based on intent and user input"""
        # Store conversation history
        self.conversation_history.append((user_input, intent))
        self.last_intent = intent
        
        # Keep only last 5 exchanges to maintain context
        if len(self.conversation_history) > 5:
            self.conversation_history = self.conversation_history[-5:]
        
        # Get base response
        response = self._get_response(intent, user_input)
        
        # Add engaging elements based on intent
        if intent in ['sad', 'depressed', 'depression', 'sadness']:
            if len(self.conversation_history) > 1:
                response = f"I understand this is difficult for you. {response}"
            else:
                response = f"I'm here for you. {response}"
        elif intent in ['happy', 'good', 'fine']:
            response = f"I'm so glad to hear that! {response}"
        elif intent == 'greeting':
            # For greetings, make it more personal
            pass  # Already handled in _get_response
        elif intent == 'mixed-feelings':
            # Base responses already start with engaging content
            response = response
        
        return response
    
    def predict_intent(self, text):
        """Predict the intent of user input using trained classifier"""
        if not self.model_trained:
            print("TOM's brain not trained! Call train_model() first.")
            return 'none'
        
        # Check for exact match first (fast path for known patterns)
        text_lower = text.lower()
        for i, pattern in enumerate(self.patterns):
            if pattern.lower() == text_lower:
                return self.pattern_tags[i]
        
        # Predict using classifier
        predicted_tag = self.model.predict([text])[0]
        
        return predicted_tag
    
    def respond(self, text):
        """Generate a response to user input"""
        # Check for crisis keywords first (bypass ML for safety)
        crisis_keywords = ['suicide', 'kill myself', 'die', 'end it all', "don't want to live", 'can\'t go on']
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in crisis_keywords):
            return random.choice(self.responses.get('crisis', [
                "I'm deeply concerned about you. Your life is precious. Please reach out to a crisis hotline immediately. In India, call iCall at 9152987821. You are not alone."
            ]))
        
        # Predict intent
        intent = self.predict_intent(text)
        
        # Get engaging response with context
        response = self._get_engaging_response(intent, text)
        
        return response


def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_welcome():
    """Print TOM's welcome message"""
    clear_screen()
    print("=" * 60)
    print("  TOM - Talk To Me".center(60))
    print("  Your Mental Health Support Companion".center(60))
    print("=" * 60)
    print()
    print("Hello! I'm TOM - Talk To Me.")
    print("I'm here to listen and support you.")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.")
    print()
    print("-" * 60)


def main():
    """Main function to run TOM"""
    # Initialize chatbot
    tom = TOmChatbot()
    
    # Load data
    if not tom.load_data():
        print("Failed to load data. Exiting...")
        sys.exit(1)
    
    # Train model
    tom.train_model()
    
    # Welcome message
    print_welcome()
    
    # Chat loop
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Exit conditions
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("\nTOM: Goodbye! Take care of yourself. Remember, I'm always here if you need to talk.")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Get response
            response = tom.respond(user_input)
            
            # Print response
            print(f"\nTOM: {response}")
            
        except KeyboardInterrupt:
            print("\n\nTOM: Goodbye! Take care.")
            break
        except Exception as e:
            print(f"\nTOM: Sorry, I encountered an error: {e}")
            print("TOM: Let's try again. How can I help you?")


if __name__ == "__main__":
    main()
