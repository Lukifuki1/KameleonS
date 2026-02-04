# generate_runtime_templates.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

registry = json.load(open("config/model_registry.json", "r"))
out_dir = Path("templates/runtime")
out_dir.mkdir(parents=True, exist_ok=True)

for section in registry.values():
    for name, meta in section.items():
        model_path = meta["path"]
        tpl = {
            "image": "registry.local/kameleon-model:latest",
            "command": [
                "python3",
                "/app/infer.py",
                "--model-path",
                model_path,
                "--log-dir",
                "/cell_logs",
            ],
            "mounts": [
                {
                    "src": "/media/4tb/Kameleon/cell/cell_logs",
                    "dst": "/cell_logs",
                    "mode": "rw",
                },
                {
                    "src": "/media/4tb/Kameleon/cell/models/base",
                    "dst": "/models",
                    "mode": "ro",
                },
            ],
            "network": False,
            "readonly_root": True,
        }
        (out_dir / f"{name}.docker").write_text(
            json.dumps(tpl, indent=2), encoding="utf-8"
        )
