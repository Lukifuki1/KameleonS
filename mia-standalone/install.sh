#!/bin/bash

echo "Installing MIA for All - My Intelligent Assistant"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed. Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install torch numpy opencv-python requests pyaudio

echo "Installation complete!"
echo ""
echo "To run MIA for All:"
echo "1. Start Ollama server: ollama serve"
echo "2. Pull the Mistral model: ollama pull mistral"
echo "3. Run the system: python mia_system.py"
echo ""
echo "For a quick demo: python demo_mia.py"