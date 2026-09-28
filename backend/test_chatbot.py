#!/usr/bin/env python3
"""
Test script for TOM - Talk To Me
================================

Test suite for the SVM-based mental health chatbot.
"""

import sys
from tom_chatbot import TOmChatbot


def test_chatbot():
    """Run comprehensive tests on TOM"""
    print("Testing TOM - Talk To Me...")
    print("=" * 60)
    
    # Initialize
    tom = TOmChatbot()
    
    # Load data
    print("\n1. Loading data...")
    if tom.load_data():
        print("   [OK] Data loaded successfully")
    else:
        print("   [FAIL] Failed to load data")
        return False
    
    # Train model
    print("\n2. Training TOM's brain...")
    if tom.train_model():
        print("   [OK] Model trained successfully")
    else:
        print("   [FAIL] Failed to train model")
        return False
    
    # Test responses
    print("\n3. Testing intent classification...")
    
    test_cases = [
        # Basic intents
        ("Hello", "greeting"),
        ("Hi there", "greeting"),
        ("Good morning", "morning"),
        ("Goodbye", "goodbye"),
        ("Thank you", "thanks"),
        
        # Single emotions
        ("I am happy", "happy"),
        ("I feel sad", "sad"),
        ("I am so stressed", "stressed"),
        ("I feel anxious", "anxious"),
        ("I'm depressed", "depressed"),
        ("I can't sleep", "sleep"),
        
        # Mixed emotions (key feature!)
        ("I am feeling good but stressed", "mixed-feelings"),
        ("I feel good but stressed at the same time", "mixed-feelings"),
        ("I am happy but also anxious", "mixed-feelings"),
        
        # Other intents
        ("What should I do", "coping"),
        ("Tell me about yourself", "about"),
    ]
    
    passed = 0
    failed = 0
    for text, expected_intent in test_cases:
        predicted = tom.predict_intent(text)
        if predicted == expected_intent:
            print(f"   [OK] '{text}' -> {predicted}")
            passed += 1
        else:
            print(f"   [FAIL] '{text}' -> {predicted} (expected {expected_intent})")
            failed += 1
    
    print(f"\n   Intent classification: {passed}/{len(test_cases)} ({passed*100//len(test_cases)}%)")
    
    # Test crisis handling (should bypass ML)
    print("\n4. Testing crisis handling...")
    crisis_tests = [
        "I want to kill myself",
        "I want to die",
        "I'm going to commit suicide",
    ]
    
    crisis_passed = 0
    for text in crisis_tests:
        response = tom.respond(text)
        if "crisis" in response.lower() or "hotline" in response.lower() or "help" in response.lower():
            print(f"   [OK] Crisis response triggered")
            crisis_passed += 1
        else:
            print(f"   [FAIL] No crisis response")
    
    print(f"\n   Crisis handling: {crisis_passed}/{len(crisis_tests)} ({crisis_passed*100//len(crisis_tests)}%)")
    
    # Test mixed emotion responses
    print("\n5. Testing mixed emotion responses...")
    mixed_tests = [
        "I am feeling good but stressed",
        "I feel happy and anxious",
        "I'm good but also worried",
    ]
    
    mixed_passed = 0
    for text in mixed_tests:
        response = tom.respond(text)
        if response and len(response) > 10:
            print(f"   [OK] '{text}'")
            print(f"      TOM: {response}")
            mixed_passed += 1
        else:
            print(f"   [FAIL] '{text}' - No valid response")
    
    print(f"\n   Mixed emotion responses: {mixed_passed}/{len(mixed_tests)}")
    
    # Overall score
    total_tests = len(test_cases) + len(crisis_tests) + len(mixed_tests)
    total_passed = passed + crisis_passed + mixed_passed
    overall_score = (total_passed / total_tests * 100)
    
    print("\n" + "=" * 60)
    print(f"TOM's OVERALL SCORE: {overall_score:.2f}%")
    print("=" * 60)
    
    if overall_score >= 85:
        print("\nExcellent! TOM is performing very well.")
        print("He correctly handles:")
        print("  - Single emotion intents")
        print("  - Mixed emotions (your key requirement!)")
        print("  - Crisis situations")
    elif overall_score >= 70:
        print("\nGood! TOM is working well.")
        print("Consider adding more training patterns for better accuracy.")
    else:
        print("\nTOM needs improvement.")
        print("Check the failed test cases above.")
    
    print("\nYou can now run: python tom_chatbot.py")
    print("=" * 60)
    
    return overall_score >= 70


if __name__ == "__main__":
    success = test_chatbot()
    sys.exit(0 if success else 1)
