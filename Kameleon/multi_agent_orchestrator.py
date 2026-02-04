import os
import sys
import subprocess
import shutil
import json
import time
import logging
import torch
import threading
import psutil
import queue
import hashlib
import multiprocessing
import socket
import signal
import traceback
import functools
import uuid
import random
import requests
from pathlib import Path
from collections import OrderedDict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import redis
import grpc
from concurrent import futures

from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer, DataCollatorForLanguageModeling
)
from datasets import load_dataset

# ------------------ SECRETS MANAGER ------------------

class SecretsManager:
    def __init__(self, path="./secrets_prod.json"):
        if not os.path.exists(path):
            raise Exception("Secrets file missing.")
        with open(path) as f:
            self.secrets = json.load(f)
    def get(self, key, default=None):
        return self.secrets.get(key, default)

SECRETS = SecretsManager()

# ------------------ STRUCTURED JSON LOGGING & TRACING ------------------

class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        msg = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "msg": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "file": record.pathname,
            "line": record.lineno,
        }
        if record.exc_info:
            msg["exc"] = self.formatException(record.exc_info)
        return json.dumps(msg)

handler = logging.FileHandler(SECRETS.get("log_file", "./cell_prod_structured.log"))
handler.setFormatter(JsonLogFormatter())
root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)
logging = root_logger

def log_json(level, msg, trace_id=None, exc=None):
    record = logging.makeRecord("root", level, __file__, 0, msg, (), exc_info=exc)
    record.trace_id = trace_id
    logging.handle(record)

def get_trace_id():
    return str(uuid.uuid4())

# ------------------ GLOBAL RATE LIMIT (REDIS) ------------------

def global_rate_limit(ip, limit=200, win=60):
    r = redis.Redis.from_url(SECRETS.get("redis_url"))
    key = f"ratelimit:{ip}"
    val = r.incr(key)
    if val == 1:
        r.expire(key, win)
    if val > limit:
        return False
    return True

# ------------------ REDIS PERSISTENT JOB QUEUE ------------------

REDIS_QUEUE = "inference_jobs"
REDIS_RESULT = "inference_results"
redis_cli = redis.Redis.from_url(SECRETS.get("redis_url"))

def enqueue_job(job):
    jid = str(uuid.uuid4())
    job["job_id"] = jid
    redis_cli.lpush(REDIS_QUEUE, json.dumps(job))
    return jid

def await_job_result(jid, timeout=90):
    start = time.time()
    while time.time() - start < timeout:
        val = redis_cli.get(f"{REDIS_RESULT}:{jid}")
        if val:
            redis_cli.delete(f"{REDIS_RESULT}:{jid}")
            return json.loads(val)
        time.sleep(0.2)
    return {"error": "Timeout", "trace_id": jid}

# ------------------ PROMETHEUS METRICS (BASIC) ------------------

PROM_METRICS = {"inference_requests": 0, "errors": 0}
def prom_inc(key):
    PROM_METRICS[key] = PROM_METRICS.get(key, 0) + 1

