#!/bin/bash

echo "Starting MIA for All - My Intelligent Assistant"
echo "================================================"

# Check if Ollama is running
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "Starting Ollama server..."
    ollama serve &
    sleep 5
else
    echo "Ollama server is already running"
fi

# Check if Mistral model is pulled
echo "Checking for Mistral model..."
if ! ollama list | grep -q "mistral"; then
    echo "Pulling Mistral model..."
    ollama pull mistral
else
    echo "Mistral model already exists"
fi

echo ""
echo "Starting MIA for All system..."
echo "================================"

# Run the main system
python mia_system.py