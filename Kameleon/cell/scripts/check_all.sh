#!/bin/bash

export PYTHONPATH=.

echo "[1/6] Format (black)..."
black .

echo "[2/6] Lint (ruff)..."
ruff check .

echo "[3/6] Type check (mypy)..."
mypy system/

echo "[4/6] Run tests (pytest)..."
pytest tests/

echo "[5/6] Varnostna analiza (bandit)..."
bandit -r system/ -ll

echo "[6/6] Odvisnosti (safety)..."
safety scan