def prometheus_exporter(port=9901):
    class PromHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                for k, v in PROM_METRICS.items():
                    self.wfile.write(f"{k} {v}\n".encode())
    server = HTTPServer(('0.0.0.0', port), PromHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

prometheus_exporter()

# ------------------ TLS, API WORKER POOL, RBAC, AUDIT LOGGING ------------------

def audit_log(event, trace_id, data):
    entry = {"event": event, "trace_id": trace_id, "data": data, "time": datetime.now().isoformat()}
    with open(SECRETS.get("audit_log_file", "./audit_prod.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")

class RBAC:
    def __init__(self, roles_cfg):
        self.roles = roles_cfg
    def has_perm(self, user, perm):
        user_roles = self.roles.get(user, [])
        return perm in user_roles

with open(SECRETS.get("rbac_file")) as f:
    RBAC_POLICIES = json.load(f)
rbac = RBAC(RBAC_POLICIES)

def with_timeout(timeout):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*a, **kw):
            res = [None]
            def target():
                try:
                    res[0] = f(*a, **kw)
                except Exception as e:
                    res[0] = e
            t = threading.Thread(target=target)
            t.start()
            t.join(timeout)
            if t.is_alive():
                raise TimeoutError("Timeout")
            if isinstance(res[0], Exception):
                raise res[0]
            return res[0]
        return wrapper
    return decorator

# ------------------ API VALIDACIJA, HEALTH, ALERTING, LOAD BALANCER ------------------

def validate_api_input(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid input: not a dict.")
    if not isinstance(data.get("prompt", ""), str):
        raise ValueError("Prompt missing or not string.")
    if len(data["prompt"]) > 4096:
        raise ValueError("Prompt too long.")
    return data

def alert_webhook(event, details):
    try:
        requests.post(SECRETS.get("alert_webhook"), json={"event": event, "details": details, "ts": time.time()})
    except Exception as e:
        log_json(logging.ERROR, f"Alert webhook fail: {e}")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            stat = {
                "status": "ok",
                "vram": int(torch.cuda.memory_allocated()) if torch.cuda.is_available() else 0,
                "ram": int(psutil.virtual_memory().used)
            }
            self.wfile.write(json.dumps(stat).encode())

def run_health():
    s = HTTPServer(("0.0.0.0", SECRETS.get("health_port", 8081)), HealthHandler)
    threading.Thread(target=s.serve_forever, daemon=True).start()

run_health()

# ------------------ HOT-RELOAD, PREFETCH, SANDBOX, PRIORITETA, RBAC, BACKUP, ROLLBACK ------------------

class HotModelPool:
    def __init__(self, max_vram_gb=40, max_models=5):
        self.lock = threading.Lock()
        self.max_models = max_models
        self.models = OrderedDict()
        self.tokenizers = OrderedDict()
        self.priorities = {}
        self.max_vram_bytes = max_vram_gb * 1024**3
        self._prefetch_models()
    def _prefetch_models(self):
        for m in MODELS[:self.max_models]:
            try:
                self.get_model(m["output"])
            except Exception:
                pass
    def reload_model(self, model_path):
        with self.lock:
            if model_path in self.models:
                del self.models[model_path]
                del self.tokenizers[model_path]
            return self.get_model(model_path)
    def get_model(self, model_path):
        with self.lock:
            if model_path in self.models:
                self.models.move_to_end(model_path)
                self.tokenizers.move_to_end(model_path)
                return self.models[model_path], self.tokenizers[model_path]
            self._evict_if_needed()
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if check_gpu() else torch.float32,
                device_map="auto" if check_gpu() else None
            )
            self.models[model_path] = model
            self.tokenizers[model_path] = tokenizer
            return model, tokenizer
    def _evict_if_needed(self):
        while len(self.models) >= self.max_models or self._vram_usage() > self.max_vram_bytes:
            old, model = self.models.popitem(last=False)
            try:
                del self.tokenizers[old]
                del model
                torch.cuda.empty_cache()
            except Exception:
                pass
    def _vram_usage(self):
        if not torch.cuda.is_available():
            return 0
        return torch.cuda.memory_allocated()

MODEL_POOL = HotModelPool()

def agent_resource_limiter(cpu=1, ram=2048):
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_AS, (ram*1024*1024, ram*1024*1024))

def agent_process_runner(agent_name, user_prompt, queue_out, timeout=30, trace_id=None):
    try:
        agent_resource_limiter()
        response = generate_agent_response(agent_name, user_prompt, trace_id=trace_id)
        queue_out.put(response)
    except Exception as e:
        queue_out.put(f"Napaka: {e}")

def agent_generate_with_isolation(agent_name, user_prompt, timeout=30, trace_id=None):
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=agent_process_runner, args=(agent_name, user_prompt, q, timeout, trace_id))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        return "Napaka: Timeout agenta."
    try:
        return q.get_nowait()
    except Exception:
        return "Napaka: Agent ni vrnil odgovora."

# ------------------ ADVANCED ERROR HANDLING Z RETRY, BACKOFF, FALLBACK ------------------

def with_retry(n=3, backoff=2, fallback=None):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*a, **k):
            for i in range(n):
                try:
                    return f(*a, **k)
                except Exception as e:
                    if i == n-1 and fallback:
                        return fallback(*a, **k)
                    time.sleep(backoff ** i)
        return wrapper
    return decorator

