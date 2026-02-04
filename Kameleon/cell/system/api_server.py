#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from functools import wraps

from flask import Flask, jsonify, request
from kameleon import Kameleon
from loguru import logger

app = Flask(__name__)
kameleon = Kameleon()

# 🔐 API ključ za dostop
API_KEY = "tajni-kljuc"


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if key != API_KEY:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated


@app.route("/chat", methods=["POST"])
@require_api_key
def chat():
    try:
        data = request.get_json(force=True)

        user_msg = data.get("messages")
        if not isinstance(user_msg, list) or not user_msg:
            return jsonify({"error": "messages must be a non-empty list"}), 400

        last = user_msg[-1]
        if not isinstance(last, dict) or last.get("role") != "user":
            return jsonify({"error": "last message must be from user"}), 400

        query = str(last.get("content", "")).strip()
        if not query:
            return jsonify({"error": "empty user query"}), 400

        response = str(kameleon.run(query)).strip()

        return (
            jsonify(
                {
                    "id": "kameleon-response",
                    "object": "chat.completion",
                    "model": "kameleon",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": response},
                            "finish_reason": "stop",
                        }
                    ],
                }
            ),
            200,
            {"Content-Type": "application/json"},
        )

    except Exception as e:
        logger.error(f"API napaka: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK"}), 200


if __name__ == "__main__":
    logger.info("KAMELEON API: Zagon na http://127.0.0.1:5005")
    app.run(host="0.0.0.0", port=5005, threaded=True)
