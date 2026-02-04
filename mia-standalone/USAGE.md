# MIA for All - My Intelligent Assistant

## Quick Start Guide

### Prerequisites
- Python 3.8+
- Ollama LLM server (automatically installed by setup scripts)

### Installation

#### Option 1: Complete Setup (Recommended)
```bash
# Make the setup script executable
chmod +x setup_complete.sh

# Run the complete setup (installs Ollama, pulls model, installs dependencies)
./setup_complete.sh
```

#### Option 2: Manual Installation
```bash
# Install system dependencies
apt-get update
apt-get install -y portaudio19-dev python3-pyaudio

# Install Python dependencies
pip install torch numpy opencv-python requests pyaudio

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Mistral model
ollama pull mistral
```

### Running the System

1. **Start Ollama server:**
   ```bash
   ollama serve
   ```

2. **Run MIA for All:**
   ```bash
   python mia_system.py
   ```

3. **Quick Demo:**
   ```bash
   python demo_mia.py
   ```

### System Components

- **AudioVideoInterface**: Handles audio/video input/output
- **ConversationModule**: Manages conversation with LLM
- **ContextManager**: Maintains conversation context
- **PersonalizationModule**: Adapts to user preferences
- **SecurityLayer**: Ensures secure communication

### Features

- Unlimited conversational abilities
- Audio input/output capabilities
- Video capture and analysis
- Text-based conversation with LLM
- Personalization and context management
- Security and privacy controls

### Notes

- In container environments, audio/video may not work without proper hardware access
- The system requires an internet connection for LLM model downloads
- For best performance, use a machine with sufficient RAM and CPU resources