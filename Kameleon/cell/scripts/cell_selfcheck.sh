#!/bin/bash

LOGDIR="/media/4tb/Kameleon/cell/logs"
SELFTEST_LOG="$LOGDIR/selfcheck.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

mkdir -p "$LOGDIR"

echo "[$TIMESTAMP] 🔍 Začenjam sistemski CELL selfcheck..." >> "$SELFTEST_LOG"

# 1. Preveri Redis
echo "[*] Preverjam Redis povezljivost..." >> "$SELFTEST_LOG"
if timeout 2 redis-cli ping | grep -q PONG; then
  echo "[+] Redis je dostopen." >> "$SELFTEST_LOG"
else
  echo "[!] Redis NI dosegljiv!" >> "$SELFTEST_LOG"
fi

# 2. Preveri kritične module
CRITICAL_MODULES=(
  "/media/4tb/Kameleon/cell/system/run_system.py"
  "/media/4tb/Kameleon/cell/system/kameleon.py"
  "/media/4tb/Kameleon/cell/system/scheduler.py"
  "/media/4tb/Kameleon/cell/system/model_integrity_guard.py"
  "/media/4tb/Kameleon/cell/system/distillation_engine.py"
  "/media/4tb/Kameleon/cell/system/convergence_loop.py"
)
echo "[*] Preverjam obstoj kritičnih komponent..." >> "$SELFTEST_LOG"
for f in "${CRITICAL_MODULES[@]}"; do
  if [ -f "$f" ]; then
    echo "[+] ✔ $f obstaja." >> "$SELFTEST_LOG"
  else
    echo "[!] ✖ $f manjka!" >> "$SELFTEST_LOG"
  fi
done

# 3. Preveri integrity hash verigo
echo "[*] Preverjam integriteto preko hash zapisov..." >> "$SELFTEST_LOG"
if [ -f "/media/4tb/Kameleon/cell/system/model_integrity_verifier.py" ]; then
  python3 /media/4tb/Kameleon/cell/system/model_integrity_verifier.py --check >> "$SELFTEST_LOG" 2>&1
else
  echo "[!] Manjka: model_integrity_verifier.py" >> "$SELFTEST_LOG"
fi

# 4. Preveri, če vsi agenti imajo main()
echo "[*] Preverjam agentne module..." >> "$SELFTEST_LOG"
AGENTS_DIR="/media/4tb/Kameleon/cell/models/active"
for agent in "$AGENTS_DIR"/*; do
  AGENT_MAIN="$agent/agent.py"
  if [ -f "$AGENT_MAIN" ] && grep -q "def main()" "$AGENT_MAIN"; then
    echo "[+] Agent $(basename "$agent"): main() OK" >> "$SELFTEST_LOG"
  else
    echo "[!] Agent $(basename "$agent"): manjka main() ali datoteka ne obstaja" >> "$SELFTEST_LOG"
  fi
done

# 5. Preveri zagon pasivnih spremljevalcev
echo "[*] Preverjam ali spremljevalni moduli tečejo..." >> "$SELFTEST_LOG"
CHECKS=("scheduler.py" "plugin_health_monitor.py" "agent_selftest.py")
for mod in "${CHECKS[@]}"; do
  COUNT=$(ps aux | grep "[${mod:0:1}]${mod:1}" | wc -l)
  if [ "$COUNT" -ge 1 ]; then
    echo "[+] $mod teče." >> "$SELFTEST_LOG"
  else
    echo "[!] $mod NI aktiven!" >> "$SELFTEST_LOG"
  fi
done

# 6. Preveri uporabo diska
echo "[*] Disk uporaba za /media/4tb/Kameleon/cell:" >> "$SELFTEST_LOG"
df -h /media/4tb/Kameleon/cell >> "$SELFTEST_LOG"

echo "[$(date "+%Y-%m-%d %H:%M:%S")] ✅ SELFTEST ZAKLJUČEN." >> "$SELFTEST_LOG"
