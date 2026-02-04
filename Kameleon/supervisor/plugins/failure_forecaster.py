# failure_forecaster.py

import json
import hashlib
import statistics
from datetime import datetime

FORECAST_LOG_PATH = "logs/failure_forecast_log.json"
WINDOW_SIZE = 50
FAILURE_THRESHOLD = 0.75

class FailureForecaster:
    def __init__(self):
        self.meta_windows = {}

    def record_metadata(self, component_id, metrics: dict, failed: bool):
        if component_id not in self.meta_windows:
            self.meta_windows[component_id] = []

        self.meta_windows[component_id].append({
            "metrics": metrics,
            "failed": failed
        })

        if len(self.meta_windows[component_id]) > WINDOW_SIZE:
            self.meta_windows[component_id].pop(0)

    def predict_failures(self):
        predictions = []

        for component_id, window in self.meta_windows.items():
            if len(window) < 10:
                continue

            fail_count = sum(1 for entry in window if entry["failed"])
            fail_ratio = fail_count / len(window)

            if fail_ratio >= FAILURE_THRESHOLD:
                predictions.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "component_id": component_id,
                    "fail_ratio": round(fail_ratio, 4),
                    "window_size": len(window),
                    "prediction": "likely_failure"
                })

        return predictions

    def export_predictions(self):
        forecast = self.predict_failures()
        with open(FORECAST_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(forecast, f, indent=2, ensure_ascii=False)

forecaster_instance = FailureForecaster()

def hook(component_id, metrics: dict, failed: bool):
    forecaster_instance.record_metadata(component_id, metrics, failed)

def flush():
    forecaster_instance.export_predictions()
