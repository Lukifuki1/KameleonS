import hashlib
import json
import threading
import time
from multiprocessing import Event
from pathlib import Path

import faiss  # type: ignore
import numpy as np
from loguru import logger

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


print(type(logger))
from queue import Queue

# ======================================================
#  GLOBAL EVENTS
# ======================================================

SAFE_MODE = Event()
SAFE_MODE.set()
FALLBACK_MODE = Event()
STOP_EVENT = Event()

REGISTRY_PATH = Path("/opt/cell/system/scripts_registry.json")

# ======================================================
#  PATHS
# ======================================================

ACTIVE_BASE = Path("/media/4tb/Kameleon/cell/models/active")
TEMP_MODEL_DIR = Path("/media/4tb/Kameleon/cell/models/temp")
TRASH_BASE = Path("/media/4tb/Kameleon/cell/trash")
HASH_STORE_FILE = Path("/media/4tb/Kameleon/cell/data/model_hashes.json")
KNOWLEDGE_JSON = Path("/media/4tb/Kameleon/cell/data/knowledge.json")
MODEL_AUTOFETCH_DIR = Path("/media/4tb/Kameleon/cell/fetch")
SAFE_REASON_FILE = Path("/media/4tb/Kameleon/cell/data/safe_mode_reason.txt")
ALLOWLIST_PATH = Path("/media/4tb/Kameleon/cell/data/model_autofetch_allowlist.json")

