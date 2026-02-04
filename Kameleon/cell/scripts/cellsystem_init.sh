#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "[✗] Zaženi kot root."
    exit 1
fi

# ---------------------------------------
# 1) STRUKTURA DIREKTORIJEV
# ---------------------------------------
mkdir -p /media/4tb/Kameleon/cell/{models/{base,distilled,embed},data/{ltm,faiss,cell_logs},agents,snapshots,backup}
mkdir -p /media/4tb/Kameleon/cell/{config,scripts,tmp_vm}

# ---------------------------------------
# 2) MODELS.JSON + SHA256 HASH
# ---------------------------------------
cat >/media/4tb/Kameleon/cell/config/models.json <<EOF
{
  "reasoning_primary": "/media/4tb/Kameleon/cell/models/base/deepseek-r1-7b-q4.gguf",
  "vision_primary": "/media/4tb/Kameleon/cell/models/base/qwen3-vl",
  "code_primary": "/media/4tb/Kameleon/cell/models/base/qwen3-coder-30b",
  "embed_model": "/media/4tb/Kameleon/cell/models/embed/mxbai-embed-large"
}
EOF

sha256sum /media/4tb/Kameleon/cell/config/models.json | awk '{print $1}' > /media/4tb/Kameleon/cell/config/models.json.sha256

# ---------------------------------------
# 3) FAISS INDEKS: AVTOMATSKA GRADNJA
# ---------------------------------------
pip install -q sentence-transformers faiss-cpu || true

cat >/media/4tb/Kameleon/cell/scripts/build_faiss_index.py <<'EOF'
#!/usr/bin/env python3
import json, time
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

LTM = Path("/media/4tb/Kameleon/cell/data/ltm")
OUT = Path("/media/4tb/Kameleon/cell/data/faiss")
LOG = Path("/media/4tb/Kameleon/cell/data/logs/faiss_build.log")
OUT.mkdir(parents=True, exist_ok=True)
INDEX_PATH = OUT / "knowledge.index"

def log(msg):
    with LOG.open("a") as f:
        f.write(f"[{time.ctime()}] {msg}\n")

try:
    model = SentenceTransformer("mxbai-embed-large")
except Exception as e:
    log(f"Napaka pri modelu: {e}")
    exit(1)

texts = []
for file in LTM.rglob("*.txt"):
    try:
        txt = file.read_text().strip()
        if txt:
            texts.append(txt)
    except: continue

if not texts:
    emb = np.zeros((1, 512), dtype="float32")
    index = faiss.IndexFlatIP(512)
    index.add(emb)
    faiss.write_index(index, str(INDEX_PATH))
    log("Prazna baza: ustvarjen dummy FAISS.")
    exit(0)

try:
    emb = model.encode(texts, normalize_embeddings=True)
    emb = np.asarray(emb, dtype="float32")
    if INDEX_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        index.add(emb)
    else:
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb)
    faiss.write_index(index, str(INDEX_PATH))
    log(f"Uspešno dodanih {len(texts)} vnosov v FAISS.")
except Exception as e:
    log(f"Napaka FAISS: {e}")
    exit(2)
EOF

chmod +x /media/4tb/Kameleon/cell/scripts/build_faiss_index.py
/media/4tb/Kameleon/cell/scripts/build_faiss_index.py || true

# ---------------------------------------
# 3.1) GENERIRANJE RUNTIME DOCKER TEMPLATE-OV
# ---------------------------------------
cat >/media/4tb/Kameleon/cell/scripts/generate_runtime_templates.py <<'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

registry = json.load(open("/media/4tb/Kameleon/cell/config/model_registry.json", "r"))
out_dir = Path("/media/4tb/Kameleon/cell/templates/runtime")
out_dir.mkdir(parents=True, exist_ok=True)

for group in registry.values():
    for name, meta in group.items():
        model_path = meta["path"]
        tpl = {
            "image": "registry.local/kameleon-model:latest",
            "command": [
                "python3", "/app/infer.py",
                "--model-path", model_path,
                "--log-dir", "/logs"
            ],
            "mounts": [
                {"src": "/media/4tb/Kameleon/cell/logs", "dst": "/logs", "mode": "rw"},
                {"src": "/media/4tb/Kameleon/cell/models", "dst": "/models", "mode": "ro"}
            ],
            "network": False,
            "readonly_root": True
        }
        (out_dir / f"{name}.docker").write_text(
            json.dumps(tpl, indent=2, ensure_ascii=False), encoding="utf-8"
        )
EOF

chmod +x /media/4tb/Kameleon/cell/scripts/generate_runtime_templates.py
/media/4tb/Kameleon/cell/scripts/generate_runtime_templates.py

# ---------------------------------------
# 4) SYSTEMD STORITVE
# ---------------------------------------
cat >/etc/systemd/system/cell-agents.service <<'EOF'
[Unit]
Description=CELL Agent Scheduler
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /media/4tb/Kameleon/cell/agents/scheduler.py
Restart=always
WorkingDirectory=/media/4tb/Kameleon/cell

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/cell-model-watchdog.service <<'EOF'
[Unit]
Description=CELL Model Integrity Watchdog
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /media/4tb/Kameleon/cell/agents/model_watchdog.py
Restart=always
WorkingDirectory=/media/4tb/Kameleon/cell

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/cell-voice.service <<'EOF'
[Unit]
Description=CELL Voice Command Controller
After=sound.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /media/4tb/Kameleon/cell/agents/voice.py
Restart=always
WorkingDirectory=/media/4tb/Kameleon/cell

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------
# 5) OMOGOČI IN ZAŽENI STORITVE
# ---------------------------------------
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable cell-agents cell-model-watchdog cell-voice
systemctl start  cell-agents cell-model-watchdog cell-voice

# ---------------------------------------
# 6) STATUS STORITEV
# ---------------------------------------
echo
echo "----------------------------------------------"
echo " STATUS STORITEV:"
echo "----------------------------------------------"
for svc in cell-agents cell-model-watchdog cell-voice; do
    state=$(systemctl is-active "$svc" || echo "napaka")
    echo " - $svc : $state"
done

# ---------------------------------------
# 7) FINALNI POVZETEK
# ---------------------------------------
echo
echo "----------------------------------------------"
echo " CELL ORKESTRATOR: AKTIVEN"
echo "----------------------------------------------"
echo " LTM:       /media/4tb/Kameleon/cell/data/ltm"
echo " MODELI:    /media/4tb/Kameleon/cell/models"
echo " AGENTI:    /media/4tb/Kameleon/cell/agents"
echo " LOGI:      /media/4tb/Kameleon/cell/data/logs"
echo " FAISS LOG: /media/4tb/Kameleon/cell/data/logs/faiss_build.log"
echo "----------------------------------------------"
