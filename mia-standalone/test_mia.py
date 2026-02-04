#!/usr/bin/env python3
"""
Test script for MIA for All system
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from mia_system import MIA_System, ConversationModule, AudioVideoInterface
        print("✓ All modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic system functionality"""
    try:
        from mia_system import MIA_System
        mia = MIA_System()
        print("✓ MIA System initialized successfully")
        return True
    except Exception as e:
        print(f"✗ System initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing MIA for All system...")
    
    success = True
    success &= test_imports()
    success &= test_basic_functionality()
    
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)