for path in [ACTIVE_BASE, TEMP_MODEL_DIR, TRASH_BASE, MODEL_AUTOFETCH_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# ======================================================
#  SBERT + FAISS
# ======================================================

try:
    from sentence_transformers import SentenceTransformer

    sbert = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception as e:
    logger.critical(f"Napaka pri nalaganju SBERT: {e}")
    raise SystemExit(1)

try:
    pass
except Exception as e:
    logger.critical(f"FAISS modul ni na voljo: {e}")
    raise SystemExit(1)
FAISS_INDEX_FILE = Path("/media/4tb/Kameleon/cell/data/faiss.index")

# ======================================================
#  GLOBAL STRUCTURES
# ======================================================

knowledge_bank = []
knowledge_embeddings = []
knowledge_lock = threading.Lock()

AGENTS = {}
AGENT_QUEUES = {}
AGENT_LAST_USED = {}
AGENT_THREADS = {}
AUDIO_QUEUE = Queue()

MODEL_REGISTRY = {}
MODEL_LOAD_LOCK = threading.Lock()

AGENT_ROLES_FILE = Path("/opt/cell/agents/agent_roles.json")

# ======================================================
#  MODEL RUNTIME LOADER
# ======================================================


def load_model_runtime(model_path: Path):
    """Naloži model (LLM) preko llama_cpp in preveri kompatibilnost."""
    try:
        from llama_cpp import Llama
    except ImportError:
        logger.critical(
            "Manjka modul 'llama_cpp'. Namesti ga z: pip install llama-cpp-python"
        )
        return None

    # ✅ Preveri, če je podprt format
    if model_path.suffix.lower() not in {".gguf", ".bin"}:
        logger.warning(
            f"{model_path.name}: format {model_path.suffix} ni podprt za llama_cpp"
        )
        return None

    try:
        llm = Llama(
            model_path=str(model_path),
            n_gpu_layers=99,
            n_ctx=8192,
            f16_kv=True,
            use_mlock=True,
            verbose=False,
        )

        # 🧪 Sanity check: preveri, ali ima osnovne metode
        if not hasattr(llm, "__call__"):
            logger.error(
                f"{model_path.name}: objekt Llama nima callable vmesnika – nalaganje spodletelo"
            )
            return None

        return llm

    except Exception as e:
        logger.error(f"Napaka pri nalaganju modela {model_path.name}: {e}")
        return None


def register_all_models():
    """Robustno naloži vse modele iz ACTIVE_BASE in napolni MODEL_REGISTRY."""
    with MODEL_LOAD_LOCK:
        if not ACTIVE_BASE.exists():
            logger.error(f"MODEL_REGISTRY: mapa {ACTIVE_BASE} ne obstaja.")
            return

        model_count = 0

        for model_file in sorted(ACTIVE_BASE.iterdir()):
            if not model_file.is_file():
                logger.debug(
                    f"MODEL_REGISTRY: preskakujem {model_file.name} (ni datoteka)"
                )
                continue

            suffix = model_file.suffix.lower()
            if suffix not in {".gguf", ".safetensors"}:
                logger.debug(
                    f"MODEL_REGISTRY: preskakujem {model_file.name} (nepodprta končnica)"
                )
                continue

            if model_file.name in MODEL_REGISTRY:
                logger.debug(f"MODEL_REGISTRY: {model_file.name} že registriran")
                continue

            try:
                logger.info(f"MODEL_REGISTRY: nalagam model {model_file.name}")
                llm = load_model_runtime(model_file)

                if llm:
                    MODEL_REGISTRY[model_file.name] = llm
                    model_count += 1
                    logger.success(
                        f"MODEL_REGISTRY: model {model_file.name} pripravljen"
                    )
                else:
                    logger.warning(
                        f"MODEL_REGISTRY: nalaganje spodletelo za {model_file.name}"
                    )

            except Exception as e:
                logger.error(
                    f"MODEL_REGISTRY: napaka pri nalaganju {model_file.name}: {e}"
                )

        if not MODEL_REGISTRY:
            logger.critical("MODEL_REGISTRY: ni bilo mogoče naložiti nobenega modela.")
        else:
            logger.info(f"MODEL_REGISTRY: uspešno naloženih {model_count} modelov.")


def pick_model_for_agent(agent_name: str):
    """Enostavna politika: vsi agenti uporabljajo prvi model v registru."""
    if not MODEL_REGISTRY:
        return None
    return next(iter(MODEL_REGISTRY.values()))


# ======================================================
#  AGENT EXECUTION LOOP
# ======================================================


def agent_executor(agent_name: str):
    llm = pick_model_for_agent(agent_name)
    if not llm:
        logger.error(f"AGENT_EXEC: agent {agent_name} nima modela.")
        return

    q_in, q_out = AGENT_QUEUES[agent_name]
    logger.success(f"AGENT_EXEC: agent {agent_name} → zagon nitke.")

    while not STOP_EVENT.is_set():
        try:
            prompt = q_in.get(timeout=0.5)
except Exception:
            continue

        try:
            result = llm(prompt, max_tokens=256, temperature=0.7, top_p=0.95)
            out = result["choices"][0]["text"]
            q_out.put(out)
        except Exception as e:
            logger.error(f"AGENT_EXEC napaka ({agent_name}): {e}")
            q_out.put("ERROR")


# ======================================================
#  AGENT FACTORY
# ======================================================


def spawn_agent(name: str):
    if name in AGENTS:
        return

    llm = pick_model_for_agent(name)
    if not llm:
        logger.error(
            f"spawn_agent: agent '{name}' ne bo aktiviran – model ni na voljo."
        )
        return

    AGENTS[name] = {"name": name, "created": time.time(), "knowledge": []}

    AGENT_QUEUES[name] = (Queue(), Queue())
    AGENT_LAST_USED[name] = time.time()

    t = threading.Thread(target=agent_executor, args=(name,), daemon=True)
    AGENT_THREADS[name] = t
    t.start()

    logger.success(f"spawn_agent: agent '{name}' ustvarjen in aktiviran.")


# ======================================================
#  OPTIMIZED KNOWLEDGE
# ======================================================

domain_embeddings = {}
assign_lock = threading.Lock()


def assign_knowledge_to_agent(agent_name: str, domain: str):
    if agent_name not in AGENTS:
        return

    if domain not in domain_embeddings:
        domain_embeddings[domain] = sbert.encode(domain, normalize_embeddings=True)

    dom_emb = domain_embeddings[domain]

    with knowledge_lock:
        if not knowledge_bank:
            AGENTS[agent_name]["knowledge"] = []
            return

        if len(knowledge_embeddings) != len(knowledge_bank):
            knowledge_embeddings.clear()
            knowledge_embeddings.extend(
                sbert.encode(knowledge_bank, batch_size=32, normalize_embeddings=True)
            )

        relevant = []
        for text, emb in zip(knowledge_bank, knowledge_embeddings):
            sim = float(np.dot(dom_emb, emb))
            if sim >= 0.45:
                relevant.append(text)

        AGENTS[agent_name]["knowledge"] = relevant


def assign_all_agents_threaded():
    if not AGENT_ROLES_FILE.exists():
        return

    try:
        roles = json.loads(AGENT_ROLES_FILE.read_text(encoding="utf-8"))
except Exception:
        return

    threads = []
    for entry in roles:
        name = entry.get("name")
        domain = entry.get("domain")
        if not name or not domain:
            continue
        t = threading.Thread(target=assign_knowledge_to_agent, args=(name, domain))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


# ======================================================
#  AUTO-SPAWN
# ======================================================


def _autospawn_all_agents():
    if not AGENT_ROLES_FILE.exists():
        return

    try:
        roles = json.loads(AGENT_ROLES_FILE.read_text(encoding="utf-8"))
except Exception:
        return

    for entry in roles:
        name = entry.get("name")
        if name:
            spawn_agent(name)


_autospawn_all_agents()
assign_all_agents_threaded()

# ======================================================
#  KNOWLEDGE INSERTION
# ======================================================


def on_knowledge_added(new_text: str):
    with knowledge_lock:
        knowledge_bank.append(new_text)
    assign_all_agents_threaded()


# ======================================================
#  UTILITIES
# ======================================================


def log_alert(msg: str, severity: str = "info"):
    fn = getattr(logger, severity.lower(), logger.info)
    fn(msg)


def safe_mode(reason: str):
    SAFE_MODE.clear()
    FALLBACK_MODE.set()
    log_alert(f"SAFE_MODE: {reason}", "critical")
    try:
        SAFE_REASON_FILE.write_text(reason)
except Exception:
        pass


def shutdown_system():
    """Signalizira vsem komponentam za zaustavitev."""
    STOP_EVENT.set()


def hash_model_file(model_path: Path) -> str:
    """Izračuna stabilen SHA-256 heš datoteke ali celotnega direktorija, vključno s potmi in vsebino."""
    h = hashlib.sha256()

    if model_path.is_file():
        # Heširaj pot
        h.update(str(model_path.relative_to(model_path.parent)).encode("utf-8"))

        # Heširaj vsebino
        with model_path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    # Direktorij
    base = model_path
    all_files = sorted(p for p in base.rglob("*") if p.is_file())

    for file_path in all_files:
        rel = file_path.relative_to(base)
        h.update(str(rel).encode("utf-8"))

        with file_path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)

    return h.hexdigest()


