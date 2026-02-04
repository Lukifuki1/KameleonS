# voice_fidelity_checker.py

import json
import uuid
import statistics
from datetime import datetime

FIDELITY_LOG_PATH = "logs/voice_fidelity_log.json"

class VoiceFidelityChecker:
    def __init__(self):
        self.records = []

    def analyze_voice(self, interaction_id, pitch_values, speech_rate, modulation_score):
        natural_pitch_variation = statistics.stdev(pitch_values) if len(pitch_values) > 1 else 0.0
        naturalness_index = round(
            (modulation_score * 0.5 + (1 - abs(speech_rate - 1.0)) * 0.3 + min(natural_pitch_variation / 50, 1.0) * 0.2),
            3
        )

        self.records.append({
            "timestamp": datetime.utcnow().isoformat(),
            "interaction_id": interaction_id,
            "pitch_variation": round(natural_pitch_variation, 3),
            "speech_rate": round(speech_rate, 3),
            "modulation_score": round(modulation_score, 3),
            "naturalness_index": naturalness_index
        })

    def export_log(self):
        with open(FIDELITY_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)

checker_instance = VoiceFidelityChecker()

def hook(interaction_id, pitch_values: list, speech_rate: float, modulation_score: float):
    checker_instance.analyze_voice(interaction_id, pitch_values, speech_rate, modulation_score)

def flush():
    checker_instance.export_log()
