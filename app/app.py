"""
Bull Stone House Annual Picnic - Photo Uploader
159th Annual William Bull & Sarah Wells Family Picnic
"""

import os
import re
import json
import uuid
import hashlib
import sqlite3
import mimetypes
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, request, render_template, redirect, url_for,
    session, flash, jsonify, send_from_directory, abort, g
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bsh-picnic-2025-secret-key-change-me")

# Event code that attendees enter (shared codeword)
EVENT_CODE = os.environ.get("EVENT_CODE", "WELLSBULL159")

# Admin password (hashed at startup)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "picnicadmin2025")

# Upload storage
UPLOAD_BASE = os.environ.get("UPLOAD_BASE", "/DATA/bsh/picnic-images")
DB_PATH = os.environ.get("DB_PATH", "/DATA/bsh/picnic.db")

# Allowed media types
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif',
    'mp4', 'mov', 'avi', 'mkv', 'm4v', 'wmv', 'webm'
}
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'm4v', 'wmv', 'webm'}

MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(UPLOAD_BASE, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS stats (
            id          INTEGER PRIMARY KEY,
            key         TEXT UNIQUE NOT NULL,
            value       INTEGER DEFAULT 0
        );

        INSERT OR IGNORE INTO stats (key, value) VALUES
            ('landing_views', 0),
            ('code_logins', 0),
            ('total_uploads', 0);

        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT NOT NULL,
            last_name   TEXT NOT NULL,
            slug        TEXT UNIQUE NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            upload_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS uploads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            filename    TEXT NOT NULL,
            original_name TEXT,
            file_type   TEXT NOT NULL,       -- 'image' or 'video'
            title       TEXT,
            caption     TEXT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            file_size   INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS admin_sessions (
            token       TEXT PRIMARY KEY,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db.commit()
    db.close()


def increment_stat(key, amount=1):
    db = get_db()
    db.execute("UPDATE stats SET value = value + ? WHERE key = ?", (amount, key))
    db.commit()


def get_stat(key):
    db = get_db()
    row = db.execute("SELECT value FROM stats WHERE key = ?", (key,)).fetchone()
    return row['value'] if row else 0


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'unknown'


def make_user_slug(first, last):
    """Create a filesystem-safe slug from a user's name."""
    raw = f"{first.strip()}_{last.strip()}"
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', raw).lower()
    return slug


def get_or_create_user(first_name, last_name):
    db = get_db()
    slug = make_user_slug(first_name, last_name)
    row = db.execute("SELECT * FROM users WHERE slug = ?", (slug,)).fetchone()
    if row:
        return dict(row)
    db.execute(
        "INSERT INTO users (first_name, last_name, slug) VALUES (?, ?, ?)",
        (first_name.strip(), last_name.strip(), slug)
    )
    db.commit()
    row = db.execute("SELECT * FROM users WHERE slug = ?", (slug,)).fetchone()
    return dict(row)


def user_upload_dir(slug):
    path = os.path.join(UPLOAD_BASE, slug)
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    increment_stat('landing_views')
    return render_template('index.html')


@app.route('/enter', methods=['POST'])
def enter_code():
    code = request.form.get('event_code', '').strip().upper()
    if code != EVENT_CODE.upper():
        flash('That code is incorrect. Please check your invitation and try again.', 'error')
        return redirect(url_for('index'))
    increment_stat('code_logins')
    session['code_verified'] = True
    return redirect(url_for('register'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not session.get('code_verified'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        first = request.form.get('first_name', '').strip()
        last = request.form.get('last_name', '').strip()
        if not first or not last:
            flash('Please enter both your first and last name.', 'error')
            return render_template('register.html')

        user = get_or_create_user(first, last)
        session['user_id'] = user['id']
        session['user_slug'] = user['slug']
        session['user_name'] = f"{user['first_name']} {user['last_name']}"
        return redirect(url_for('upload'))

    return render_template('register.html')


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('Please select at least one file to upload.', 'error')
            return redirect(url_for('upload'))

        db = get_db()
        slug = session['user_slug']
        upload_dir = user_upload_dir(slug)
        saved = 0

        for f in files:
            if f.filename == '':
                continue
            if not allowed_file(f.filename):
                flash(f'"{f.filename}" is not a supported file type.', 'error')
                continue

            original = secure_filename(f.filename)
            ext = original.rsplit('.', 1)[1].lower() if '.' in original else ''
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            dest = os.path.join(upload_dir, unique_name)
            f.save(dest)
            size = os.path.getsize(dest)
            ftype = file_type(original)

            db.execute(
                """INSERT INTO uploads
                   (user_id, filename, original_name, file_type, file_size)
                   VALUES (?, ?, ?, ?, ?)""",
                (session['user_id'], unique_name, original, ftype, size)
            )
            saved += 1

        if saved:
            db.execute(
                "UPDATE users SET upload_count = upload_count + ? WHERE id = ?",
                (saved, session['user_id'])
            )
            increment_stat('total_uploads', saved)
            db.commit()
            flash(f'Successfully uploaded {saved} file{"s" if saved != 1 else ""}!', 'success')

        return redirect(url_for('gallery'))

    return render_template('upload.html', user_name=session.get('user_name'))


@app.route('/gallery')
@login_required
def gallery():
    db = get_db()
    uploads = db.execute(
        """SELECT * FROM uploads WHERE user_id = ? ORDER BY uploaded_at DESC""",
        (session['user_id'],)
    ).fetchall()
    return render_template(
        'gallery.html',
        uploads=[dict(u) for u in uploads],
        user_name=session.get('user_name'),
        user_slug=session.get('user_slug')
    )


@app.route('/update-media', methods=['POST'])
@login_required
def update_media():
    data = request.get_json()
    upload_id = data.get('id')
    title = data.get('title', '').strip()
    caption = data.get('caption', '').strip()

    db = get_db()
    row = db.execute(
        "SELECT * FROM uploads WHERE id = ? AND user_id = ?",
        (upload_id, session['user_id'])
    ).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Not found'}), 404

    db.execute(
        "UPDATE uploads SET title = ?, caption = ? WHERE id = ?",
        (title or None, caption or None, upload_id)
    )
    db.commit()
    return jsonify({'ok': True})


@app.route('/delete-media', methods=['POST'])
@login_required
def delete_media():
    data = request.get_json()
    upload_id = data.get('id')

    db = get_db()
    row = db.execute(
        "SELECT * FROM uploads WHERE id = ? AND user_id = ?",
        (upload_id, session['user_id'])
    ).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Not found'}), 404

    # Remove file
    slug = session['user_slug']
    filepath = os.path.join(UPLOAD_BASE, slug, row['filename'])
    try:
        os.remove(filepath)
    except OSError:
        pass

    db.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
    db.execute(
        "UPDATE users SET upload_count = MAX(0, upload_count - 1) WHERE id = ?",
        (session['user_id'],)
    )
    increment_stat('total_uploads', -1)
    db.commit()
    return jsonify({'ok': True})


@app.route('/media/<slug>/<filename>')
@login_required
def serve_media(slug, filename):
    # Users can only view their own media (admins bypass via admin routes)
    if slug != session.get('user_slug'):
        abort(403)
    upload_dir = os.path.join(UPLOAD_BASE, slug)
    return send_from_directory(upload_dir, filename)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if pw == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Incorrect password.', 'error')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        row['key']: row['value']
        for row in db.execute("SELECT key, value FROM stats").fetchall()
    }
    users = db.execute(
        "SELECT * FROM users ORDER BY upload_count DESC, created_at ASC"
    ).fetchall()
    recent_uploads = db.execute(
        """SELECT u.*, us.first_name, us.last_name, us.slug
           FROM uploads u JOIN users us ON u.user_id = us.id
           ORDER BY u.uploaded_at DESC LIMIT 20"""
    ).fetchall()
    return render_template(
        'admin_dashboard.html',
        stats=stats,
        users=[dict(u) for u in users],
        recent_uploads=[dict(r) for r in recent_uploads]
    )


@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        abort(404)
    uploads = db.execute(
        "SELECT * FROM uploads WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    ).fetchall()
    return render_template(
        'admin_user.html',
        user=dict(user),
        uploads=[dict(u) for u in uploads]
    )


@app.route('/admin/media/<slug>/<filename>')
@admin_required
def admin_serve_media(slug, filename):
    upload_dir = os.path.join(UPLOAD_BASE, slug)
    return send_from_directory(upload_dir, filename)


@app.route('/admin/stats-api')
@admin_required
def admin_stats_api():
    db = get_db()
    stats = {
        row['key']: row['value']
        for row in db.execute("SELECT key, value FROM stats").fetchall()
    }
    return jsonify(stats)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
