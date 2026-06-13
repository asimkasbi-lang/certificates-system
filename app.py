
"""
نظام استخراج الشهادات الدراسية
Certificate Extraction System
FuticFlow Automation Systems © 2026
"""
 
import os
import re
import json
import uuid
import hashlib
import logging
import threading
from io import BytesIO
from functools import lru_cache
from datetime import datetime, timedelta
 
from flask import (
    Flask, request, jsonify, send_file,
    render_template, render_template_string, abort, make_response
)
from pypdf import PdfReader, PdfWriter
 
# ─────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR  = os.path.join(BASE_DIR, "pdfs")
INDEX_FILE = os.path.join(BASE_DIR, "civil_index.json")
 
# Schools config — add / rename as needed
SCHOOLS = {
    "alqaqaa": {
        "name_ar": "مدرسة القعقاع بن عمرو التميمي",
        "name_en": "ALQaqaa bin Amro ALtamimi School",
        "emoji": "🏫",
        "color": "#16a34a",   # green
    },
    "school2": {
        "name_ar": "مدرسة النور الأساسية",
        "name_en": "Al Noor Basic School",
        "emoji": "🌟",
        "color": "#2563eb",
    },
    "school3": {
        "name_ar": "مدرسة الفجر للبنات",
        "name_en": "Al Fajr Girls School",
        "emoji": "🌸",
        "color": "#9333ea",
    },
    "school4": {
        "name_ar": "مدرسة السلام الأساسية",
        "name_en": "Al Salam Basic School",
        "emoji": "🕊️",
        "color": "#0891b2",
    },
}
 
# Token expiry (hours) — link stays valid this long
TOKEN_EXPIRY_HOURS = 72
 
# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB request cap
 
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
 
# ─────────────────────────────────────────
# Civil ID Index  (loaded once at startup)
# ─────────────────────────────────────────
_civil_index: dict = {}
_index_lock  = threading.Lock()
 
def load_index():
    """Load or rebuild the civil-ID → {file, page} index."""
    global _civil_index
 
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            _civil_index = json.load(f)
        log.info("Index loaded: %d students", len(_civil_index))
        return
 
    log.info("Building index from PDFs …")
    try:
        import pdfplumber
    except ImportError:
        os.system("pip install pdfplumber --break-system-packages -q")
        import pdfplumber
 
    idx = {}
    for fname in sorted(os.listdir(PDF_DIR)):
        if not fname.endswith(".pdf"):
            continue
        path = os.path.join(PDF_DIR, fname)
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                m = re.search(r"CIVIL NO\s*:\s*(\d{7,8})", text)
                if m:
                    idx[m.group(1)] = {"file": fname, "page": i + 1}
    _civil_index = idx
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    log.info("Index built: %d students", len(idx))
 
 
# ─────────────────────────────────────────
# Token store  (in-memory; survives restarts via JSON file)
# ─────────────────────────────────────────
TOKEN_STORE_FILE = os.path.join(BASE_DIR, "tokens.json")
_tokens: dict = {}  # token -> {civil_id, expires_iso}
_tokens_lock = threading.Lock()
 
def _load_tokens():
    global _tokens
    if os.path.exists(TOKEN_STORE_FILE):
        try:
            with open(TOKEN_STORE_FILE, "r") as f:
                _tokens = json.load(f)
        except Exception:
            _tokens = {}
 
def _save_tokens():
    with open(TOKEN_STORE_FILE, "w") as f:
        json.dump(_tokens, f)
 
def _purge_expired():
    now = datetime.utcnow()
    expired = [t for t, v in _tokens.items()
               if datetime.fromisoformat(v["expires"]) < now]
    for t in expired:
        del _tokens[t]
    if expired:
        _save_tokens()
 
def create_token(civil_id: str) -> str:
    """Return a secure download token for this civil_id."""
    with _tokens_lock:
        _purge_expired()
        # Reuse existing valid token for same civil_id
        for tok, val in _tokens.items():
            if val["civil_id"] == civil_id:
                expires = datetime.fromisoformat(val["expires"])
                if expires > datetime.utcnow() + timedelta(hours=1):
                    return tok
 
        token = hashlib.sha256(
            f"{civil_id}:{uuid.uuid4()}".encode()
        ).hexdigest()
        expires = (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()
        _tokens[token] = {"civil_id": civil_id, "expires": expires}
        _save_tokens()
        return token
 
def resolve_token(token: str):
    """Return civil_id if token valid, else None."""
    with _tokens_lock:
        _purge_expired()
        entry = _tokens.get(token)
        if not entry:
            return None
        if datetime.fromisoformat(entry["expires"]) < datetime.utcnow():
            del _tokens[token]
            _save_tokens()
            return None
        return entry["civil_id"]
 
 
# ─────────────────────────────────────────
# PDF extraction
# ─────────────────────────────────────────
@lru_cache(maxsize=4)
def _get_reader(fname: str) -> PdfReader:
    path = os.path.join(PDF_DIR, fname)
    return PdfReader(path)
 
def extract_page_pdf(fname: str, page_num: int) -> bytes:
    """Extract a single page (1-based) from a PDF and return bytes."""
    reader = _get_reader(fname)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_num - 1])
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()
 
 
# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────
 
@app.route("/")
def index_redirect():
    return render_template_string(open(os.path.join(BASE_DIR,"templates","index.html")).read(), school=SCHOOLS["alqaqaa"], school_key="alqaqaa")
 
@app.route("/school/<school_key>")
def school_portal(school_key):
    school = SCHOOLS.get(school_key)
    if not school:
        abort(404)
    return render_template_string(open(os.path.join(BASE_DIR,"templates","index.html")).read(), school=school, school_key=school_key)
 
 
@app.route("/api/search", methods=["POST"])
def api_search():
    """Lookup a civil ID and return a download token."""
    data = request.get_json(force=True, silent=True) or {}
    civil_id = str(data.get("civil_id", "")).strip()
 
    if not re.fullmatch(r"\d{7,8}", civil_id):
        return jsonify({"success": False,
                        "message": "الرقم المدني غير صحيح. يجب أن يكون 7 أو 8 أرقام."}), 400
 
    with _index_lock:
        entry = _civil_index.get(civil_id)
 
    if not entry:
        return jsonify({"success": False,
                        "message": "لم يتم العثور على شهادة بهذا الرقم المدني."}), 404
 
    token = create_token(civil_id)
    return jsonify({
        "success": True,
        "message": "تم العثور على الشهادة!",
        "token": token,
        "download_url": f"/download/{token}",
        "expires_hours": TOKEN_EXPIRY_HOURS,
    })
 
 
@app.route("/download/<token>")
def download_certificate(token):
    """Stream the single-page certificate PDF."""
    civil_id = resolve_token(token)
    if not civil_id:
        return render_template_string(open(os.path.join(BASE_DIR,"templates","error.html")).read(), message="الرابط منتهي الصلاحية أو غير صحيح. الرجاء البحث مجدداً."), 410
 
    with _index_lock:
        entry = _civil_index.get(civil_id)
    if not entry:
        abort(404)
 
    try:
        pdf_bytes = extract_page_pdf(entry["file"], entry["page"])
    except Exception as e:
        log.error("PDF extraction failed: %s", e)
        abort(500)
 
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = (
        f'inline; filename="certificate_{civil_id}.pdf"'
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp
 
 
@app.route("/health")
def health():
    return jsonify({"status": "ok", "students": len(_civil_index)})
 
 
# ─────────────────────────────────────────
# Boot
# ─────────────────────────────────────────
if __name__ == "__main__":
    _load_tokens()
    load_index()
    # threaded=True handles concurrent requests
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
