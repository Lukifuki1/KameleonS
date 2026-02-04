#!/usr/bin/env bash
set -euo pipefail

# PRODUKCIJSKI LOCKDOWN & FORENZIČNI IZVOZ ZA SISTEM KAMELEON
# Avtoritativna izvedba sistema z forenzično potrjenim stanjem

DST_DISK="${1:-}"
if [[ -z "$DST_DISK" || ! -d "$DST_DISK" ]]; then
  echo "Napaka: navedi obstoječo destinacijo za forenzični izvoz."
  exit 2
fi

TS=$(date -u +"%Y%m%dT%H%M%SZ")
HN=$(hostname -f)
SNAP_DIR="${DST_DISK%/}/cell_snapshot_${HN}_${TS}"
mkdir -p "$SNAP_DIR"

echo "[1] Začetek lockdown sekvence: $(date -u)"
echo "    Izvoz bo v: $SNAP_DIR"

# -- 1. Onemogoči kritične avtomatizirane storitve --
SERVICES=(
  "model-autofetch.service"
  "cell-autoupdate.service"
  "cell-remote-listener.service"
  "cell-agents.service"
  "cell-model-watchdog.service"
)

echo "[2] Ustavitev in maskiranje storitev"
for svc in "${SERVICES[@]}"; do
  if systemctl list-units --full -all | grep -q "$svc"; then
    echo "    - Stop + mask: $svc"
    systemctl stop "$svc" || true
    systemctl disable "$svc" || true
    systemctl mask "$svc" || true
  else
    echo "    - $svc ni prisoten ali že deaktiviran"
  fi
done

# -- 2. Deaktivacija radijskih modulov --
echo "[3] Izklapljam vse radijske vmesnike"
nmcli radio all off 2>/dev/null || true
rfkill block all 2>/dev/null || true

# -- 3. Forenzična sistemska slika --
FORENSIC="$SNAP_DIR/forensics"
mkdir -p "$FORENSIC"

echo "[4] Zajem sistemskega stanja"
ss -tunap > "$FORENSIC/sockets_ss.txt" 2>/dev/null || true
lsof -i -Pn > "$FORENSIC/lsof_net.txt" 2>/dev/null || true
ps auxww > "$FORENSIC/ps_aux.txt"
pstree -p > "$FORENSIC/pstree.txt" || true
ip a > "$FORENSIC/ip_addr.txt"
ip r > "$FORENSIC/ip_route.txt"
uname -a > "$FORENSIC/uname.txt"
df -h > "$FORENSIC/disk_usage.txt"
mount > "$FORENSIC/mounts.txt"
sha256sum /media/4tb/Kameleon/cell/config/models.json > "$FORENSIC/models_json.sha256" 2>/dev/null || true

# -- 4. Kritični direktoriji sistema --
DIRS_TO_COPY=(
  "/media/4tb/Kameleon/cell/models"
  "/media/4tb/Kameleon/cell/data"
  "/media/4tb/Kameleon/cell/config"
  "/media/4tb/Kameleon/cell/agents"
  "/media/4tb/Kameleon/cell/scripts"
  "/media/4tb/Kameleon/cell/snapshots"
  "/var/log"
  "/etc/systemd/system"
)

echo "[5] Rsync kopiranje sistema"
for src in "${DIRS_TO_COPY[@]}"; do
  if [[ -d "$src" ]]; then
    dst="$SNAP_DIR$src"
    mkdir -p "$(dirname "$dst")"
    rsync -aHAX --numeric-ids --delete --protect-args "$src" "$dst" || echo "⚠️ Napaka pri rsync: $src"
  else
    echo "    Skipped: $src (ne obstaja)"
  fi
done

# -- 5. SHA256 zgoščenke --
echo "[6] Izračun SHA256 za vse datoteke"
find "$SNAP_DIR" -type f -print0 | xargs -0 sha256sum > "$FORENSIC/sha256sums.txt" || echo "⚠️ SHA256 napaka"

# -- 6. (Opcijsko) snapshot particije --
# dd if=/dev/sdX of="$FORENSIC/disk_snapshot.img" bs=4M conv=sync,noerror status=progress

# -- 7. Zakleni strukturo --
echo "[7] Zaklep snapshot strukture"
chmod -R a-w "$SNAP_DIR" || true
# find "$SNAP_DIR" -type f -exec chattr +i {} \; 2>/dev/null || true

# -- 8. Forenzični log zapis --
LOG_FILE="/var/log/cell_airgap_lockdown_${TS}.log"
{
  echo "=== CELL LOCKDOWN FORENSICS ==="
  echo "Datum UTC: $(date -u)"
  echo "Gostitelj: $HN"
  echo "Snapshot dir: $SNAP_DIR"
  echo "Onemogočene storitve: ${SERVICES[*]}"
  echo "Radio OFF: yes"
} >> "$LOG_FILE"

# -- 9. Zaključno poročilo --
echo
echo "[✓] Lockdown zaključen: $(date -u)"
echo "    ➤ Snapshot:     $SNAP_DIR"
echo "    ➤ SHA256:       $FORENSIC/sha256sums.txt"
echo "    ➤ Sistem log:   $LOG_FILE"
echo "    ➤ STATUS:       DISK ZAKLENJEN – nadaljuj s chain-of-custody postopkom"