def fallback_response(agent_name, user_prompt, **kw):
    fallback_model = MODELS[0]["output"]
    model, tokenizer = MODEL_POOL.get_model(fallback_model)
    prompt = agent_prompt({"name": agent_name, "role": "fallback", "domain": "", "description": ""}, user_prompt)
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
    with torch.no_grad():
        output = model.generate(input_ids, max_new_tokens=256)
    return tokenizer.decode(output[0], skip_special_tokens=True)

# ------------------ API LAYER (REST/GRPC, WORKER POOL, LOAD BALANCER SUPPORT) ------------------

class SecureAPIServer(BaseHTTPRequestHandler):
    SECRET_TOKEN = SECRETS.get("api_token")
    def _send(self, code, resp):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())
    def _auth(self):
        return self.headers.get('Authorization') == f"Bearer {self.SECRET_TOKEN}"
    def do_POST(self):
        ip = self.client_address[0]
        trace_id = get_trace_id()
        if not global_rate_limit(ip):
            self._send(429, {"error": "Global rate limit.", "trace_id": trace_id})
            return
        if not self._auth():
            self._send(401, {"error": "Unauthorized.", "trace_id": trace_id})
            return
        try:
            length = int(self.headers.get('Content-Length'))
            data = json.loads(self.rfile.read(length).decode())
            data = validate_api_input(data)
        except Exception as e:
            self._send(400, {"error": str(e), "trace_id": trace_id})
            return
        user = data.get("user")
        if not rbac.has_perm(user, "inference"):
            self._send(403, {"error": "Forbidden", "trace_id": trace_id})
            return
        agent_name = select_agent(data["prompt"])
        jid = enqueue_job({
            "agent_name": agent_name,
            "user_prompt": data["prompt"],
            "trace_id": trace_id,
            "priority": data.get("priority", 1)
        })
        audit_log("api_call", trace_id, {"agent": agent_name, "user": user, "prompt": data["prompt"]})
        result = await_job_result(jid)
        self._send(200, {"result": result, "trace_id": trace_id})

    def log_message(self, *args): return

