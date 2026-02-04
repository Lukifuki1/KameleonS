#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$HOME/Namizje/Kameleon/cell"
ISOS_DIR="${PROJECT_ROOT}/vms/isos"
IMAGES_DIR="${PROJECT_ROOT}/vms/images"
DEFAULT_NET="default"

mkdir -p "${ISOS_DIR}" "${IMAGES_DIR}"

declare -A ISO_URLS=(
  [ubuntu-24.04-live-server-amd64.iso]="https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso"
  [ubuntu-22.04-live-server-amd64.iso]="https://releases.ubuntu.com/22.04/ubuntu-22.04-live-server-amd64.iso"
  [debian-12-netinst-amd64.iso]="https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.5.0-amd64-netinst.iso"
  [rocky-9.3-x86_64-dvd.iso]="https://download.rockylinux.org/pub/rocky/9/isos/x86_64/Rocky-9.3-x86_64-dvd.iso"
  [almalinux-9.3-x86_64-dvd.iso]="https://repo.almalinux.org/almalinux/9.3/isos/x86_64/AlmaLinux-9.3-x86_64-dvd.iso"
  [centos-7-x86_64-dvd.iso]="https://cloud.centos.org/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-2009.iso"
  [sles-15-sp4.iso]="https://download.opensuse.org/distribution/leap/15.4/iso/openSUSE-Leap-15.4-DVD-x86_64.iso"
  [openwrt-23.05.4-x86-64-combined-squashfs.img.gz]="https://downloads.openwrt.org/releases/23.05.4/targets/x86/64/openwrt-23.05.4-x86-64-combined-squashfs.img.gz"
  [freertos-iot-demo.zip]="https://github.com/FreeRTOS/FreeRTOS/releases/download/202212.00/FreeRTOS-202212.00-Project-Download.zip"
  [zephyr-demo.zip]="https://github.com/zephyrproject-rtos/zephyr/releases/download/zephyr-v3.5.0/zephyr-v3.5.0.zip"
  [riot-os-demo.tar.gz]="https://github.com/RIOT-OS/RIOT/releases/download/2024.01/RIOT-2024.01.tar.gz"
  [contiki-demo.zip]="https://github.com/contiki-os/contiki/releases/download/3.0/contiki-3.0.zip"
  [tinyos-demo.zip]="https://github.com/tinyos/tinyos-main/archive/refs/heads/master.zip"
  [android-things-demo.zip]="https://github.com/androidthings/sample-bluetooth/releases/download/1.0.0/sample-bluetooth-1.0.0.zip"
  [win10-eval.iso]="https://software-download.microsoft.com/download/pr/21923.1000.231017-2218.23h2_release_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso"
  [win-server-eval.iso]="https://software-download.microsoft.com/download/pr/Windows_Server_2022_Datacenter_EVAL_en-us.iso"
  [windows-iot.iso]="https://aka.ms/IoTCoreRPI"
)

VMS=(
  "ubuntu-24.04;ubuntu-24.04-live-server-amd64.iso;20;4096;2;ubuntu24.04;yes"
  "ubuntu-22.04;ubuntu-22.04-live-server-amd64.iso;20;4096;2;ubuntu22.04;yes"
  "debian-12.5;debian-12-netinst-amd64.iso;20;4096;2;debian12;yes"
  "rocky-9.3;rocky-9.3-x86_64-dvd.iso;20;4096;2;rhel9.0;yes"
  "alma-9.3;almalinux-9.3-x86_64-dvd.iso;20;4096;2;rhel9.0;yes"
  "centos-7;centos-7-x86_64-dvd.iso;20;4096;2;rhel7.6;yes"
  "sles-15.4;sles-15-sp4.iso;20;4096;2;sles15sp4;yes"
  "openwrt;openwrt-23.05.4-x86-64-combined-squashfs.img.gz;2;512;1;generic;yes"
  "win10-eval;win10-eval.iso;60;8192;4;win10;no"
  "win-server-eval;win-server-eval.iso;60;8192;4;win2k22;no"
  "windows-iot;windows-iot.iso;4;2048;2;win10;no"
)

