#!/usr/bin/env python3
"""
Final verification script to ensure MIA for All system is properly set up
"""

import sys
import os
import subprocess

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("=== Checking Dependencies ===")
    
    # Check Python packages
    required_packages = ['torch', 'numpy', 'opencv-python', 'pyaudio', 'requests']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} - INSTALLED")
        except ImportError:
            print(f"✗ {package} - MISSING")
            return False
    
    print()
    return True

def check_ollama():
    """Check if Ollama is installed and running"""
    print("=== Checking Ollama ===")
    
    try:
        # Check if ollama command exists
        result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Ollama - INSTALLED")
        else:
            print("✗ Ollama - NOT INSTALLED")
            return False
            
        # Check if model exists
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Ollama server - RUNNING")
            if 'mistral' in result.stdout:
                print("✓ Mistral model - AVAILABLE")
            else:
                print("⚠ Mistral model - NOT FOUND (will be pulled automatically)")
        else:
            print("⚠ Ollama server - NOT RUNNING")
            
    except FileNotFoundError:
        print("✗ Ollama - NOT INSTALLED")
        return False
    
    print()
    return True

def test_system_import():
    """Test that the main system can be imported"""
    print("=== Testing System Import ===")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mia_system import MIA_System
        print("✓ MIA_System - IMPORT SUCCESSFUL")
        return True
    except Exception as e:
        print(f"✗ MIA_System - IMPORT FAILED: {e}")
        return False

def test_demo():
    """Test that demo script works"""
    print("=== Testing Demo Script ===")
    
    try:
        import demo_mia
        print("✓ Demo script - IMPORT SUCCESSFUL")
        return True
    except Exception as e:
        print(f"✗ Demo script - IMPORT FAILED: {e}")
        return False

def main():
    """Run all verification checks"""
    print("MIA for All - Final Verification")
    print("=" * 40)
    print()
    
    checks = [
        check_dependencies,
        check_ollama,
        test_system_import,
        test_demo
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("=" * 40)
    if all_passed:
        print("✓ ALL CHECKS PASSED - MIA for All is ready to use!")
        print()
        print("To run MIA for All:")
        print("1. Start Ollama server: ollama serve")
        print("2. Run: python mia_system.py")
        print("3. Or run demo: python demo_mia.py")
    else:
        print("✗ SOME CHECKS FAILED - Please review the errors above")
    
    return all_passed

if __name__ == "__main__":
    main()