#!/usr/bin/env python3
"""Docker entrypoint: initialise the database then launch gunicorn."""
import os, sys

# Make sure the data directories exist
os.makedirs(os.environ.get("UPLOAD_BASE", "/DATA/bsh/picnic-images"), exist_ok=True)
db_path = os.environ.get("DB_PATH", "/DATA/bsh/picnic.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Bootstrap the schema
sys.path.insert(0, "/app")
from app import init_db
init_db()

print("Database initialised. Starting gunicorn …")
os.execlp(
    "gunicorn",
    "gunicorn",
    "--bind", "0.0.0.0:5000",
    "--workers", "4",
    "--timeout", "120",
    "--max-requests", "1000",
    "app:app",
)