function log() { echo -e "\n[+] $*"; }

log "Prenos vseh javno dostopnih ISO/IMG/ZIP datotek..."

for iso in "${!ISO_URLS[@]}"; do
  TARGET="${ISOS_DIR}/${iso}"
  if [ ! -f "${TARGET}" ]; then
    log "Prenašam ${iso} ..."
    curl -L --output "${TARGET}" "${ISO_URLS[$iso]}" || {
      log "Napaka pri prenosu: ${iso} (${ISO_URLS[$iso]})"
      rm -f "${TARGET}"
      continue
    }
  else
    log "ISO/ZIP že prisoten: ${iso}"
  fi
done

log "Samodejno odpakiranje arhivov (.zip, .tar.gz)..."

for archive in "${ISOS_DIR}"/*.zip "${ISOS_DIR}"/*.tar.gz; do
  [ -e "$archive" ] || continue
  cd "${ISOS_DIR}"
  case "$archive" in
    *.zip)
      unzip -o "$archive"
      ;;
    *.tar.gz)
      tar -xzvf "$archive"
      ;;
  esac
done

cd "$PROJECT_ROOT"

log "Ustvarjam VM-je iz razpoložljivih ISO-jev in IMG-jev..."

for vmdef in "${VMS[@]}"; do
  IFS=";" read -r NAME ISO_NAME DISK_SIZE RAM VCPUS OS_VARIANT HEADLESS <<< "$vmdef"
  ISO_PATH="${ISOS_DIR}/${ISO_NAME}"
  DISK_PATH="${IMAGES_DIR}/${NAME}.qcow2"

  if [[ "${ISO_NAME}" == *.img || "${ISO_NAME}" == *.img.gz ]]; then
    UNPACKED_IMG="${ISO_PATH%.gz}"
    if [[ "${ISO_NAME}" == *.gz && ! -f "${UNPACKED_IMG}" ]]; then
      log "Razpakiram ${ISO_PATH} ..."
      gunzip -kf "${ISO_PATH}"
    fi
    if [[ ! -f "${DISK_PATH}" ]]; then
      log "Kopiram disk sliko za ${NAME} ..."
      qemu-img convert -f raw -O qcow2 "${UNPACKED_IMG}" "${DISK_PATH}"
    else
      log "Disk ${DISK_PATH} že obstaja."
    fi
    log "VM ${NAME} (embedded IMG) pripravljen za ročno emulacijo z qemu-system-*."
    continue
  fi

  if [ ! -f "${ISO_PATH}" ]; then
    echo "[!] ISO ni prisoten: ${ISO_NAME} — VM '${NAME}' bo preskočen."
    continue
  fi

  if [ -f "${DISK_PATH}" ]; then
    echo "[i] VM '${NAME}' že obstaja (${DISK_PATH}), preskakujem."
    continue
  fi

  log "Ustvarjam disk za ${NAME} (${DISK_SIZE}G)..."
  qemu-img create -f qcow2 "${DISK_PATH}" "${DISK_SIZE}G"

  log "Ustvarjam VM: ${NAME}"
  virt-install \
    --name "${NAME}" \
    --ram "${RAM}" \
    --vcpus "${VCPUS}" \
    --disk path="${DISK_PATH}",format=qcow2 \
    --cdrom "${ISO_PATH}" \
    --os-variant "${OS_VARIANT}" \
    --network network="${DEFAULT_NET}" \
    $( [[ "${HEADLESS}" == "yes" ]] && echo "--graphics none" || echo "--graphics spice") \
    --noautoconsole \
    --import || true
done

log "Vsi VM-ji in disk slike so pripravljeni. Embedded in RTOS slike zaženite z ustreznim qemu-system-arm/ppc/riscv ali ročno prilagodite zagonske parametre."
