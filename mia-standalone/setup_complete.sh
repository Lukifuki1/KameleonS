#!/bin/bash

echo "=== Setting up MIA for All - My Intelligent Assistant ==="

# Check if we're running in a container environment
if [ -f "/.dockerenv" ]; then
    echo "Running in Docker container environment"
fi

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y portaudio19-dev python3-pyaudio

# Install Python dependencies
echo "Installing Python dependencies..."
pip install torch numpy opencv-python requests pyaudio

# Check if Ollama is installed
echo "Checking for Ollama installation..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# Start Ollama server in background
echo "Starting Ollama server..."
ollama serve &

# Give Ollama a moment to start
sleep 5

# Pull the Mistral model
echo "Pulling Mistral model..."
ollama pull mistral

echo ""
echo "=== Setup Complete ==="
echo "MIA for All is now ready to use!"
echo ""
echo "To run MIA for All:"
echo "1. Start Ollama server: ollama serve"
echo "2. Run the system: python mia_system.py"
echo ""
echo "For a quick demo: python demo_mia.py"
echo ""
echo "Note: In container environments, audio/video may not work without proper hardware access."