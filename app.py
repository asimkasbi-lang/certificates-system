"""
نظام استخراج الشهادات الدراسية
Certificate Extraction System
FuticFlow Automation Systems © 2026
"""

import os, re, json, uuid, hashlib, logging, threading
from io import BytesIO
from functools import lru_cache
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, abort, make_response
from pypdf import PdfReader, PdfWriter

# ─────────────────────────────────────────
# Embedded HTML Templates
# ─────────────────────────────────────────
INDEX_HTML = '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n  <meta charset="UTF-8"/>\n  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n  <title>{{ school.name_ar }} - بوابة الشهادات</title>\n  <style>\n    :root {\n      --brand: {{ school.color }};\n      --brand-dark: color-mix(in srgb, {{ school.color }} 80%, black);\n      --radius: 16px;\n    }\n\n    * { box-sizing: border-box; margin: 0; padding: 0; }\n\n    body {\n      font-family: \'Segoe UI\', Tahoma, Arial, sans-serif;\n      background: #f0f4f8;\n      min-height: 100vh;\n      display: flex;\n      flex-direction: column;\n      align-items: center;\n      justify-content: center;\n      padding: 20px;\n    }\n\n    /* ── Card ─────────────────────────── */\n    .card {\n      background: #fff;\n      border-radius: var(--radius);\n      box-shadow: 0 4px 24px rgba(0,0,0,.10);\n      padding: 40px 36px;\n      width: 100%;\n      max-width: 480px;\n      text-align: center;\n    }\n\n    /* ── Header ───────────────────────── */\n    .school-name {\n      font-size: 1.5rem;\n      font-weight: 800;\n      color: #1e293b;\n      line-height: 1.4;\n      margin-bottom: 6px;\n    }\n    .portal-title {\n      font-size: 1rem;\n      color: #64748b;\n      margin-bottom: 32px;\n    }\n\n    /* ── Input group ──────────────────── */\n    .label {\n      display: block;\n      font-size: .95rem;\n      font-weight: 700;\n      color: #334155;\n      margin-bottom: 10px;\n      text-align: right;\n    }\n    input[type="text"] {\n      width: 100%;\n      padding: 14px 16px;\n      border: 2px solid #e2e8f0;\n      border-radius: 10px;\n      font-size: 1rem;\n      text-align: center;\n      letter-spacing: 2px;\n      direction: ltr;\n      transition: border-color .2s;\n      outline: none;\n    }\n    input[type="text"]:focus { border-color: var(--brand); }\n\n    /* ── Button ───────────────────────── */\n    .btn {\n      display: flex;\n      align-items: center;\n      justify-content: center;\n      gap: 8px;\n      width: 100%;\n      margin-top: 18px;\n      padding: 15px;\n      background: var(--brand);\n      color: #fff;\n      border: none;\n      border-radius: 10px;\n      font-size: 1.05rem;\n      font-weight: 700;\n      cursor: pointer;\n      transition: background .2s, transform .1s;\n    }\n    .btn:hover  { background: var(--brand-dark); }\n    .btn:active { transform: scale(.98); }\n    .btn:disabled { opacity: .6; cursor: not-allowed; }\n\n    /* ── Spinner ──────────────────────── */\n    .spinner {\n      width: 18px; height: 18px;\n      border: 3px solid rgba(255,255,255,.4);\n      border-top-color: #fff;\n      border-radius: 50%;\n      animation: spin .7s linear infinite;\n    }\n    @keyframes spin { to { transform: rotate(360deg); } }\n\n    /* ── Result panel ─────────────────── */\n    .result {\n      margin-top: 24px;\n      padding: 18px 20px;\n      border-radius: 12px;\n      font-size: .95rem;\n      line-height: 1.7;\n      display: none;\n    }\n    .result.success {\n      background: #f0fdf4;\n      border: 1.5px solid #86efac;\n      color: #166534;\n      display: block;\n    }\n    .result.error {\n      background: #fef2f2;\n      border: 1.5px solid #fca5a5;\n      color: #991b1b;\n      display: block;\n    }\n    .result-title {\n      font-weight: 800;\n      font-size: 1.05rem;\n      margin-bottom: 10px;\n    }\n\n    /* ── Download button ──────────────── */\n    .dl-btn {\n      display: inline-flex;\n      align-items: center;\n      gap: 8px;\n      margin-top: 14px;\n      padding: 13px 28px;\n      background: var(--brand);\n      color: #fff;\n      text-decoration: none;\n      border-radius: 10px;\n      font-size: 1rem;\n      font-weight: 700;\n      transition: background .2s;\n    }\n    .dl-btn:hover { background: var(--brand-dark); }\n\n    /* ── Footer ───────────────────────── */\n    footer {\n      margin-top: 28px;\n      font-size: .78rem;\n      color: #94a3b8;\n      text-align: center;\n      line-height: 1.7;\n    }\n  </style>\n</head>\n<body>\n\n<div class="card">\n  <p style="font-size:2.4rem; margin-bottom:8px;">{{ school.emoji }}</p>\n  <h1 class="school-name">{{ school.name_ar }}</h1>\n  <p class="portal-title">بوابة استخراج الشهادات الدراسية</p>\n\n  <label class="label" for="civil_id">الرقم المدني للطالب:</label>\n  <input type="text" id="civil_id" maxlength="8" inputmode="numeric"\n         placeholder="أدخل الرقم المدني المكون من 7 أو 8 أرقام"\n         oninput="this.value=this.value.replace(/\\D/g,\'\')"/>\n\n  <button class="btn" id="searchBtn" onclick="search()">\n    <span id="btnText">🔍 ابحث عن الشهادة</span>\n    <span id="btnSpinner" class="spinner" style="display:none"></span>\n  </button>\n\n  <div id="result"></div>\n</div>\n\n<footer>\n  تم التطوير والتطبيق بواسطة أخصائي نظم مدرسية: عاصم ناصر الكاسبي<br/>\n  FuticFlow Automation Systems © 2026\n</footer>\n\n<script>\n  const input = document.getElementById(\'civil_id\');\n  input.addEventListener(\'keydown\', e => { if (e.key === \'Enter\') search(); });\n\n  async function search() {\n    const civil_id = input.value.trim();\n    const btn      = document.getElementById(\'searchBtn\');\n    const btnText  = document.getElementById(\'btnText\');\n    const spinner  = document.getElementById(\'btnSpinner\');\n    const resultEl = document.getElementById(\'result\');\n\n    if (!/^\\d{7,8}$/.test(civil_id)) {\n      showError(\'يرجى إدخال رقم مدني صحيح مكون من 7 أو 8 أرقام.\');\n      return;\n    }\n\n    // Loading state\n    btn.disabled   = true;\n    btnText.style.display  = \'none\';\n    spinner.style.display  = \'inline-block\';\n    resultEl.className     = \'\';\n    resultEl.style.display = \'none\';\n    resultEl.innerHTML     = \'\';\n\n    try {\n      const res  = await fetch(\'/api/search\', {\n        method:  \'POST\',\n        headers: { \'Content-Type\': \'application/json\' },\n        body:    JSON.stringify({ civil_id })\n      });\n      const data = await res.json();\n\n      if (data.success) {\n        showSuccess(data);\n      } else {\n        showError(data.message || \'حدث خطأ غير متوقع.\');\n      }\n    } catch (err) {\n      showError(\'تعذّر الاتصال بالخادم. يرجى المحاولة لاحقاً.\');\n    } finally {\n      btn.disabled          = false;\n      btnText.style.display = \'inline\';\n      spinner.style.display = \'none\';\n    }\n  }\n\n  function showSuccess(data) {\n    const el = document.getElementById(\'result\');\n    el.className = \'result success\';\n    el.innerHTML = `\n      <div class="result-title">✅ تم العثور على الشهادة!</div>\n      <p>يمكنك تحميل الشهادة الدراسية عبر الرابط أدناه.</p>\n      <p style="font-size:.82rem;color:#166534;margin-top:6px;">\n        ⏱ الرابط صالح لمدة ${data.expires_hours} ساعة — يمكنك الرجوع إليه في أي وقت.\n      </p>\n      <a class="dl-btn" href="${data.download_url}" target="_blank" rel="noopener">\n        📄 تحميل الشهادة الدراسية\n      </a>\n    `;\n  }\n\n  function showError(msg) {\n    const el = document.getElementById(\'result\');\n    el.className = \'result error\';\n    el.innerHTML = `<div class="result-title">❌ لم يتم العثور على الشهادة</div><p>${msg}</p>`;\n  }\n</script>\n</body>\n</html>\n'

