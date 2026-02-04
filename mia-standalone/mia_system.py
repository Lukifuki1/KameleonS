#!/usr/bin/env python3
"""
MIA for All - My Intelligent Assistant
Standalone personal assistant using Ollama LLM server
"""

import os
import sys
import json
import time
import threading
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import torch
import numpy as np

# Audio/Video imports
import pyaudio
import wave
import cv2
from io import BytesIO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mia_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MIA_for_All")

class AudioVideoInterface:
    """Audio/Video interface for MIA system"""
    
    def __init__(self):
        self.microphone = Microphone()
        self.speaker = Speaker()
        self.camera = Camera()
        self.tts = TextToSpeech()
        self.stt = SpeechToText()
        self.video_processor = VideoProcessor()
        logger.info("Audio/Video interface initialized")
    
    def listen(self) -> str:
        """Listen to user input"""
        try:
            logger.info("Listening to user...")
            audio_data = self.microphone.record()
            text = self.stt.transcribe(audio_data)
            logger.info(f"Transcribed text: {text}")
            return text
        except Exception as e:
            logger.error(f"Error in listening: {e}")
            return ""
    
    def speak(self, text: str):
        """Speak response to user"""
        try:
            logger.info(f"Speaking: {text}")
            audio_data = self.tts.synthesize(text)
            self.speaker.play(audio_data)
        except Exception as e:
            logger.error(f"Error in speaking: {e}")
    
    def capture_video(self) -> np.ndarray:
        """Capture video frame"""
        try:
            frame = self.camera.capture()
            logger.info("Video frame captured")
            return frame
        except Exception as e:
            logger.error(f"Error in video capture: {e}")
            return None
    
    def process_video(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process video frame"""
        try:
            result = self.video_processor.analyze(frame)
            logger.info("Video processed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in video processing: {e}")
            return {}

class Microphone:
    """Microphone interface"""
    
    def __init__(self, rate=16000, chunk=1024):
        self.rate = rate
        self.chunk = chunk
        self.audio = pyaudio.PyAudio()
    
    def record(self, duration=5) -> bytes:
        """Record audio for specified duration"""
        frames = []
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        for _ in range(0, int(self.rate / self.chunk * duration)):
            data = stream.read(self.chunk)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        return b''.join(frames)

class Speaker:
    """Speaker interface"""
    
    def __init__(self, rate=16000):
        self.rate = rate
        self.audio = pyaudio.PyAudio()
    
    def play(self, audio_data: bytes):
        """Play audio data"""
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            output=True,
            frames_per_buffer=1024
        )
        
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()

class Camera:
    """Camera interface"""
    
    def __init__(self, device_id=0):
        self.device_id = device_id
        self.cap = cv2.VideoCapture(device_id)
    
    def capture(self) -> np.ndarray:
        """Capture single frame"""
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Failed to capture frame")
        return frame
    
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()

class TextToSpeech:
    """Text-to-Speech interface"""
    
    def __init__(self):
        # Using a simple TTS approach - in real implementation could use Coqui TTS or similar
        self.speakers = ["lahka ženska", "prijazna asistentka", "pomagalka"]
        logger.info("Text-to-Speech initialized")
    
    def synthesize(self, text: str) -> bytes:
        """Synthesize speech from text"""
        # In real implementation, this would use actual TTS engine
        logger.info(f"Synthesizing speech: {text}")
        # Return dummy audio data
        return b"dummy_audio_data"

class SpeechToText:
    """Speech-to-Text interface"""
    
    def __init__(self):
        # Using a simple STT approach - in real implementation could use Whisper or similar
        logger.info("Speech-to-Text initialized")
    
    def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text"""
        # In real implementation, this would use actual STT engine
        logger.info("Transcribing audio...")
        # Return dummy transcription
        return "dummy_transcription"

class VideoProcessor:
    """Video processing interface"""
    
    def __init__(self):
        logger.info("Video processor initialized")
    
    def analyze(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze video frame"""
        # In real implementation, this would use computer vision models
        height, width = frame.shape[:2]
        return {
            "frame_shape": (height, width),
            "timestamp": datetime.now().isoformat(),
            "analysis": "video_analysis_complete"
        }

class ConversationModule:
    """Main conversation module for MIA using Ollama LLM"""
    
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        self.conversation_history = []
        self.context_manager = ContextManager()
        self.personality = "lahka ženska, prijazna, pomožna, neomejena v pogovorih"
        self.model_name = "mistral"
        logger.info("Conversation module initialized with Ollama")
    
    def process_input(self, user_input: str, modality: str = "text") -> str:
        """Process user input and generate response using Ollama"""
        try:
            # Update context
            context = self.context_manager.get_context(self.conversation_history)
            
            # Prepare prompt
            prompt = self._prepare_prompt(user_input, context)
            
            # Generate response using Ollama
            response = self._generate_response_with_ollama(prompt)
            
            # Update conversation history
            self.conversation_history.append({
                "user": user_input,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error in conversation processing: {e}")
            return "Oprostite, prišlo je do napake pri obdelavi vašega vprašanja."
    
    def _prepare_prompt(self, user_input: str, context: Dict) -> str:
        """Prepare prompt for the Ollama model"""
        prompt = f"""
        Tvoj identitetni profil: {self.personality}
        Kontekst pogovora: {context}
        Uporabnik: {user_input}
        Odgovor:
        """
        return prompt
    
    def _generate_response_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama LLM"""
        try:
            # Check if Ollama server is available
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "Nisem razumel vašega vprašanja.")
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return "Oprostite, trenutno ni mogoče povezati z LLM modelom."
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama connection error: {e}")
            return "Oprostite, trenutno ni mogoče povezati z LLM modelom. Preverite, ali je Ollama zagnan."
        except Exception as e:
            logger.error(f"Error in Ollama generation: {e}")
            return "Oprostite, prišlo je do napake pri generiranju odgovora."

class ContextManager:
    """Manages conversation context"""
    
    def __init__(self):
        self.conversation_context = {}
        self.user_preferences = {}
        self.emotional_state = {}
        self.memory = Memory()
    
    def update_context(self, user_input: str, response: str):
        """Update conversation context"""
        self.conversation_context['last_input'] = user_input
        self.conversation_context['last_response'] = response
        self.conversation_context['timestamp'] = datetime.now().isoformat()
    
    def get_context(self, history: List[Dict]) -> str:
        """Get current context for conversation"""
        if not history:
            return "Novega pogovora, brez prejšnjega konteksta."
        
        # Create context from last few exchanges
        recent_history = history[-5:]  # Last 5 exchanges
        context_str = "Kontekst pogovora:\n"
        for exchange in recent_history:
            context_str += f"Uporabnik: {exchange.get('user', '. ..')}\n"
            context_str += f"Asistent: {exchange.get('response', '. ..')}\n"
        
        return context_str

class Memory:
    """Memory management for MIA"""
    
    def __init__(self):
        self.user_preferences = {}
        self.conversation_memory = []
        self.long_term_memory = {}
    
    def store_preference(self, preference: str, value: Any):
        """Store user preference"""
        self.user_preferences[preference] = value
    
    def recall_preference(self, preference: str) -> Any:
        """Recall user preference"""
        return self.user_preferences.get(preference, None)
    
    def store_conversation(self, user_input: str, response: str):
        """Store conversation for context"""
        self.conversation_memory.append({
            "user": user_input,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

class PersonalizationModule:
    """Personalization and adaptation module"""
    
    def __init__(self):
        self.user_profile = {}
        self.learning_engine = LearningEngine()
        self.adaptation_system = AdaptationSystem()
        logger.info("Personalization module initialized")
    
    def adapt_to_user(self, user_feedback: str):
        """Adapt to user preferences and feedback"""
        # In real implementation, this would analyze feedback and adjust
        logger.info(f"Adapting to user feedback: {user_feedback}")
    
    def learn_preferences(self) -> Dict[str, Any]:
        """Learn user preferences"""
        return self.learning_engine.analyze_preferences()

class LearningEngine:
    """Engine for learning user preferences"""
    
    def __init__(self):
        self.preferences = {}
    
    def analyze_preferences(self) -> Dict[str, Any]:
        """Analyze user preferences"""
        return self.preferences

class AdaptationSystem:
    """System for adapting to user needs"""
    
    def __init__(self):
        self.adaptation_parameters = {}
    
    def adjust_parameters(self):
        """Adjust system parameters based on user behavior"""
        pass

class SecurityLayer:
    """Security and privacy layer"""
    
    def __init__(self):
        self.encryption = Encryption()
        self.authentication = Authentication()
        self.privacy_controls = PrivacyControls()
        logger.info("Security layer initialized")
    
    def secure_communication(self, data: str) -> str:
        """Secure communication"""
        return self.encryption.encrypt(data)
    
    def verify_identity(self, user_id: str) -> bool:
        """Verify user identity"""
        return self.authentication.verify(user_id)

class Encryption:
    """Simple encryption for demonstration"""
    
    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        # In real implementation, use proper encryption
        return f"encrypted_{data}"

class Authentication:
    """Authentication system"""
    
    def verify(self, user_id: str) -> bool:
        """Verify user identity"""
        # In real implementation, use proper authentication
        return True

class PrivacyControls:
    """Privacy control system"""
    
    def __init__(self):
        self.privacy_settings = {
            "data_collection": True,
            "voice_recording": True,
            "video_recording": True,
            "data_sharing": False
        }
    
    def update_settings(self, settings: Dict[str, bool]):
        """Update privacy settings"""
        self.privacy_settings.update(settings)

class MIA_System:
    """Main MIA for All System class"""
    
    def __init__(self):
        self.audio_video = AudioVideoInterface()
        self.conversation = ConversationModule()
        self.context = ContextManager()
        self.security = SecurityLayer()
        self.personalization = PersonalizationModule()
        self.memory = Memory()
        self.is_running = False
        
        logger.info("MIA for All System initialized successfully")
        logger.info("Lahka ženska asistentka pripravljena za neomejene pogovore")
    
    def initialize_system(self):
        """Initialize all system components"""
        logger.info("Initializing MIA for All system...")
        # All components are initialized in __init__
        logger.info("MIA for All system initialized")
    
    def start_conversation(self):
        """Start the conversation loop"""
        self.is_running = True
        logger.info("MIA for All conversation started")
        logger.info("Pozdravljen! Sem MIA, tvoja osebna ženska asistentka.")
        logger.info("Lahko ti izpolnim vse pogovorne, video in slikovne zahteve!")
        
        # Initial greeting
        self.audio_video.speak("Pozdravljen! Sem MIA, tvoja osebna ženska asistentka. Lahko ti izpolnim vse pogovorne, video in slikovne zahteve!")
        
        while self.is_running:
            try:
                # Listen to user
                user_input = self.audio_video.listen()
                
                if user_input:
                    # Process input
                    response = self.conversation.process_input(user_input)
                    
                    # Speak response
                    self.audio_video.speak(response)
                    
                    # Update context
                    self.context.update_context(user_input, response)
                    
                    # Adapt to user
                    self.personalization.adapt_to_user(response)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                logger.info("Conversation stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                self.audio_video.speak("Oprostite, prišlo je do napake. Lahko poskusimo znova?")
                time.sleep(1)
    
    def stop_conversation(self):
        """Stop the conversation"""
        self.is_running = False
        logger.info("MIA for All conversation stopped")
    
    def handle_special_requests(self, request: str) -> str:
        """Handle special requests from user"""
        if "video" in request.lower():
            return self.handle_video_request()
        elif "image" in request.lower() or "slika" in request.lower():
            return self.handle_image_request()
        elif "conversation" in request.lower() or "pogovor" in request.lower():
            return self.handle_conversation_request()
        elif "help" in request.lower():
            return self.handle_help_request()
        else:
            return "Razumem, lahko vam pomagam s tem. Kaj bi želeli raziskati?"
    
    def handle_video_request(self) -> str:
        """Handle video-related requests"""
        try:
            frame = self.audio_video.capture_video()
            if frame is not None:
                analysis = self.audio_video.process_video(frame)
                return f"Video analiza končana. Slika ima dimenzije {analysis.get('frame_shape', 'neznano')}"
            else:
                return "Video zajem ni uspel."
        except Exception as e:
            logger.error(f"Error in video request: {e}")
            return "Oprostite, prišlo je do napake pri video analizi."
    
    def handle_image_request(self) -> str:
        """Handle image-related requests"""
        return "Slikovne zahteve so podprte. Lahko mi poveš, kaj bi želel videti v sliki?"
    
    def handle_conversation_request(self) -> str:
        """Handle conversation-related requests"""
        return "Neomejeni pogovori so podprti. Lahko razpravljamo o katerikoli temi, ki vas zanima."
    
    def handle_help_request(self) -> str:
        """Handle help requests"""
        return """
        Sem tvoja osebna ženska asistentka MIA for All!
        Moje funkcionalnosti:
        - Neomejeni pogovori o katerikoli temi
        - Audio komunikacija
        - Video analiza
        - Slikovne zahteve
        - Prilagodljiv slog
        - Varnost in zasebnost
        
        Kaj bi želel raziskati?
        """

def main():
    """Main function to start MIA for All system"""
    logger.info("Starting MIA for All System - My Intelligent Assistant")
    
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            logger.info("Ollama server is running and accessible")
        else:
            logger.warning("Ollama server might not be running properly")
    except requests.exceptions.RequestException:
        logger.warning("Ollama server is not running. Please start Ollama server before running MIA.")
        print("Prosimo, zaženite Ollama server pred zagonom MIA sistema.")
        print("Za namestitev Ollama: https://ollama.com/download")
        return
    
    # Create MIA system instance
    mia = MIA_System()
    
    # Initialize system
    mia.initialize_system()
    
    # Start conversation
    try:
        mia.start_conversation()
    except Exception as e:
        logger.error(f"Error starting MIA for All system: {e}")
        print("Napaka pri zagonu sistema MIA for All")

if __name__ == "__main__":
    main()