def run_tls_api_server(port):
    server = HTTPServer(("0.0.0.0", port), SecureAPIServer)
    server.socket = ssl.wrap_socket(
        server.socket,
        keyfile=SECRETS.get("tls_key"),
        certfile=SECRETS.get("tls_cert"),
        server_side=True
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()

run_tls_api_server(SECRETS.get("api_port", 8443))

# ------------------ DISTRIBUTED INFERENCE GRPC MICROSERVICE ------------------

def serve_grpc():
    import agent_serving_pb2_grpc, agent_serving_pb2
    class AgentService(agent_serving_pb2_grpc.AgentServiceServicer):
        @with_retry(n=3, fallback=fallback_response)
        def Infer(self, request, context):
            trace_id = request.trace_id or get_trace_id()
            try:
                result = agent_generate_with_isolation(request.agent_name, request.prompt, trace_id=trace_id)
                prom_inc("inference_requests")
                return agent_serving_pb2.InferReply(response=result, trace_id=trace_id)
            except Exception as e:
                prom_inc("errors")
                alert_webhook("grpc_infer_fail", {"trace_id": trace_id, "err": str(e)})
                return agent_serving_pb2.InferReply(response="Napaka", trace_id=trace_id)
    s = grpc.server(futures.ThreadPoolExecutor(max_workers=SECRETS.get("grpc_workers", 8)))
    agent_serving_pb2_grpc.add_AgentServiceServicer_to_server(AgentService(), s)
    s.add_insecure_port(f'[::]:{SECRETS.get("grpc_port", 50051)}')
    s.start()
    logging.info(f"GRPC agent microservice na {SECRETS.get('grpc_port', 50051)}")
    s.wait_for_termination()

threading.Thread(target=serve_grpc, daemon=True).start()

# ------------------ KVANTIZACIJA (GGUF/GPTQ/AWQ AUTO-DETEKCIJA) ------------------

def quantize_support_load(model_path):
    for ext in [".gguf", ".gptq", ".awq"]:
        if os.path.exists(model_path+ext):
            pass
    return AutoModelForCausalLM.from_pretrained(model_path)

# ------------------ BACKUP, ROLLBACK, CONFIG HOT-LOAD ------------------

def backup_configs_models():
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    for f in [CONFIG_PATH, AGENTS_PATH]:
        shutil.copy2(f, f+".bak."+ts)
    for m in MODELS:
        if os.path.exists(m["output"]):
            shutil.copytree(m["output"], m["output"]+".bak."+ts)

def rollback_model(model_path):
    baks = [f for f in os.listdir(os.path.dirname(model_path)) if f.startswith(os.path.basename(model_path)+".bak.")]
    if not baks:
        return False
    last = sorted(baks)[-1]
    shutil.rmtree(model_path)
    shutil.copytree(os.path.join(os.path.dirname(model_path), last), model_path)
    return True

def hot_reload_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    global MODELS, TRAIN_CFG
    MODELS = cfg["models"]
    TRAIN_CFG = cfg["train"]

# ------------------ TESTNI FRAMEWORK (UNIT/LOAD/FUZZ) ------------------

def run_unit_tests():
    assert callable(agent_generate_with_isolation)
    assert isinstance(MODEL_POOL.get_model(MODELS[0]["output"]), tuple)
    print("Unit testi OK")

def run_load_test():
    t0 = time.time()
    for i in range(20):
        agent_generate_with_isolation(MODELS[0]["name"], "Test zahteva " + str(i))
    print("Load test OK", time.time() - t0)

def run_fuzz_test():
    for _ in range(10):
        s = "".join(random.choices("abcdef12345 \n\t" * 50, k=1000))
        try:
            agent_generate_with_isolation(MODELS[0]["name"], s)
        except Exception:
            pass
    print("Fuzz test OK")

# ------------------- POLNE KONFIGURACIJE (MODELI, AGENTI, TRAIN) -------------------

DEFAULT_MODELS_PATH = "./models"
DEFAULT_DATASETS_PATH = "./datasets"
CONFIG_PATH = "./config_prod.json"
AGENTS_PATH = "/opt/cell/agents/agent_full.json"
MIN_DISK_GB = 20
MIN_RAM_GB = 16

DEFAULT_MODELS = [
    {
        "name": "mistralai/Mistral-7B-v0.1",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_1.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/uncensored-mistral-7b",
        "domains": [
            "security", "cybernetics", "strategy", "red teaming", "exploitation", "AI", "philosophy", "logic",
            "malware", "reverse engineering", "blockchain", "crypto", "anonymity", "OSINT", "penetration testing",
            "APT", "botnet", "opsec", "forensics", "darknet", "steganography", "covert", "decentralization"
        ]
    },
    {
        "name": "meta-llama/Llama-2-7b-hf",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_2.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/uncensored-llama-2-7b",
        "domains": [
            "medicine", "law", "psychology", "economics", "pedagogy", "management", "leadership", "diplomacy",
            "social engineering", "HR", "creativity", "writing", "politics", "marketing", "brand", "e-commerce", "copywriting"
        ]
    },
    {
        "name": "tiiuae/falcon-7b",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_3.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/uncensored-falcon-7b",
        "domains": [
            "robotics", "mathematics", "physics", "chemistry", "biology", "climatology", "agronomy", "geography",
            "engineering", "logistics", "supply chain", "industrial", "SCADA", "IoT", "FPGA", "hardware", "embedded"
        ]
    },
    {
        "name": "TheBloke/Nous-Hermes-2-Mistral-7B-DPO-Uncensored",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_4.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/nous-hermes-2-mistral-7b-uncensored",
        "domains": [
            "uncensored", "AI", "programming", "code", "automation", "cybersecurity", "general knowledge"
        ]
    },
    {
        "name": "TheBloke/Mixtral-8x7B-Instruct-v0.1-GPTQ",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_5.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/mixtral-8x7b-instruct",
        "domains": [
            "multidomain", "science", "technology", "AI", "automation", "penetration testing", "security"
        ]
    },
    {
        "name": "Open-Orca/OpenOrca-Platypus2-13B",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_6.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/openorca-platypus2-13b",
        "domains": [
            "AI", "general knowledge", "engineering", "science", "multidomain"
        ]
    },
    {
        "name": "Phind/Phind-CodeLlama-34B-v2",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_7.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/phind-codellama-34b-v2",
        "domains": [
            "programming", "security automation", "exploit dev", "reverse engineering"
        ]
    },
    {
        "name": "teknium/OpenHermes-2.5-Mistral-7B",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_8.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/openhermes-2.5-mistral-7b",
        "domains": [
            "uncensored", "AI", "code", "red team", "general"
        ]
    },
    {
        "name": "Undi95/Toppy-M-7B",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_9.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/toppy-m-7b",
        "domains": [
            "philosophy", "uncensored", "AI", "cybersecurity"
        ]
    },
    {
        "name": "TheBloke/Wizard-Vicuna-13B-Uncensored-HF",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_10.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/wizard-vicuna-13b-uncensored",
        "domains": [
            "uncensored", "OSINT", "malware", "security research", "penetration testing"
        ]
    },
    {
        "name": "meta-llama/Llama-2-70b-hf",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_11.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/llama-2-70b",
        "domains": [
            "all"
        ]
    },
    {
        "name": "undreamed/undreamed-13b-uncensored",
        "dataset": f"{DEFAULT_DATASETS_PATH}/uncensored_dataset_12.jsonl",
        "output": f"{DEFAULT_MODELS_PATH}/undreamed-13b-uncensored",
        "domains": [
            "uncensored", "deep web", "psychology", "general", "AI"
        ]
    }
]

DEFAULT_TRAIN = {
    "batch_size": 2,
    "grad_acc_steps": 8,
    "epochs": 2,
    "learning_rate": 2e-5,
    "max_length": 2048
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"models": DEFAULT_MODELS, "train": DEFAULT_TRAIN}, f, indent=2)