ERROR_HTML = '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n  <meta charset="UTF-8"/>\n  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n  <title>خطأ - بوابة الشهادات</title>\n  <style>\n    body { font-family: Arial, sans-serif; display: flex; align-items: center;\n           justify-content: center; min-height: 100vh; background: #f0f4f8; }\n    .box { background: #fff; border-radius: 16px; padding: 40px; max-width: 440px;\n           text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,.1); }\n    h2 { color: #991b1b; margin-bottom: 14px; }\n    p  { color: #64748b; line-height: 1.7; }\n    a  { display: inline-block; margin-top: 20px; padding: 12px 28px;\n         background: #16a34a; color: #fff; text-decoration: none;\n         border-radius: 10px; font-weight: 700; }\n  </style>\n</head>\n<body>\n  <div class="box">\n    <p style="font-size:3rem">⚠️</p>\n    <h2>رابط غير صالح</h2>\n    <p>{{ message }}</p>\n    <a href="/">العودة للبوابة</a>\n  </div>\n</body>\n</html>\n'



BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PDF_DIR    = os.path.join(BASE_DIR, "pdfs")
INDEX_FILE = os.path.join(BASE_DIR, "civil_index.json")
TOKEN_STORE_FILE = os.path.join(BASE_DIR, "tokens.json")
TOKEN_EXPIRY_HOURS = 72

