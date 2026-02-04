# plugins/offline_translation_daemon.py

import json
from datetime import datetime
from pathlib import Path
from transformers import MarianMTModel, MarianTokenizer

TRANSLATION_LOG = "logs/offline_translation_log.json"
SUPPORTED_LANGS = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "sl": "slv",
    "it": "ita",
    "ru": "rus"
}
MODEL_BASE_PATH = "models/translation/"
CACHE = {}

class OfflineTranslationDaemon:
    def __init__(self):
        self.log_path = Path(TRANSLATION_LOG)
        self.ensure_log_exists()

    def ensure_log_exists(self):
        if not self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_model(self, source_lang, target_lang):
        key = f"{source_lang}_{target_lang}"
        if key in CACHE:
            return CACHE[key]

        src_code = SUPPORTED_LANGS.get(source_lang)
        tgt_code = SUPPORTED_LANGS.get(target_lang)

        if not src_code or not tgt_code:
            raise ValueError(f"Nepodprt jezik: {source_lang} → {target_lang}")

        model_name = f"Helsinki-NLP/opus-mt-{src_code}-{tgt_code}"
        tokenizer = MarianTokenizer.from_pretrained(model_name, cache_dir=MODEL_BASE_PATH)
        model = MarianMTModel.from_pretrained(model_name, cache_dir=MODEL_BASE_PATH)
        CACHE[key] = (tokenizer, model)
        return tokenizer, model

    def translate(self, text, source_lang, target_lang):
        tokenizer, model = self.get_model(source_lang, target_lang)
        inputs = tokenizer([text], return_tensors="pt", padding=True)
        translated = model.generate(**inputs)
        result = tokenizer.batch_decode(translated, skip_special_tokens=True)[0]
        self.log_translation(source_lang, target_lang, text, result)
        return result

    def log_translation(self, source_lang, target_lang, original, translated):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "from": source_lang,
            "to": target_lang,
            "input": original,
            "output": translated
        }
        with open(self.log_path, "r+", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()

daemon_instance = OfflineTranslationDaemon()

def hook(text, source_lang="sl", target_lang="en"):
    return daemon_instance.translate(text, source_lang, target_lang)
