# sis.py
# Semantična imunologija: prefilter, konsistenca, ponovljivost, karantena
# Popravljena in robustna verzija, združljiva z orchestrator_shared.

import re
import time
from hashlib import sha256

from loguru import logger
from orchestrator_shared import knowledge_bank, knowledge_lock

# Pomnilni prostori imunskega sistema (lokalni procesni)
QUARANTINE = set()  # trajno izolirani toksini
IMMUNE_MEMORY = set()  # zaupno potrjene oblike (hash)
CONSISTENCY_INDEX = {}  # hash -> original besedilo

# Zunanji log za zavrnjene vnose (uporablja fallback monitor)
SIS_LOGFILE = "/media/4tb/Kameleon/cell/cell_logs/sis_filter.log"


def log_rejection(reason):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(SIS_LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] REJECTED: {reason}\n")


# ------------------------------------------------------------
# PRE-FILTER (odstrani očitno napačne / manipulativne vnose)
# ------------------------------------------------------------
SHORT_NOISE_RE = re.compile(r"^[A-Za-z0-9\s]{1,5}$")
BLACKLIST_PATTERNS = [
    re.compile(r"\bhallucinat", re.I),
    re.compile(r"\brandom guess\b", re.I),
    re.compile(r"\bthis may be wrong\b", re.I),
    re.compile(r"###"),
]


def prefilter(output_text):
    if not output_text:
        return None
    t = str(output_text).strip()
    if not t:
        return None
    if SHORT_NOISE_RE.fullmatch(t):
        return None
    for pat in BLACKLIST_PATTERNS:
        if pat.search(t):
            return None
    return t


# ------------------------------------------------------------
# OBSTOJEČE ZNANJE
# ------------------------------------------------------------
def _existing_texts_from_knowledge_bank():
    existing = []
    try:
        kb = knowledge_bank
    except NameError:
        return []
    if isinstance(kb, dict):
        entries = kb.get("entries", [])
        for e in entries:
            if isinstance(e, dict) and "text" in e:
                existing.append(str(e["text"]))
            else:
                existing.append(str(e))
        return existing
    if isinstance(kb, list):
        for e in kb:
            if isinstance(e, dict) and "text" in e:
                existing.append(str(e["text"]))
            else:
                existing.append(str(e))
        return existing
    return []


# ------------------------------------------------------------
# KONSISTENCA
# ------------------------------------------------------------
def detect_contradiction(new_text, existing_texts):
    if not new_text:
        return False
    nt = new_text.lower().strip()
    for et in existing_texts:
        et = et.lower().strip()
        if nt.startswith("not ") and nt[4:].strip() == et:
            return True
        if et.startswith("not ") and et[4:].strip() == nt:
            return True
        if " is not " in nt and " is " in et:
            a = nt.split(" is not ")[0].strip()
            b = et.split(" is ")[0].strip()
            if a == b:
                return True
        if " is not " in et and " is " in nt:
            a = et.split(" is not ")[0].strip()
            b = nt.split(" is ")[0].strip()
            if a == b:
                return True
    return False


def consistency_check(output_text):
    existing = _existing_texts_from_knowledge_bank()
    if detect_contradiction(output_text, existing):
        QUARANTINE.add(output_text)
        logger.info(f"SIS: kontradikcija zaznana, karantena → {output_text}")
        log_rejection("consistency_check: contradiction")
        return None
    return output_text


# ------------------------------------------------------------
# PONOVLJIVOST
# ------------------------------------------------------------
def repeatability_filter(outputs, min_count=2):
    norm_map = {}
    for o in outputs:
        s = str(o).strip()
        key = " ".join(s.split())
        norm_map.setdefault(key, []).append(s)
    stable = []
    for key, variants in norm_map.items():
        if len(variants) >= min_count:
            freq = {}
            for v in variants:
                freq[v] = freq.get(v, 0) + 1
            canonical = max(freq.items(), key=lambda x: x[1])[0]
            stable.append(canonical)
    return stable


# ------------------------------------------------------------
# HASH IDENTITETE
# ------------------------------------------------------------
def identity_hash(text):
    return sha256(text.encode("utf-8")).hexdigest()


def identity_store(output_text):
    h = identity_hash(output_text)
    CONSISTENCY_INDEX[h] = output_text
    IMMUNE_MEMORY.add(h)


# ------------------------------------------------------------
# GLAVNI FILTER
# ------------------------------------------------------------
def filter_outputs(outputs):
    if not outputs:
        return []

    cleaned = []
    for o in outputs:
        t = prefilter(o)
        if t is None:
            log_rejection("prefilter removed item")
            continue
        cleaned.append(t)

    if not cleaned:
        log_rejection("prefilter removed all")
        return []

    consistent = []
    for c in cleaned:
        t = consistency_check(c)
        if t is None:
            continue
        consistent.append(t)

    if not consistent:
        log_rejection("consistency_check removed all")
        return []

    stable = repeatability_filter(consistent, min_count=2)
    if not stable:
        log_rejection("repeatability_filter removed all")
        return []

    try:
        if hasattr(knowledge_bank, "setdefault") and isinstance(knowledge_bank, dict):
            with knowledge_lock:
                kb = knowledge_bank.setdefault("entries", [])
                for s in stable:
                    if s not in kb:
                        kb.append(s)
                        identity_store(s)
                        logger.info(f"SIS: potrjen izhod → {s}")
        elif isinstance(knowledge_bank, list):
            with knowledge_lock:
                for s in stable:
                    if s not in knowledge_bank:
                        knowledge_bank.append(s)
                        identity_store(s)
                        logger.info(f"SIS: potrjen izhod → {s}")
        else:
            for s in stable:
                identity_store(s)
                logger.info(f"SIS(fallback): potrjen izhod → {s}")
    except Exception as ex:
        logger.error(f"SIS: napaka pri zapisu v knowledge_bank: {ex}")

    return stable


# ------------------------------------------------------------
# INTERFACE ZA ORCHESTRATOR
# ------------------------------------------------------------
def is_repeatable(text: str) -> bool:
    # Začasna implementacija – vedno true
    return True
