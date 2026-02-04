# MIA for All - My Intelligent Assistant

MIA for All is a standalone personal assistant that combines audio/video capabilities with an LLM (Large Language Model) for unlimited conversational abilities.

## Features

- **Audio/Video Capabilities**: Listen, speak, capture and process video
- **LLM Integration**: Uses Ollama LLM server for natural language processing
- **Conversational AI**: Unlimited conversation capabilities
- **Personalization**: Adapts to user preferences and feedback
- **Security**: Built-in security and privacy controls

## Requirements

- Python 3.8+
- Ollama LLM server (https://ollama.com/download)
- Audio/Video hardware (microphone, speaker, camera)

## Installation

### Quick Setup

For a complete setup including Ollama installation and model pulling:
```bash
chmod +x setup_complete.sh
./setup_complete.sh
```

### Manual Installation

1. Install Ollama: https://ollama.com/download
2. Pull the Mistral model:
   ```bash
   ollama pull mistral
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start Ollama server:
   ```bash
   ollama serve
   ```
2. Run MIA for All:
   ```bash
   python mia_system.py
   ```

## System Components

- **AudioVideoInterface**: Handles audio/video input/output
- **ConversationModule**: Manages conversation with LLM
- **ContextManager**: Maintains conversation context
- **PersonalizationModule**: Adapts to user preferences
- **SecurityLayer**: Ensures secure communication

## Files in This Project

- `mia_system.py` - Main system implementation
- `demo_mia.py` - Demo script to test functionality
- `setup_complete.sh` - Complete installation script
- `run_mia.sh` - Script to run the system with Ollama
- `install.sh` - Basic installation script
- `requirements.txt` - Python dependencies
- `USAGE.md` - Detailed usage instructions

## License

MIT License