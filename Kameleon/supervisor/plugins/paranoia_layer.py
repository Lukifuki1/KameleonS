#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔒 paranoia_layer.py
Pasivni nadzor hiperaktivnosti agentov brez posega v sistem.

• Ne spreminja nobenih obstoječih procesov ali datotek sistema.
• Samo bere immutable loge in piše lastne nadzorne zapise.
• Zazna nenadne izpade v dinamiki (surge), OUT/IN nesorazmerja in burst vzorce.
"""

import os
import re
import time
import json
import math
from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Event
from pathlib import Path
from loguru import logger

# Poti – samo branje obstoječih logov, pisanje lastnih diagnostik
PROMPT_AUDIT_LOG = Path("/opt/cell/logs/prompt_audit.log")
PARANOIA_LOG     = Path("/opt/cell/logs/paranoia_events.log")
PARANOIA_JSON    = Path("/opt/cell/logs/paranoia_report.json")

# Parametri detektorja
WINDOW_SEC             = 60          # drseče okno za trenutni tempo
BASELINE_HORIZON_MIN   = 30          # horizont za bazno statistiko
SURGE_Z_THRESHOLD      = 3.5         # prag z-ocene za "nenaden skok"
ABS_RATE_THRESHOLD     = 20          # absolutni prag dogodkov/min (dodatna varovalka)
BURST_EVENTS_THRESHOLD = 10          # minimalno število dogodkov v <10s za burst
BURST_WINDOW_SEC       = 10
OUT_IN_RATIO_THRESHOLD = 1.6         # OUT mora biti ~≈ IN; previsok ratio je sumljiv
MIN_BASELINE_EVENTS    = 60          # minimalno dogodkov za zanesljivo bazo

# Parsanje vrstic iz prompt_audit.log
# Primeri:
# 2025-10-10 12:34:56 [agent_07] IN: ...
# 2025-10-10 12:34:57 [agent_07] OUT: ...
LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<agent>[^\]]+)\] (?P<dir>IN|OUT):"
)

class EWMA:
    """Enostavna EWMA + tekoča varianca (Welford) za baseline stopnjo/min."""
    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.mean = None
        self.m2 = 0.0
        self.n = 0

    def update(self, x: float):
        # EWMA
        if self.mean is None:
            self.mean = x
        else:
            self.mean = self.alpha * x + (1 - self.alpha) * self.mean
        # Welford (za približek variance baseline točk)
        self.n += 1
        if self.n == 1:
            self.m2 = 0.0
        else:
            # uporabljamo standardno posodobitev na realnih vzorcih (x), ne EWMA
            delta = x - (self.m2 / (self.n - 1) if self.n > 1 else x)
            # robustno: hranimo sum kvadratnih odstopanj le približno
            self.m2 += delta * delta

    @property
    def std(self) -> float:
        if self.n < 2:
            return 0.0
        # robusten približek: std preko M2/n
        return math.sqrt((self.m2 / max(1, self.n - 1)))


class AgentActivity:
    """Sledi minutni hitrosti, OUT/IN razmerju in burst vzorcem."""
    def __init__(self):
        self.events_in = deque()   # časi IN
        self.events_out = deque()  # časi OUT
        self.events_all = deque()  # vsi dogodki (za burst)
        self.baseline = EWMA(alpha=0.15)
        self.per_min_counts = deque(maxlen=BASELINE_HORIZON_MIN)  # realizirane minute
        self.last_min_bucket = None
        self.bucket_count = 0

    def add_event(self, ts: float, kind: str):
        # okna za IN/OUT
        if kind == "IN":
            self.events_in.append(ts)
        else:
            self.events_out.append(ts)
        self.events_all.append(ts)

        # čistimo stare dogodke iz oken
        cutoff = ts - WINDOW_SEC
        while self.events_in and self.events_in[0] < cutoff:
            self.events_in.popleft()
        while self.events_out and self.events_out[0] < cutoff:
            self.events_out.popleft()
        while self.events_all and self.events_all[0] < ts - BURST_WINDOW_SEC:
            self.events_all.popleft()

        # minutni bucket za baseline
        minute_bucket = int(ts // 60)
        if self.last_min_bucket is None:
            self.last_min_bucket = minute_bucket

        if minute_bucket != self.last_min_bucket:
            # zaključimo prejšnjo minuto
            self.per_min_counts.append(self.bucket_count)
            self.baseline.update(self.bucket_count)
            self.bucket_count = 0
            self.last_min_bucket = minute_bucket

        self.bucket_count += 1

    def current_rate(self) -> float:
        return len(self.events_in) + len(self.events_out)  # dogodki v zadnjih WINDOW_SEC

    def ratio_out_in(self) -> float:
        ins = max(1, len(self.events_in))
        return len(self.events_out) / ins

    def burst_active(self) -> bool:
        return len(self.events_all) >= BURST_EVENTS_THRESHOLD

    def baseline_ready(self) -> bool:
        return sum(self.per_min_counts) >= MIN_BASELINE_EVENTS

    def z_score(self) -> float:
        if not self.baseline_ready():
            return 0.0
        mu = self.baseline.mean or 0.0
        sigma = self.baseline.std or 1.0
        x = self.current_rate()
        return (x - mu) / (sigma if sigma > 0 else 1.0)


def tail_file(path: Path, stop_event: Event):
    """Varno 'tail -f' branje brez zaklepanja."""
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        # skok na konec
        f.seek(0, os.SEEK_END)
        while not stop_event.is_set():
            pos = f.tell()
            line = f.readline()
            if not line:
                time.sleep(0.2)
                f.seek(pos)
                continue
            yield line


def parse_line(line: str):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    try:
        ts = int(datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S").timestamp())
        return ts, m.group("agent"), m.group("dir")
    except Exception:
        return None


def record_event(event: dict):
    # zapis v tekstovni log
    PARANOIA_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PARANOIA_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # posodobitev JSON poročila (naj zadnjih 500)
    try:
        if PARANOIA_JSON.exists():
            data = json.loads(PARANOIA_JSON.read_text(encoding="utf-8"))
        else:
            data = {"events": []}
        data["events"].append(event)
        data["events"] = data["events"][-500:]
        PARANOIA_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error(f"PARANOIA: napaka pri pisanju JSON poročila: {e}")


def run(stop_event: Event):
    logger.info("🔒 PARANOIA LAYER: aktiviran (pasivni nadzor hiperaktivnosti)")
    if not PROMPT_AUDIT_LOG.exists():
        logger.warning(f"🔒 PARANOIA: ne najdem {PROMPT_AUDIT_LOG} – čakam na nastanek datoteke.")
        while not stop_event.is_set() and not PROMPT_AUDIT_LOG.exists():
            time.sleep(1)

    agents: dict[str, AgentActivity] = defaultdict(AgentActivity)

    for line in tail_file(PROMPT_AUDIT_LOG, stop_event):
        parsed = parse_line(line)
        if not parsed:
            continue

        ts, agent, direction = parsed
        a = agents[agent]
        a.add_event(ts, direction)

        # Izračun indikatorjev
        z = a.z_score()
        rate = a.current_rate() * (60 / WINDOW_SEC)  # preračun v dogodke/min
        ratio = a.ratio_out_in()
        burst = a.burst_active()
        baseline_ok = a.baseline_ready()

        # Pogoji hiperaktivnosti "brez zunanjega razloga":
        # 1) močan nenaden skok proti baseline (z-score)
        # 2) absolutni prag visoke frekvence
        # 3) OUT/IN neravnovesje (preveč izhodov glede na vhode)
        # 4) kratek burst
        flags = []
        if baseline_ok and z >= SURGE_Z_THRESHOLD:
            flags.append(f"surge_z>={SURGE_Z_THRESHOLD} (z={z:.2f})")
        if rate >= ABS_RATE_THRESHOLD:
            flags.append(f"abs_rate>={ABS_RATE_THRESHOLD}/min (rate={rate:.1f}/min)")
        if ratio >= OUT_IN_RATIO_THRESHOLD and (len(a.events_out) + len(a.events_in)) >= 10:
            flags.append(f"OUT/IN>={OUT_IN_RATIO_THRESHOLD} (ratio={ratio:.2f})")
        if burst:
            flags.append(f"burst≥{BURST_EVENTS_THRESHOLD} v {BURST_WINDOW_SEC}s")

        if flags:
            event = {
                "ts": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "agent": agent,
                "current_rate_per_min": round(rate, 2),
                "z_score": round(z, 2),
                "out_in_ratio": round(ratio, 2),
                "burst": burst,
                "flags": flags
            }
            logger.warning(f"🔒 PARANOIA: hiperaktivnost zaznana pri {agent} -> {', '.join(flags)}")
            record_event(event)

    logger.info("🔒 PARANOIA LAYER: zaustavljen")