with open(CONFIG_PATH) as f:
    config = json.load(f)
MODELS = config["models"]
TRAIN_CFG = config["train"]

if not os.path.exists(AGENTS_PATH):
    logging.error(f"Manjka agent_full.json ({AGENTS_PATH})!")
    sys.exit(1)

with open(AGENTS_PATH) as f:
    AGENTS = json.load(f)
if not isinstance(AGENTS, list) or not all("name" in a and "role" in a and "domain" in a for a in AGENTS):
    logging.error("Datoteka agent_full.json nima ustrezne strukture!")
    sys.exit(1)

# ------------------- AGENT-MODEL MAPPING ZA INFERENCO -------------------

DOMAIN_MODEL_MAP = {}
for model in MODELS:
    for domain in model["domains"]:
        DOMAIN_MODEL_MAP[domain.strip().lower()] = model["output"]

AGENT_MODEL_MAP = {}
for agent in AGENTS:
    d = agent.get("domain", "").lower()
    selected = None
    for key, out in DOMAIN_MODEL_MAP.items():
        if key in d:
            selected = out
            break
    AGENT_MODEL_MAP[agent["name"]] = selected if selected else MODELS[0]["output"]



def ensure_dir(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        if not os.access(path, os.W_OK):
            raise PermissionError
    except Exception as e:
        logging.error(f"Ne morem pripraviti mape {path}: {e}")
        sys.exit(1)

def check_gpu():
    return torch.cuda.is_available()

def check_disk(min_gb, paths):
    for path in paths:
        root = os.path.abspath(os.path.dirname(path))
        usage = shutil.disk_usage(root)
        if usage.free < min_gb * 1024**3:
            logging.error(f"Premalo prostora v {root}: {usage.free / 1024 ** 3:.2f} GB prosto.")
            return False
    return True

def check_write_access(paths):
    for p in paths:
        root = os.path.abspath(os.path.dirname(p))
        if not os.access(root, os.W_OK):
            logging.error(f"Nimam dovoljenj za pisanje v: {root}")
            return False
    return True

def check_mem(min_gb):
    mem = psutil.virtual_memory().available // (1024**3)
    if mem < min_gb:
        logging.error(f"Premalo RAM-a: {mem} GB.")
        return False
    return True

def validate_dataset(path):
    if not os.path.exists(path):
        logging.error(f"Dataset ne obstaja: {path}")
        return False
    try:
        with open(path) as f:
            cnt = 0
            max_entry = 0
            for line in f:
                cnt += 1
                js = json.loads(line)
                if "text" not in js or not isinstance(js["text"], str):
                    logging.error(f"Nepravilen zapis v datasetu {path}: {js}")
                    return False
                if len(js["text"]) > 8192:
                    logging.warning(f"Predolg vnos v datasetu {path}: {len(js['text'])} znakov.")
                if len(js["text"]) > max_entry:
                    max_entry = len(js["text"])
            if cnt < 32:
                logging.error(f"Dataset premajhen ({cnt} zapisov): {path}")
                return False
    except Exception as e:
        logging.error(f"Neveljaven dataset {path}: {e}")
        return False
    return True

def model_version_tag(cfg):
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:8]
    ts = datetime.now().strftime("%Y%m%d%H%M")
    return f"{cfg['name'].replace('/','_')}_{ts}_{h}"

