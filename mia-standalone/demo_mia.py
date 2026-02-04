#!/usr/bin/env python3
"""
Demo script for MIA for All system capabilities
"""

import sys
import os
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_system():
    """Demonstrate MIA system capabilities"""
    print("=== MIA for All - My Intelligent Assistant Demo ===")
    print()
    
    # Import the system
    from mia_system import MIA_System, ConversationModule
    
    print("1. Initializing MIA System...")
    mia = MIA_System()
    print("✓ System initialized successfully")
    print()
    
    print("2. Testing Conversation Module...")
    conversation = ConversationModule()
    print("✓ Conversation module ready")
    print()
    
    print("3. Testing basic conversation...")
    # Test with a simple question
    test_question = "Kako si?"
    response = conversation.process_input(test_question)
    print(f"Question: {test_question}")
    print(f"Response: {response}")
    print()
    
    print("4. System Components Overview:")
    print("- Audio/Video Interface: Handles audio/video input/output")
    print("- Conversation Module: Manages conversation with LLM")
    print("- Context Manager: Maintains conversation context")
    print("- Personalization Module: Adapts to user preferences")
    print("- Security Layer: Ensures secure communication")
    print()
    
    print("5. System Features:")
    print("- Unlimited conversational abilities")
    print("- Audio input/output capabilities")
    print("- Video capture and analysis")
    print("- Text-based conversation with LLM")
    print("- Personalization and context management")
    print("- Security and privacy controls")
    print()
    
    print("Demo completed successfully!")
    print("To run the full system, start Ollama server and run: python mia_system.py")

if __name__ == "__main__":
    demo_system()