# ======================================================
#  AUTOFETCH ALLOWLIST LOAD
# ======================================================

if ALLOWLIST_PATH.exists():
    try:
        MODEL_AUTOFETCH_ALLOWLIST = json.loads(
            ALLOWLIST_PATH.read_text(encoding="utf-8")
        )
        logger.info(f"Naložena allowlist: {len(MODEL_AUTOFETCH_ALLOWLIST)} elementov.")
    except Exception as e:
        logger.warning(f"Ne morem naložiti MODEL_AUTOFETCH_ALLOWLIST: {e}")
        MODEL_AUTOFETCH_ALLOWLIST = []
else:
    logger.warning(f"Datoteka {ALLOWLIST_PATH} ne obstaja. Allowlist je prazna.")
    MODEL_AUTOFETCH_ALLOWLIST = []


# ======================================================
#  INIT ENTRYPOINT
# ======================================================

if __name__ == "__main__":
    logger.info("Kameleon: inicializacija sistema")

    try:
        register_all_models()
    except Exception as e:
        logger.critical(f"Napaka pri registraciji modelov: {e}")

    try:
        _autospawn_all_agents()
        assign_all_agents_threaded()
    except Exception as e:
        logger.critical(f"Napaka pri inicializaciji agentov: {e}")

    logger.success("Kameleon: sistem pripravljen")