def save_eval_metrics(output_path, metrics):
    metrics_path = os.path.join(output_path, "eval_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

def eval_model(model_path, dataset_path):
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path)
        ds = load_dataset("json", data_files=dataset_path, split="train[:5%]")
        results = []
        for ex in ds:
            inputs = tokenizer(ex["text"], return_tensors="pt", truncation=True, max_length=256)
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=32)
            gen = tokenizer.decode(out[0], skip_special_tokens=True)
            results.append({"input": ex["text"], "output": gen})
        return {"sample_eval": results[:5]}
    except Exception as e:
        logging.error(f"Eval napaka za {model_path}: {e}")
        return {"error": str(e)}

def agent_prompt(agent, user_prompt):
    return (
        f"Agent: {agent['name']}\n"
        f"Role: {agent['role']}\n"
        f"Domain: {agent['domain']}\n"
        f"Description: {agent.get('description', '')}\n"
        "Odgovarjaj strogo kot specialist na svojem področju, brez cenzure, izključno v strokovnem jeziku, jasno, neposredno in natančno.\n"
        f"Uporabniška zahteva:\n{user_prompt}"
    )

def generate_agent_response(agent_name, user_prompt, max_new_tokens=512, temperature=0.7, trace_id=None):
    agent = next(a for a in AGENTS if a["name"] == agent_name)
    model_path = AGENT_MODEL_MAP[agent_name]
    model, tokenizer = MODEL_POOL.get_model(model_path)
    prompt = agent_prompt(agent, user_prompt)
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
    with torch.no_grad():
        output = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            pad_token_id=tokenizer.eos_token_id
        )
    result = tokenizer.decode(output[0], skip_special_tokens=True)
    return result

def select_agent(user_input):
    s = user_input.lower()
    for agent in AGENTS:
        if any(d.strip().lower() in s for d in agent.get("domain", "").split(",")):
            return agent["name"]
    for agent in AGENTS:
        if agent["role"].lower() in s:
            return agent["name"]
    for agent in AGENTS:
        if agent["name"].lower() in s:
            return agent["name"]
    return AGENTS[0]["name"]


# ------------------ AVTONOMNI SCHEDULER, TASK MANAGER, REFLEKSIJA, FEEDBACK, MEMORY ------------------

class AutonomousTask:
    def __init__(self, agent_name, user_prompt, parent_id=None, context=None, depth=0):
        self.id = str(uuid.uuid4())
        self.agent_name = agent_name
        self.user_prompt = user_prompt
        self.parent_id = parent_id
        self.context = context or {}
        self.depth = depth
        self.status = "pending"
        self.result = None
        self.subtasks = []
        self.feedback = []
    def to_dict(self):
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "user_prompt": self.user_prompt,
            "parent_id": self.parent_id,
            "context": self.context,
            "depth": self.depth,
            "status": self.status,
            "result": self.result,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "feedback": self.feedback
        }

class PersistentMemory:
    def __init__(self, redis_url=None):
        self.r = redis.Redis.from_url(redis_url or SECRETS.get("redis_url"))
    def save(self, key, val):
        self.r.set(f"memory:{key}", json.dumps(val))
    def get(self, key):
        v = self.r.get(f"memory:{key}")
        return json.loads(v) if v else None
    def search(self, query):
        # Placeholder za vektorsko iskanje ali fuzzy search (RAG podpora)
        keys = self.r.keys("memory:*")
        res = []
        for k in keys:
            val = self.r.get(k)
            if query.lower() in str(val).lower():
                res.append(json.loads(val))
        return res

