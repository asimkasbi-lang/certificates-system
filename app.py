import os, re, json, logging, threading, hmac, hashlib, base64
from io import BytesIO
from functools import lru_cache
from flask import Flask, request, jsonify, make_response, abort
from pypdf import PdfReader, PdfWriter

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PDF_DIR    = os.path.join(BASE_DIR, "pdfs")
INDEX_FILE = os.path.join(BASE_DIR, "civil_index.json")
SECRET     = "futicflow2026securekey"

SCHOOLS = {
    "alqaqaa": {
        "name_ar": "مدرسة القعقاع بن عمرو التميمي",
        "name_en": "ALQaqaa bin Amro ALtamimi School",
        "emoji": "🏫",
        "color": "#16a34a",
    },
    "sultanboos": {
        "name_ar": "مدرسة السلطان قابوس",
        "name_en": "Sultan Qaboos School",
        "emoji": "🏫",
        "color": "#1d4ed8",
    },
    "asimbnaddi": {
        "name_ar": "مدرسة عاصم بن عدي",
        "name_en": "Asim bin Addi School",
        "emoji": "🏫",
        "color": "#b45309",
    },
    "aljawabi": {
        "name_ar": "مدرسة الجوابي للبنات",
        "name_en": "ALJawabi Girls School",
        "emoji": "🌸",
        "color": "#9333ea",
    },
}

FOOTER = "تم التطوير بواسطة أخصائي أنظمه مدرسية: عاصم ناصر الكاسبي"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
app = Flask(__name__)

# ── Civil ID Index ──────────────────────────────
_civil_index = {}
_index_lock  = threading.Lock()

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
    except Exception:
        os.system("pip install pdfplumber -q")
        import pdfplumber
    idx = {}
    for fname in sorted(os.listdir(PDF_DIR)):
        if not fname.endswith(".pdf"):
            continue
        with pdfplumber.open(os.path.join(PDF_DIR, fname)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                m = re.search(r"CIVIL NO\s*:\s*(\d{7,8})", text)
                if m:
                    idx[m.group(1)] = {"file": fname, "page": i+1}
    _civil_index = idx
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    log.info("Index built: %d students", len(idx))

# ── Stateless Token ─────────────────────────────
def make_token(civil_id):
    sig = hmac.new(SECRET.encode(), civil_id.encode(), hashlib.sha256).hexdigest()[:16]
    payload = base64.urlsafe_b64encode(civil_id.encode()).decode()
    return f"{payload}.{sig}"

def verify_token(token):
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        civil_id = base64.urlsafe_b64decode(parts[0]).decode()
        expected = hmac.new(SECRET.encode(), civil_id.encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(parts[1], expected):
            return civil_id
        return None
    except Exception:
        return None

# ── PDF Extract ─────────────────────────────────
@lru_cache(maxsize=10)
def get_reader(fname):
    return PdfReader(os.path.join(PDF_DIR, fname))

def extract_page(fname, page_num):
    reader = get_reader(fname)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_num - 1])
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()

