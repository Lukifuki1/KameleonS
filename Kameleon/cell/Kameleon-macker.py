#!/usr/bin/env python3
import atexit
import fcntl
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from loguru import logger

LOGFILE = "kameleon_autosetup.log"
LOCKFILE = "/tmp/kameleon_autosetup.lock"
LOG_MAX_MB = 10
SILENT = "--silent" in sys.argv
INTERACTIVE = "--interactive" in sys.argv

sys.modules["ROOT"] = Path("/media/4tb/Kameleon/cell")


def preveri_venv():
    venv = os.environ.get("VIRTUAL_ENV", None)
    py_exec = os.path.realpath(sys.executable)
    if not venv or not py_exec.startswith(venv):
        log("NAPAKA: Skripta mora teči znotraj aktivnega virtualnega okolja (venv)!")
        sys.exit(140)
    if os.geteuid() == 0:
        log("NAPAKA: Skripta ne sme teči kot root/sudo znotraj venv!")
        sys.exit(141)
    forbidden = ["/usr", "/etc", "/usr/local/bin"]
    for f in forbidden:
        if os.getcwd().startswith(f):
            log(f"NAPAKA: Trenutni direktorij je prepovedan: {f}")
            sys.exit(142)


def blokiraj_sistemske_operacije():
    import builtins

    orig_open = builtins.open

    def open_guard(path, *args, **kwargs):
        if any(path.startswith(f) for f in ["/usr", "/etc", "/usr/local/bin"]):
            raise PermissionError(f"Pisanje v sistemske poti je prepovedano: {path}")
        return orig_open(path, *args, **kwargs)

    builtins.open = open_guard

    orig_run = subprocess.run

    def run_guard(cmd, *args, **kwargs):
        if isinstance(cmd, list):
            cmd_str = " ".join(cmd)
        else:
            cmd_str = cmd
        forbidden = ["apt", "pip", "systemctl", "docker", "bash"]
        for f in forbidden:
            if cmd_str.startswith(f) and "VIRTUAL_ENV" not in os.environ:
                raise PermissionError(
                    f"Izvajanje sistemske operacije prepovedano izven venv: {cmd_str}"
                )
        # Prepreči globalne interpretere
        if "python" in cmd_str and sys.executable not in cmd_str:
            raise PermissionError(
                f"Izvajanje globalnega Pythona ni dovoljeno: {cmd_str}"
            )
        return orig_run(cmd, *args, **kwargs)

    subprocess.run = run_guard

    orig_popen = subprocess.Popen

    def popen_guard(cmd, *args, **kwargs):
        if isinstance(cmd, list):
            cmd_str = " ".join(cmd)
        else:
            cmd_str = cmd
        forbidden = ["apt", "pip", "systemctl", "docker", "bash"]
        for f in forbidden:
            if cmd_str.startswith(f) and "VIRTUAL_ENV" not in os.environ:
                raise PermissionError(
                    f"Izvajanje sistemske operacije prepovedano izven venv: {cmd_str}"
                )
        if "python" in cmd_str and sys.executable not in cmd_str:
            raise PermissionError(
                f"Izvajanje globalnega Pythona ni dovoljeno: {cmd_str}"
            )
        return orig_popen(cmd, *args, **kwargs)

    subprocess.Popen = popen_guard


def preveri_poti_subprocesov(cmd):
    forbidden = ["/usr", "/etc", "/usr/local/bin"]
    for f in forbidden:
        if any(f in str(x) for x in cmd if isinstance(x, str)):
            log(f"NAPAKA: Podproces zlorablja sistemsko pot: {cmd}")
            sys.exit(143)


def log(msg):
    if not SILENT:
        print(msg)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")


def rotate_log():
    try:
        if not os.path.exists(LOGFILE):
            return  # Nič za rotirat

        if os.path.getsize(LOGFILE) < LOG_MAX_MB * 1024 * 1024:
            return  # Še ni dovolj veliko

        base = LOGFILE.rsplit(".log", 1)[0]

        # Rotacija: log.4.log ← log.3.log ← log.2.log ← log.1.log ← system.log
        for i in range(4, 0, -1):
            old = f"{base}.{i}.log"
            nxt = f"{base}.{i + 1}.log"
            if os.path.exists(old):
                os.rename(old, nxt)

        os.rename(LOGFILE, f"{base}.1.log")
        open(LOGFILE, "w", encoding="utf-8").close()  # Ustvari prazno datoteko

    except Exception as e:
        print(f"[rotate_log] Napaka pri rotaciji loga: {e}")