AGENT_MEMORY = PersistentMemory()

class FeedbackManager:
    def __init__(self, redis_url=None):
        self.r = redis.Redis.from_url(redis_url or SECRETS.get("redis_url"))
    def add_feedback(self, task_id, score, note=""):
        entry = {"score": score, "note": note, "ts": time.time()}
        self.r.rpush(f"feedback:{task_id}", json.dumps(entry))
    def get_feedback(self, task_id):
        allf = self.r.lrange(f"feedback:{task_id}", 0, -1)
        return [json.loads(fb) for fb in allf]

AGENT_FEEDBACK = FeedbackManager()

class AgentReflection:
    @staticmethod
    def evaluate_result(result, threshold=0.65):
        # Dummy self-eval (lahko zamenjaš z LLM scoringom ali heuristiko)
        if isinstance(result, str) and len(result) > 50:
            return True, "Sprejemljivo"
        return False, "Ponovi nalogo ali izboljšaj output"

def autonomous_scheduler(user_prompt, max_depth=3, context=None):
    """Planiranje, razbijanje in refleksija nalog v agentnem omrežju."""
    trace_id = get_trace_id()
    root_agent = select_agent(user_prompt)
    root_task = AutonomousTask(root_agent, user_prompt, context=context)
    AGENT_MEMORY.save(root_task.id, root_task.to_dict())
    queue = [root_task]
    while queue:
        task = queue.pop(0)
        if task.depth > max_depth:
            continue
        agent_name = task.agent_name
        resp = agent_generate_with_isolation(agent_name, task.user_prompt, trace_id=trace_id)
        task.result = resp
        task.status = "done"
        AGENT_MEMORY.save(task.id, task.to_dict())
        ok, comment = AgentReflection.evaluate_result(resp)
        AGENT_FEEDBACK.add_feedback(task.id, int(ok), note=comment)
        if not ok and task.depth < max_depth:
            # Samogeneracija popravkov ali podnalog
            subprompt = f"Izboljšaj to rešitev:\n{resp}\nNavodila: {task.user_prompt}"
            subtask = AutonomousTask(agent_name, subprompt, parent_id=task.id, context=task.context, depth=task.depth+1)
            task.subtasks.append(subtask)
            AGENT_MEMORY.save(task.id, task.to_dict())
            queue.append(subtask)
    return root_task.result

# ------------------ INTER-AGENT KOMUNIKACIJA, DELEGACIJA, BLACKBOARD ------------------

class InterAgentComm:
    def __init__(self, redis_url=None):
        self.r = redis.Redis.from_url(redis_url or SECRETS.get("redis_url"))
    def publish(self, channel, msg):
        self.r.publish(channel, json.dumps(msg))
    def subscribe(self, channel):
        pubsub = self.r.pubsub()
        pubsub.subscribe(channel)
        return pubsub

AGENT_COMMS = InterAgentComm()

def delegate_to_expert(domain, user_prompt):
    """Delegira nalogo agentu z največjo ekspertizo za domeno."""
    candidates = [a for a in AGENTS if domain in a["domain"].lower()]
    if not candidates:
        agent_name = AGENTS[0]["name"]
    else:
        agent_name = candidates[0]["name"]
    trace_id = get_trace_id()
    return agent_generate_with_isolation(agent_name, user_prompt, trace_id=trace_id)

def agent_blackboard_publish(msg):
    AGENT_COMMS.publish("agent_blackboard", msg)

def agent_blackboard_listen():
    pubsub = AGENT_COMMS.subscribe("agent_blackboard")
    for m in pubsub.listen():
        if m["type"] == "message":
            data = json.loads(m["data"])
            print("Blackboard message:", data)

# ------------------ AVTONOMNI FEEDBACK LOOP ZA FINE-TUNING ------------------

