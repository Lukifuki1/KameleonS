# plugins/trajectory_predictor.py

import json
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

DECISION_LOG = "logs/goal_score_success.json"
TRAJECTORY_LOG = "logs/trajectory_predictions.json"
WINDOW_SIZE = 25
MIN_AGGREGATE_SUPPORT = 3

class TrajectoryPredictor:
    def __init__(self):
        self.log_path = Path(TRAJECTORY_LOG)
        self.decision_data = self.load_json(DECISION_LOG)
        self.predictions = []
        self.ensure_log_exists()

    def load_json(self, path):
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def ensure_log_exists(self):
        if not self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def extract_goal_vectors(self):
        vectors = []
        for entry in self.decision_data:
            goal = entry.get("goal")
            if isinstance(goal, dict):
                vector = self.hash_goal(goal)
                vectors.append((vector, goal))
        return vectors[-WINDOW_SIZE:]

    def hash_goal(self, goal_dict):
        serialized = json.dumps(goal_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def analyze_trajectory(self):
        window = self.extract_goal_vectors()
        if not window:
            return None

        counts = Counter([v[0] for v in window])
        dominant_vector, freq = counts.most_common(1)[0]

        if freq < MIN_AGGREGATE_SUPPORT:
            return None

        dominant_goal = next(goal for vec, goal in window if vec == dominant_vector)

        prediction = {
            "timestamp": datetime.utcnow().isoformat(),
            "predicted_vector": dominant_vector,
            "predicted_goal": dominant_goal,
            "support": freq,
            "window_size": len(window)
        }

        self.predictions.append(prediction)
        self.save_prediction()
        return prediction

    def save_prediction(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.predictions, f, indent=2, ensure_ascii=False)

predictor_instance = TrajectoryPredictor()

def hook():
    return predictor_instance.analyze_trajectory()
