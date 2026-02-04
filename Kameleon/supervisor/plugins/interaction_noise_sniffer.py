# interaction_noise_sniffer.py

import json
import time
import statistics
from datetime import datetime

NOISE_LOG_PATH = "logs/interaction_noise_log.json"

class InteractionNoiseSniffer:
    def __init__(self):
        self.records = []

    def analyze_signal(self, interaction_id, snr_db, waveform_jitter, dropouts):
        noise_flag = snr_db < 15 or waveform_jitter > 0.05 or dropouts > 0
        self.records.append({
            "timestamp": datetime.utcnow().isoformat(),
            "interaction_id": interaction_id,
            "snr_db": round(snr_db, 2),
            "jitter": round(waveform_jitter, 4),
            "dropouts": dropouts,
            "noisy": noise_flag
        })

    def export_log(self):
        with open(NOISE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)

sniffer_instance = InteractionNoiseSniffer()

def hook(interaction_id, snr_db, waveform_jitter, dropouts):
    sniffer_instance.analyze_signal(interaction_id, snr_db, waveform_jitter, dropouts)

def flush():
    sniffer_instance.export_log()