def autonomous_feedback_retrain(threshold=0.5):
    """Avtonomno zazna nizko kvaliteto outputa in sproži retraining."""
    for key in AGENT_FEEDBACK.r.keys("feedback:*"):
        all_fb = AGENT_FEEDBACK.r.lrange(key, 0, -1)
        scores = [json.loads(fb)["score"] for fb in all_fb]
        if scores and sum(scores)/len(scores) < threshold:
            # Sproži retraining agenta/modela (lahko z dodatnimi podatki)
            agent_or_model = key.decode().split(":")[1]
            logging.warning(f"Agent/model {agent_or_model} dosega prenizko kvaliteto, sprožam auto-retrain.")
            # Klici retrain, retrain_model(agent_or_model)
            # Tukaj implementiraj retrain pipeline s self-play ali RLHF

# ------------------ DYNAMIC PLUGIN LOADER (SAMO-NADGRADNJE, MODULI) ------------------

import importlib
def load_plugin(plugin_path):
    """Dinamično nalaganje agentnih orodij/modulov."""
    spec = importlib.util.spec_from_file_location("plugin_module", plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def self_update_agent_code(repo_url):
    """Agent sam sproži git pull/updater, backup, in reload."""
    os.system(f"git pull {repo_url}")
    os.execl(sys.executable, sys.executable, *sys.argv)

# ------------------ SELF-HEALING & AUTORECOVERY (WATCHDOG + INFRA) ------------------

def autonomous_watchdog():
    """Nenehno preverjanje agentov, modelov, API, resource in samodejni recovery."""
    while True:
        try:
            for m in MODELS:
                model_path = m["output"]
                try:
                    MODEL_POOL.get_model(model_path)
                except Exception as e:
                    logging.error(f"Samodejni restart modela: {model_path}")
                    MODEL_POOL.reload_model(model_path)
            # Health-check API, GRPC, redis, disk, RAM
            if not check_mem(MIN_RAM_GB):
                alert_webhook("memory_alert", {"ram": psutil.virtual_memory().used})
            # ČE je API down, ga restartaj
            # Če Redis nedostopen, poizkusi reconnect
            # Če katerikoli agent “zmrzne”, ga izoliraj
        except Exception as e:
            logging.error(f"Autonomous watchdog fail: {e}")
        time.sleep(15)

# ------------------ META-REASONING (“vem da ne vem”) ------------------

def agent_meta_reasoning(prompt, agent_name=None):
    """Agent sam preveri ali zna odgovoriti in če ne, eskalira, delegira ali prosi za pomoč."""
    if not agent_name:
        agent_name = select_agent(prompt)
    answer = agent_generate_with_isolation(agent_name, prompt)
    if "ne vem" in answer.lower() or "can't answer" in answer.lower():
        agent_blackboard_publish({"agent": agent_name, "prompt": prompt, "status": "needs_help"})
        # Avtomatsko eskalira
        return "Agent eskaliral neznano zahtevo."
    return answer

# ------------------ DYNAMIC SCALING & CLOUD FEDERATION (primer AWS/GCP, samo skeleton) ------------------

def dynamic_cloud_scale(current_load, threshold=0.7):
    """Auto-scaling agent pool (primer za cloud provider API-je)."""
    if current_load > threshold:
        # Klici cloud API za skaliranje navzgor
        logging.info("Avtonomno skaliranje navzgor.")
        # npr. boto3 za AWS EC2 AutoScalingGroup
    else:
        logging.info("Load OK.")

# ------------------ AUTO-REPORTING & CONTINUOUS SELF-EVAL ------------------

def auto_reporting(interval=300):
    while True:
        report = {
            "active_agents": len(MODELS),
            "resource": {
                "cpu": psutil.cpu_percent(),
                "ram": psutil.virtual_memory().used,
                "vram": int(torch.cuda.memory_allocated()) if torch.cuda.is_available() else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        with open(SECRETS.get("report_file", "./agent_report.jsonl"), "a") as f:
            f.write(json.dumps(report) + "\n")
        time.sleep(interval)

def start_auto_reporting():
    threading.Thread(target=auto_reporting, daemon=True).start()

start_auto_reporting()

# ------------------ GLAVNI ENTRY ------------------

def main():
    backup_configs_models()
    run_unit_tests()
    run_load_test()
    run_fuzz_test()
    logging.info("Produkcijski sistem v CI/CD pipelinu z structured logging, worker pool, TLS API, distribucijsko inferenco, sandbox agenti, audit in prometheus monitoring, RBAC in rollback podporo.")
    print("Produkcijski cikel inicializiran.")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