def backup_configs():
    backup_dir = f"backup_{time.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    for pattern in ["cell/config/*.json", "cell/**/*.yaml", "cell/**/*.yml"]:
        for fpath in glob.glob(pattern, recursive=True):
            dest = os.path.join(backup_dir, os.path.relpath(fpath, "cell"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(fpath, dest)
    shutil.copy2(LOGFILE, os.path.join(backup_dir, os.path.basename(LOGFILE)))
    log(f"Backup konfiguracij in loga izveden v {backup_dir}")


def remove_lockfile():
    if os.path.exists(LOCKFILE):
        try:
            os.remove(LOCKFILE)
        except OSError as e:
            logger.warning(f"Ne morem odstraniti LOCKFILE: {e}")


atexit.register(remove_lockfile)


def check_root():
    if os.geteuid() != 0:
        log("NAPAKA: Skripto moraš pognati kot root (sudo).")
        sys.exit(100)


def check_debian():
    if not os.path.exists("/etc/apt/sources.list"):
        log("NAPAKA: Podprt je samo Debian/Ubuntu sistem.")
        sys.exit(111)


def single_instance():
    f = open(LOCKFILE, "w")
    try:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("NAPAKA: Druga instanca skripte že teče.")
        sys.exit(101)


# noinspection PyUnreachableCode
def check_python_version():
    if sys.version_info < (3, 8):
        log("NAPAKA: Zahtevan je Python 3.8 ali novejši.")
        sys.exit(102)


def check_network():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        log("Internetna povezava aktivna.")
    except Exception:
        log("NAPAKA: Ni internetne povezave.")
        sys.exit(103)


def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        log(f"Ustvarjena mapa: {path}")


def install_python_package(pkg):
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", pkg],
            check=True,
            capture_output=True,
            text=True,
        )
        log(f"Nameščen python paket: {pkg}")
    except subprocess.CalledProcessError as e:
        log(f"NAPAKA pri python paketu {pkg}: {e.stderr}")
        if INTERACTIVE:
            input("Nadaljujem? (Enter)")
        else:
            sys.exit(104)


def install_system_package(pkg):
    if shutil.which(pkg) is None:
        try:
            subprocess.run(["apt", "update"], check=True)
            subprocess.run(["apt", "install", "-y", pkg], check=True)
            log(f"Nameščen sistemski paket: {pkg}")
        except subprocess.CalledProcessError as e:
            log(f"NAPAKA pri sistemskem paketu {pkg}: {e.stderr}")
            if INTERACTIVE:
                input("Nadaljujem? (Enter)")
            else:
                sys.exit(105)
    else:
        log(f"Sistemski paket že nameščen: {pkg}")


def check_docker():
    try:
        subprocess.run(
            ["docker", "ps"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        log("Docker deluje.")
    except Exception:
        log("Docker ni nameščen – nameščam ...")
        try:
            subprocess.run(["apt", "update"], check=True)
            subprocess.run(["apt", "install", "-y", "docker.io"], check=True)
            subprocess.run(["systemctl", "start", "docker"], check=True)
            log("Docker nameščen in zagnan.")
        except Exception as e:
            log(f"NAPAKA pri dockerju: {e}")
            if INTERACTIVE:
                input("Nadaljujem? (Enter)")
            else:
                sys.exit(106)


def deep_fix_json_paths(obj, root_dir):
    if isinstance(obj, dict):
        return {k: deep_fix_json_paths(v, root_dir) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_fix_json_paths(v, root_dir) for v in obj]
    if isinstance(obj, str):
        if not os.path.exists(obj):
            alt = os.path.join(root_dir, obj) if not os.path.isabs(obj) else obj
            if os.path.exists(alt):
                return alt
        return obj
    return obj


def fix_json_paths(path, root_dir):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        fixed = deep_fix_json_paths(data, root_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fixed, f, indent=2)
        log(f"Popravljene poti v JSON: {path}")
    except Exception as e:
        log(f"NAPAKA v JSON popravljanju {path}: {e}")
        if INTERACTIVE:
            input("Nadaljujem? (Enter)")
        else:
            sys.exit(107)


def najdi_py_skripte(root_dir):
    return [y for x in os.walk(root_dir) for y in glob.glob(os.path.join(x[0], "*.py"))]


def preveri_shebang_encoding(skripta):
    popravljeno = False
    try:
        with open(skripta, "r", encoding="utf-8") as f:
            vrstice = f.readlines()
    except Exception as e:
        log(f"NAPAKA pri branju {skripta}: {e}")
        return

    # Dodaj shebang če manjka
    if not vrstice or not vrstice[0].startswith("#!"):
        vrstice = ["#!/usr/bin/env python3\n"] + vrstice
        popravljeno = True

    # Dodaj encoding deklaracijo če manjka
    enc_decl = "# -*- coding: utf-8 -*-\n"
    if len(vrstice) < 2 or "coding" not in "".join(vrstice[:2]):
        vrstice = [vrstice[0], enc_decl] + vrstice[1:]
        popravljeno = True

    if popravljeno:
        try:
            with open(skripta, "w", encoding="utf-8") as f:
                f.writelines(vrstice)
            log(f"AUTOPOP: Dodan shebang/encoding v {skripta}")
        except Exception as e:
            log(f"NAPAKA pri pisanju {skripta}: {e}")


def preveri_pravice(skripta):
    try:
        if not os.access(skripta, os.R_OK):
            os.chmod(skripta, 0o644)
            log(f"AUTOPOP: Dodane bralne pravice {skripta}")
        if skripta.endswith((".sh", ".py")) and not os.access(skripta, os.X_OK):
            os.chmod(skripta, 0o755)
            log(f"AUTOPOP: Dodane izvršilne pravice {skripta}")
    except Exception as e:
        log(f"NAPAKA pri pravicah {skripta}: {e}")


def preveri_world_writable(pot):
    if os.path.exists(pot):
        st = os.stat(pot)
        if st.st_mode & 0o002:
            log(f"OPOZORILO: {pot} je globalno zapisljiv! To je varnostno tvegano.")


def preveri_in_popravi_main(skripta):
    try:
        with open(skripta, "r", encoding="utf-8") as f:
            vsebina = f.read()
        if "if __name__" not in vsebina:
            with open(skripta, "a", encoding="utf-8") as f:
                f.write('\nif __name__ == "__main__":\n    main()\n')
            log(f"AUTOPOP: Dodan main-guard v {skripta}")
    except Exception as e:
        log(f"NAPAKA main guard {skripta}: {e}")


def preveri_python_kompatibilnost(skripta):
    try:
        subprocess.run(
            [sys.executable, "-m", "py_compile", skripta],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        log(
            f"NAPAKA v Python sintaksi: {skripta} -> {e.stderr.decode(errors='ignore').strip()}"
        )
        if not INTERACTIVE:
            rollback()
            sys.exit(198)


def robustna_modularna_validacija(root_dir):
    napak = []
    skripte = najdi_py_skripte(root_dir)
    for s in skripte:
        try:
            preveri_shebang_encoding(s)
            preveri_pravice(s)
            preveri_world_writable(s)
            preveri_in_popravi_main(s)
            preveri_python_kompatibilnost(s)
        except Exception as e:
            log(f"NAPAKA v {s}: {e}")
            napak.append(s)
    if napak:
        log(f"NAPAKA: Problematične skripte: {napak}")
        if not INTERACTIVE:
            rollback()
            sys.exit(199)


def self_diagnostic():
    try:
        open("/tmp/test_write", "w").close()
        os.remove("/tmp/test_write")
        log("SanityCheck: Disk I/O OK.")
    except Exception as e:
        log(f"NAPAKA: Disk ni zapisljiv: {e}")
        rollback()
        sys.exit(200)
    try:

        log("SanityCheck: psutil OK.")
    except Exception:
        log("NAPAKA: psutil ni dostopen, ponovno nameščam...")
        install_python_package("psutil")


def log_process_output(process, label):
    while True:
        line = process.stdout.readline()
        if not line:
            break
        log(f"[{label} STDOUT] {line.decode(errors='ignore').strip()}")
        time.sleep(0.01)
    err = process.stderr.read()
    if err:
        log(f"[{label} STDERR] {err.decode(errors='ignore').strip()}")


def healthcheck_http(endpoint, timeout=3):
    import requests

    try:
        resp = requests.get(timeout=5, timeout=5, endpoint, timeout=timeout)
        if resp.status_code == 200:
            log(f"HTTP healthcheck OK: {endpoint}")
        else:
            log(f"NAPAKA HTTP healthcheck {endpoint}: status {resp.status_code}")
            rollback()
            sys.exit(121)
    except Exception as e:
        log(f"NAPAKA HTTP healthcheck {endpoint}: {e}")
        rollback()
        sys.exit(121)


def preveri_in_konvertiraj_ggml_v_gguf():
    import subprocess
    from pathlib import Path

    active_dir = Path("cell/models/active")
    quarantine_dir = Path("cell/models/quarantine")
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    for distilled_path in active_dir.glob("*.distilled"):
        gguf_path = distilled_path.with_suffix(".gguf")
        if gguf_path.exists():
            log(f"Preskakujem, ker .gguf že obstaja: {gguf_path.name}")
            continue

        log(f"Poskus konverzije: {distilled_path.name}")
        try:
            subprocess.run(
                [
                    sys.executable,
                    "convert_llama_ggml_to_gguf.py",
                    "--input",
                    str(distilled_path),
                    "--output",
                    str(gguf_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            log(f"Konverzija uspešna: {gguf_path.name}")
        except subprocess.CalledProcessError as e:
            log(f"NAPAKA konverzije: {distilled_path.name} – {e.stderr.strip()}")
            quarantine = quarantine_dir / distilled_path.name
            try:
                distilled_path.rename(quarantine)
                log(f"Premaknjeno v karanteno: {quarantine.name}")
            except Exception as ex:
                log(f"NAPAKA pri premiku v karanteno: {ex}")


def healthcheck_grpc(endpoint, grpc_health=None):
    import grpc
    from grpc_health.v1 import health_pb2, health_pb2_grpc

    try:
        host, port = endpoint.split(":")
        address = f"{host}:{port}"
        service_name = grpc_health or ""  # omogoča ciljanje določene GRPC storitve

        channel = grpc.insecure_channel(address)
        grpc.channel_ready_future(channel).result(timeout=5)

        stub = health_pb2_grpc.HealthStub(channel)
        response = stub.Check(
            health_pb2.HealthCheckRequest(service=service_name), timeout=3
        )

        if response.status == health_pb2.HealthCheckResponse.SERVING:
            log(f"GRPC healthcheck OK: {endpoint} (service='{service_name}')")
        else:
            log(f"NAPAKA GRPC healthcheck {endpoint}: status {response.status}")
            rollback()
            sys.exit(122)

    except grpc.FutureTimeoutError:
        log(
            f"NAPAKA GRPC healthcheck {endpoint}: povezava ni bila vzpostavljena pravočasno."
        )
        rollback()
        sys.exit(122)
    except Exception as e:
        log(f"NAPAKA GRPC healthcheck {endpoint}: {e}")
        rollback()
        sys.exit(122)


def start_python(script):
    try:
        p = subprocess.Popen(
            [sys.executable, script], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        threading.Thread(
            target=log_process_output, args=(p, script), daemon=True
        ).start()
        time.sleep(1)
        if p.poll() is not None and p.returncode != 0:
            log(f"NAPAKA: Python modul {script} je takoj crashnil!")
            rollback()
            sys.exit(109)
        log(f"Python modul zagnan: {script}")
    except Exception as e:
        log(f"NAPAKA pri zagonu python modula {script}: {e}")
        rollback()
        sys.exit(110)


def docker_healthcheck(name):
    try:
        subprocess.run(["docker", "inspect", name], check=True, stdout=subprocess.PIPE)
        log(f"Docker kontejner OK: {name}")
    except Exception:
        log(f"NAPAKA: Docker kontejner ni zdrav: {name}")
        rollback()
        sys.exit(112)


def build_and_run_docker(dockerfile, context):
    name = os.path.splitext(os.path.basename(dockerfile))[0]
    try:
        subprocess.run(
            ["docker", "build", "-t", name, "-f", dockerfile, context], check=True
        )
        subprocess.run(
            ["docker", "rm", "-f", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        subprocess.run(["docker", "run", "-d", "--name", name, name], check=True)
        log(f"Docker image zagnan: {name}")
        docker_healthcheck(name)
    except subprocess.CalledProcessError as e:
        log(f"NAPAKA v docker procesu {name}: {e.stderr}")
        rollback()
        sys.exit(113)


def run_shell_script(script):
    try:
        subprocess.run(["bash", script], check=True, capture_output=True, text=True)
        log(f"Shell skript OK: {script}")
    except subprocess.CalledProcessError as e:
        log(f"NAPAKA v skripti {script}: {e.stderr}")
        if INTERACTIVE:
            input("Nadaljujem? (Enter)")
        else:
            rollback()
            sys.exit(114)


def test_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    res = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    if res == 0:
        log(f"OPOZORILO: Port {port} je že zaseden.")
    else:
        log(f"Port {port} prost.")


def write_service(service_name, exec_start, working_directory):
    service_file = f"""\n[Unit]
Description=Kameleon {service_name}
After=network.target

[Service]
Type=simple
WorkingDirectory={working_directory}
ExecStart={exec_start}
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
"""
    path = f"/etc/systemd/system/{service_name}.service"
    with open(path, "w", encoding="utf-8") as f:
        f.write(service_file)
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", service_name])
    subprocess.run(["systemctl", "start", service_name])
    log(f"Systemd service ustvarjen in zagnan: {service_name}")


def write_watchdog(script, interval=60):
    wd_script = f"""#!/bin/bash
while true; do
    if ! pgrep -f "{script}"; then
        {sys.executable} {script} &
    fi
    sleep {interval}
done
"""
    path = f"/usr/local/bin/kameleon_watchdog_{os.path.basename(script)}.sh"
    with open(path, "w", encoding="utf-8") as f:
        f.write(wd_script)
    os.chmod(path, 0o755)
    log(f"Watchdog skripta ustvarjena: {path}")
    return path


def hash_integrity(file_path):
    import hashlib

    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def verify_integrity(files):
    integrity_ok = True
    for file in files:
        if os.path.exists(file):
            hashval = hash_integrity(file)
            log(f"INTEGRITETA: {file} | SHA256: {hashval}")
        else:
            log(f"INTEGRITETA: {file} | MANJKA!")
            integrity_ok = False
    return integrity_ok


def monitor_resources(threshold_cpu=90, threshold_mem=95):
    import psutil

    cpu = psutil.cpu_percent(interval=2)
    mem = psutil.virtual_memory().percent
    log(f"Sistemska zasedenost: CPU {cpu}%, RAM {mem}%")
    if cpu > threshold_cpu or mem > threshold_mem:
        log("OPOZORILO: Visoka zasedenost sistema! Prekinitve niso priporočene.")
        if not INTERACTIVE:
            rollback()
            sys.exit(130)


def rollback():
    log("POZOR: Rollback izvajanje...")
    try:
        docker_ps = subprocess.run(
            ["docker", "ps", "-q"], capture_output=True, text=True
        )
        for cid in docker_ps.stdout.strip().split("\n"):
            if cid:
                subprocess.run(
                    ["docker", "rm", "-f", cid],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
        log("Vsi docker kontejnerji so ustavljeni in odstranjeni.")
    except Exception as e:
        log(f"NAPAKA pri rollbacku dockerjev: {e}")
    for unit in [
        "kameleon_api_server",
        "kameleon_orchestrator_shared",
        "kameleon_run_system",
        "kameleon_scheduler",
        "kameleon_multi_agent_orchestrator",
        "kameleon_super-orkestrator",
    ]:
        subprocess.run(
            ["systemctl", "stop", unit], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    log("Rollback končan.")


def main():
    preveri_venv()
    blokiraj_sistemske_operacije()

    rotate_log()
    backup_configs()
    monitor_resources()
    single_instance()
    check_python_version()
    check_network()

    root = os.path.abspath(os.path.dirname(__file__))
    log("=== KAMELEON avtomatizirana venv postavitev ===")

    required_dirs = [
        "cell/agents",
        "cell/config",
        "cell/data",
        "cell/docs",
        "cell/knowledge_bank",
        "cell/logs",
        "cell/models/active",
        "cell/models/base",
        "cell/models/distilled",
        "cell/models/embed",
        "cell/orchestrator",
        "cell/runtime/fused_models",
        "cell/runtime/sandbox_sessions",
        "cell/scripts",
        "cell/security",
        "cell/system",
        "cell/templates",
        "cell/vms",
    ]
    for d in required_dirs:
        ensure_dir_exists(os.path.join(root, d))

    for conf in glob.glob(os.path.join(root, "cell/config/*.json")):
        fix_json_paths(conf, root)

    robustna_modularna_validacija(root)

    python_packages = [
        "docker",
        "requests",
        "psutil",
        "flask",
        "pyyaml",
        "torch",
        "transformers",
        "scikit-learn",
        "pandas",
        "gunicorn",
        "uvicorn",
        "fastapi",
        "paramiko",
        "cryptography",
        "aiohttp",
        "python-dotenv",
        "grpcio",
        "grpcio-health-checking",
        "pytest",
    ]
    for p in python_packages:
        install_python_package(p)

    for sh in glob.glob(os.path.join(root, "cell/scripts/*.sh")):
        run_shell_script(sh)

    modules = [
        ("cell/system/api_server.py", "http://localhost:5000/healthz"),
        ("cell/system/orchestrator_shared.py", None),
        ("cell/system/run_system.py", None),
        ("cell/system/scheduler.py", None),
        ("multi_agent_orchestrator.py", None),
        ("super-orkestrator.py", None),
    ]
    for m, health in modules:
        path = os.path.join(root, m)
        if os.path.exists(path):
            start_python(path)
            if health and health.startswith("http"):
                healthcheck_http(health)
            if health and health.startswith("grpc"):
                healthcheck_grpc(health[7:])
        else:
            log(f"OPOZORILO: Modul manjka: {m}")

    for port in [80, 443, 8080, 8443, 5000]:
        test_port(port)

    integrity_files = [
        "multi_agent_orchestrator.py",
        "super-orkestrator.py",
        "cell/system/run_system.py",
        "cell/system/api_server.py",
    ]
    verify_integrity([os.path.join(root, f) for f in integrity_files])

    # --- OPEN WEB-UI FULL AUTOINTEGRACIJA ---
    open_webui_dir = os.path.join(root, "open-webui")
    dockerfile_path = os.path.join(open_webui_dir, "Dockerfile")

    if not os.path.isdir(open_webui_dir):
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/open-webui/open-webui.git",
                    open_webui_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            log("Open WebUI repozitorij avtomatsko kloniran.")
        except subprocess.CalledProcessError as e:
            log(f"NAPAKA pri kloniranju Open WebUI: {e.stderr}")
            if not INTERACTIVE:
                rollback()
                sys.exit(191)

    for ext in ("*.json", "*.yaml", "*.yml"):
        for fpath in glob.glob(os.path.join(open_webui_dir, "**", ext), recursive=True):
            try:
                if ext.endswith("json"):
                    fix_json_paths(fpath, open_webui_dir)
            except Exception as e:
                log(f"NAPAKA pri popravljanju poti v {fpath}: {e}")

    for s in najdi_py_skripte(open_webui_dir):
        try:
            preveri_shebang_encoding(s)
            preveri_pravice(s)
            preveri_world_writable(s)
            preveri_in_popravi_main(s)
            preveri_python_kompatibilnost(s)
        except Exception as e:
            log(f"NAPAKA v open-webui skripti {s}: {e}")

    if os.path.exists(dockerfile_path):
        try:
            subprocess.run(
                [
                    "docker",
                    "build",
                    "-t",
                    "open-webui",
                    "-f",
                    dockerfile_path,
                    open_webui_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["docker", "rm", "-f", "open-webui"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    "open-webui",
                    "-p",
                    "8080:8080",
                    "open-webui",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            log("Open WebUI docker image zagnan na http://localhost:8080")
            time.sleep(8)
            healthcheck_http("http://localhost:8080/health")
            hashval = hash_integrity(dockerfile_path)
            log(f"INTEGRITETA: open-webui/Dockerfile | SHA256: {hashval}")
        except Exception as e:
            log(f"NAPAKA pri Open WebUI docker: {e}")
            if not INTERACTIVE:
                rollback()
                sys.exit(192)
    else:
        log(
            "OPOZORILO: Dockerfile za open-webui manjka po kloniranju ali je nepravilna struktura."
        )

    self_diagnostic()
    log("=== KAMELEON venv postavitev uspešno zaključena ===")
    preveri_in_konvertiraj_ggml_v_gguf()
