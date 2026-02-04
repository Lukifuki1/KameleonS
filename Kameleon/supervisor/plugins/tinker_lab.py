# plugins/tinker_lab.py

import json
import uuid
import time
import traceback
from datetime import datetime
from pathlib import Path

STRATEGY_DIR = "strategies/"
TINKER_LOG = "logs/tinker_lab_results.json"
SANDBOX_NAMESPACE = "tinker_sandbox"

class TinkerLab:
    def __init__(self):
        self.log_file = Path(TINKER_LOG)
        self.ensure_log_exists()

    def ensure_log_exists(self):
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def load_strategy(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        return code

    def run_strategy(self, code):
        output = {
            "timestamp": datetime.utcnow().isoformat(),
            "strategy_id": str(uuid.uuid4()),
            "success": False,
            "result": None,
            "error": None
        }

        local_env = {}

        try:
            exec(code, {**globals(), **{SANDBOX_NAMESPACE: local_env}})
            if "run" in local_env and callable(local_env["run"]):
                result = local_env["run"]()
                output["result"] = result
                output["success"] = True
            else:
                output["error"] = "Function 'run()' not defined in strategy."
        except Exception as e:
            output["error"] = traceback.format_exc()

        self.append_log(output)
        return output

    def append_log(self, entry):
        with open(self.log_file, "r+", encoding="utf-8") as f:
            logs = json.load(f)
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=2, ensure_ascii=False)
            f.truncate()

    def test_file(self, strategy_filename):
        full_path = Path(STRATEGY_DIR) / strategy_filename
        if not full_path.exists():
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "strategy_id": None,
                "success": False,
                "result": None,
                "error": f"Strategy file not found: {strategy_filename}"
            }

        code = self.load_strategy(full_path)
        return self.run_strategy(code)

tinker = TinkerLab()

def hook(strategy_filename):
    return tinker.test_file(strategy_filename)