SCHOOLS = {
    "alqaqaa": {"name_ar": "مدرسة القعقاع بن عمرو التميمي", "name_en": "ALQaqaa bin Amro ALtamimi School", "emoji": "🏫", "color": "#16a34a"},
    "school2": {"name_ar": "مدرسة النور الأساسية",           "name_en": "Al Noor Basic School",               "emoji": "🌟", "color": "#2563eb"},
    "school3": {"name_ar": "مدرسة الفجر للبنات",             "name_en": "Al Fajr Girls School",                "emoji": "🌸", "color": "#9333ea"},
    "school4": {"name_ar": "مدرسة السلام الأساسية",          "name_en": "Al Salam Basic School",               "emoji": "🕊️", "color": "#0891b2"},
}

INDEX_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{name_ar} - بوابة الشهادات</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#f0f4f8;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}}
    .card{{background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.10);padding:40px 36px;width:100%;max-width:480px;text-align:center}}
    .school-name{{font-size:1.5rem;font-weight:800;color:#1e293b;line-height:1.4;margin-bottom:6px}}
    .portal-title{{font-size:1rem;color:#64748b;margin-bottom:32px}}
    .label{{display:block;font-size:.95rem;font-weight:700;color:#334155;margin-bottom:10px;text-align:right}}
    input[type=text]{{width:100%;padding:14px 16px;border:2px solid #e2e8f0;border-radius:10px;font-size:1rem;text-align:center;letter-spacing:2px;direction:ltr;transition:border-color .2s;outline:none}}
    input[type=text]:focus{{border-color:{color}}}
    .btn{{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;margin-top:18px;padding:15px;background:{color};color:#fff;border:none;border-radius:10px;font-size:1.05rem;font-weight:700;cursor:pointer;transition:background .2s,transform .1s}}
    .btn:disabled{{opacity:.6;cursor:not-allowed}}
    .spinner{{width:18px;height:18px;border:3px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    .result{{margin-top:24px;padding:18px 20px;border-radius:12px;font-size:.95rem;line-height:1.7;display:none}}
    .result.success{{background:#f0fdf4;border:1.5px solid #86efac;color:#166534;display:block}}
    .result.error{{background:#fef2f2;border:1.5px solid #fca5a5;color:#991b1b;display:block}}
    .result-title{{font-weight:800;font-size:1.05rem;margin-bottom:10px}}
    .dl-btn{{display:inline-flex;align-items:center;gap:8px;margin-top:14px;padding:13px 28px;background:{color};color:#fff;text-decoration:none;border-radius:10px;font-size:1rem;font-weight:700}}
    footer{{margin-top:28px;font-size:.78rem;color:#94a3b8;text-align:center;line-height:1.7}}
  </style>
</head>
<body>
<div class="card">
  <p style="font-size:2.4rem;margin-bottom:8px">{emoji}</p>
  <h1 class="school-name">{name_ar}</h1>
  <p class="portal-title">بوابة استخراج الشهادات الدراسية</p>
  <label class="label" for="civil_id">الرقم المدني للطالب:</label>
  <input type="text" id="civil_id" maxlength="8" inputmode="numeric" placeholder="أدخل الرقم المدني المكون من 7 أو 8 أرقام" oninput="this.value=this.value.replace(/\\D/g,'')"/>
  <button class="btn" id="searchBtn" onclick="search()">
    <span id="btnText">🔍 ابحث عن الشهادة</span>
    <span id="btnSpinner" class="spinner" style="display:none"></span>
  </button>
  <div id="result"></div>
</div>
<footer>تم التطوير والتطبيق بواسطة أخصائي نظم مدرسية: عاصم ناصر الكاسبي<br/>FuticFlow Automation Systems © 2026</footer>
<script>
  document.getElementById('civil_id').addEventListener('keydown',e=>{{if(e.key==='Enter')search()}});
  async function search(){{
    const civil_id=document.getElementById('civil_id').value.trim();
    const btn=document.getElementById('searchBtn');
    const btnText=document.getElementById('btnText');
    const spinner=document.getElementById('btnSpinner');
    const resultEl=document.getElementById('result');
    if(!/^\\d{{7,8}}$/.test(civil_id)){{showError('يرجى إدخال رقم مدني صحيح مكون من 7 أو 8 أرقام.');return;}}
    btn.disabled=true;btnText.style.display='none';spinner.style.display='inline-block';
    resultEl.className='';resultEl.style.display='none';resultEl.innerHTML='';
    try{{
      const res=await fetch('/api/search',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{civil_id}})}});
      const data=await res.json();
      if(data.success)showSuccess(data);else showError(data.message||'حدث خطأ غير متوقع.');
    }}catch(err){{showError('تعذّر الاتصال بالخادم.');}}
    finally{{btn.disabled=false;btnText.style.display='inline';spinner.style.display='none';}}
  }}
  function showSuccess(data){{
    const el=document.getElementById('result');
    el.className='result success';
    el.innerHTML=`<div class="result-title">✅ تم العثور على الشهادة!</div><p>يمكنك تحميل الشهادة الدراسية عبر الرابط أدناه.</p><p style="font-size:.82rem;margin-top:6px">⏱ الرابط صالح لمدة ${{data.expires_hours}} ساعة</p><a class="dl-btn" href="${{data.download_url}}" target="_blank">📄 تحميل الشهادة الدراسية</a>`;
  }}
  function showError(msg){{
    const el=document.getElementById('result');
    el.className='result error';
    el.innerHTML=`<div class="result-title">❌ لم يتم العثور على الشهادة</div><p>${{msg}}</p>`;
  }}
</script>
</body></html>"""

ERROR_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"/><title>خطأ</title>
<style>body{{font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#f0f4f8}}.box{{background:#fff;border-radius:16px;padding:40px;max-width:440px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,.1)}}h2{{color:#991b1b;margin-bottom:14px}}p{{color:#64748b;line-height:1.7}}a{{display:inline-block;margin-top:20px;padding:12px 28px;background:#16a34a;color:#fff;text-decoration:none;border-radius:10px;font-weight:700}}</style>
</head>
<body><div class="box"><p style="font-size:3rem">⚠️</p><h2>رابط غير صالح</h2><p>{message}</p><a href="/">العودة للبوابة</a></div></body></html>"""

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

_civil_index = {}
_index_lock  = threading.Lock()
_tokens      = {}
_tokens_lock = threading.Lock()

def load_index():
    global _civil_index
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            _civil_index = json.load(f)
        log.info("Index loaded: %d students", len(_civil_index))
        return
    log.info("Building index from PDFs...")
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

def _load_tokens():
    global _tokens
    if os.path.exists(TOKEN_STORE_FILE):
        try:
            with open(TOKEN_STORE_FILE, "r") as f:
                _tokens = json.load(f)
        except:
            _tokens = {}

def _save_tokens():
    with open(TOKEN_STORE_FILE, "w") as f:
        json.dump(_tokens, f)

def _purge_expired():
    now = datetime.utcnow()
    expired = [t for t, v in _tokens.items() if datetime.fromisoformat(v["expires"]) < now]
    for t in expired:
        del _tokens[t]
    if expired:
        _save_tokens()

def create_token(civil_id):
    with _tokens_lock:
        _purge_expired()
        for tok, val in _tokens.items():
            if val["civil_id"] == civil_id:
                if datetime.fromisoformat(val["expires"]) > datetime.utcnow() + timedelta(hours=1):
                    return tok
        token = hashlib.sha256(f"{civil_id}:{uuid.uuid4()}".encode()).hexdigest()
        expires = (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()
        _tokens[token] = {"civil_id": civil_id, "expires": expires}
        _save_tokens()
        return token

def resolve_token(token):
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

@lru_cache(maxsize=4)
def _get_reader(fname):
    return PdfReader(os.path.join(PDF_DIR, fname))

def extract_page_pdf(fname, page_num):
    reader = _get_reader(fname)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_num - 1])
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()

@app.route("/")
def index_redirect():
    s = SCHOOLS["alqaqaa"]
    return INDEX_HTML.format(**s)

@app.route("/school/<school_key>")
def school_portal(school_key):
    school = SCHOOLS.get(school_key)
    if not school:
        abort(404)
    return INDEX_HTML.format(**school)

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True, silent=True) or {}
    civil_id = str(data.get("civil_id", "")).strip()
    if not re.fullmatch(r"\d{7,8}", civil_id):
        return jsonify({"success": False, "message": "الرقم المدني غير صحيح. يجب أن يكون 7 أو 8 أرقام."}), 400
    with _index_lock:
        entry = _civil_index.get(civil_id)
    if not entry:
        return jsonify({"success": False, "message": "لم يتم العثور على شهادة بهذا الرقم المدني."}), 404
    token = create_token(civil_id)
    return jsonify({"success": True, "message": "تم العثور على الشهادة!", "token": token, "download_url": f"/download/{token}", "expires_hours": TOKEN_EXPIRY_HOURS})

@app.route("/download/<token>")
def download_certificate(token):
    civil_id = resolve_token(token)
    if not civil_id:
        return ERROR_HTML.format(message="الرابط منتهي الصلاحية أو غير صحيح. الرجاء البحث مجدداً."), 410
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
    resp.headers["Content-Disposition"] = f'inline; filename="certificate_{civil_id}.pdf"'
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.route("/health")
def health():
    return jsonify({"status": "ok", "students": len(_civil_index)})

if __name__ == "__main__":
    _load_tokens()
    load_index()
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