# ── HTML ────────────────────────────────────────
def render_page(school):
    color = school["color"]
    name  = school["name_ar"]
    emoji = school["emoji"]
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{name} - بوابة الشهادات</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f4f8;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}}
.card{{background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.1);padding:40px 36px;width:100%;max-width:480px;text-align:center}}
.school-name{{font-size:1.5rem;font-weight:800;color:#1e293b;margin-bottom:6px}}
.sub{{font-size:1rem;color:#64748b;margin-bottom:32px}}
.label{{display:block;font-size:.95rem;font-weight:700;color:#334155;margin-bottom:10px;text-align:right}}
input{{width:100%;padding:14px 16px;border:2px solid #e2e8f0;border-radius:10px;font-size:1rem;text-align:center;letter-spacing:2px;direction:ltr;outline:none;transition:border-color .2s}}
input:focus{{border-color:{color}}}
.btn{{width:100%;margin-top:18px;padding:15px;background:{color};color:#fff;border:none;border-radius:10px;font-size:1.05rem;font-weight:700;cursor:pointer;transition:opacity .2s}}
.btn:hover{{opacity:.9}}
.btn:disabled{{opacity:.6;cursor:not-allowed}}
#result{{margin-top:20px;padding:18px;border-radius:12px;display:none;font-size:.95rem;line-height:1.8}}
.dl-btn{{display:inline-block;margin-top:14px;padding:13px 28px;background:{color};color:#fff;text-decoration:none;border-radius:10px;font-weight:700;font-size:1rem}}
footer{{margin-top:28px;font-size:.78rem;color:#94a3b8;text-align:center;line-height:1.7}}
</style>
</head>
<body>
<div class="card">
  <p style="font-size:2.4rem;margin-bottom:8px">{emoji}</p>
  <h1 class="school-name">{name}</h1>
  <p class="sub">بوابة استخراج الشهادات الدراسية</p>
  <label class="label">الرقم المدني للطالب:</label>
  <input type="text" id="cid" maxlength="8" inputmode="numeric"
         placeholder="أدخل الرقم المدني"
         oninput="this.value=this.value.replace(/\\D/g,'')"/>
  <button class="btn" id="btn" onclick="doSearch()">🔍 ابحث عن الشهادة</button>
  <div id="result"></div>
</div>
<footer>{FOOTER}<br/>FuticFlow Automation Systems &copy; 2026</footer>
<script>
document.getElementById('cid').addEventListener('keydown',function(e){{if(e.key==='Enter')doSearch()}});
async function doSearch(){{
  var cid=document.getElementById('cid').value.trim();
  var btn=document.getElementById('btn');
  var res=document.getElementById('result');
  if(!/^\\d{{7,8}}$/.test(cid)){{showErr('يرجى إدخال رقم مدني صحيح مكون من 7 أو 8 أرقام');return;}}
  btn.disabled=true;btn.textContent='جاري البحث...';
  res.style.display='none';
  try{{
    var r=await fetch('/api/search',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{civil_id:cid}})}});
    var d=await r.json();
    if(d.success){{
      res.innerHTML='<b>✅ تم العثور على الشهادة!</b><br/>يمكنك تحميل الشهادة الدراسية عبر الرابط أدناه<br/><a class="dl-btn" href="'+d.download_url+'" target="_blank">📄 تحميل الشهادة الدراسية</a>';
      res.style.cssText='display:block;background:#f0fdf4;border:1.5px solid #86efac;color:#166534;margin-top:20px;padding:18px;border-radius:12px;text-align:center';
    }}else{{showErr(d.message||'لم يتم العثور على شهادة بهذا الرقم المدني');}}
  }}catch(e){{showErr('تعذّر الاتصال بالخادم، يرجى المحاولة لاحقاً');}}
  finally{{btn.disabled=false;btn.textContent='🔍 ابحث عن الشهادة';}}
}}
function showErr(m){{
  var r=document.getElementById('result');
  r.innerHTML='<b>❌ '+m+'</b>';
  r.style.cssText='display:block;background:#fef2f2;border:1.5px solid #fca5a5;color:#991b1b;margin-top:20px;padding:18px;border-radius:12px;text-align:center';
}}
</script>
</body>
</html>"""

# ── Routes ──────────────────────────────────────
@app.route("/")
def index():
    return render_page(SCHOOLS["alqaqaa"])

@app.route("/school/<key>")
def school(key):
    s = SCHOOLS.get(key)
    if not s: abort(404)
    return render_page(s)

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True, silent=True) or {}
    cid  = str(data.get("civil_id", "")).strip()
    if not re.fullmatch(r"\d{7,8}", cid):
        return jsonify({"success": False, "message": "رقم مدني غير صحيح"}), 400
    with _index_lock:
        entry = _civil_index.get(cid)
    if not entry:
        return jsonify({"success": False, "message": "لم يتم العثور على شهادة بهذا الرقم المدني"}), 404
    token = make_token(cid)
    return jsonify({"success": True, "download_url": f"/download/{token}"})

@app.route("/download/<token>")
def download(token):
    cid = verify_token(token)
    if not cid:
        return "<h2 style='font-family:Arial;padding:20px'>الرابط غير صحيح</h2><a href='/'>عودة</a>", 410
    with _index_lock:
        entry = _civil_index.get(cid)
    if not entry: abort(404)
    try:
        pdf_bytes = extract_page(entry["file"], entry["page"])
    except Exception as e:
        log.error("PDF error: %s", e)
        abort(500)
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="certificate_{cid}.pdf"'
    return resp

@app.route("/health")
def health():
    return jsonify({"status": "ok", "students": len(_civil_index)})

# ── Startup ──────────────────────────────────────
load_index()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
