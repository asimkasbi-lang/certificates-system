import os, re, json, logging, threading, hmac, hashlib, base64
from io import BytesIO
from functools import lru_cache
from flask import Flask, request, jsonify, make_response, abort
from pypdf import PdfReader, PdfWriter

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PDF_DIR    = os.path.join(BASE_DIR, "pdfs")
INDEX_FILE = os.path.join(BASE_DIR, "civil_index.json")
SECRET     = os.environ.get("SECRET_KEY", "CHANGE_ME")

SCHOOLS = {
    "sultanboos": {
        "name_ar": "مدرسة السلطان قابوس للبنين",
        "name_en": "Sultan Qaboos School",
        "emoji": "🏫",
        "color": "#1d4ed8",
    },
    "alqaqaa": {
        "name_ar": "\u0645\u062f\u0631\u0633\u0629 \u0627\u0644\u0642\u0639\u0642\u0627\u0639 \u0628\u0646 \u0639\u0645\u0631\u0648 \u0627\u0644\u062a\u0645\u064a\u0645\u064a \u0644\u0644\u0628\u0646\u064a\u0646",
        "name_en": "Al Qaqaa Bin Amr Al Tamimi School",
        "emoji": "\U0001f3eb",
        "color": "#0f766e",
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
    with _index_lock:
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
                    m = re.search(r"CIVIL NO\s*:?\s*(\d{7,15})", text)
                    if m:
                        idx[m.group(1)] = {"file": fname, "page": i+1}

        _civil_index = idx

        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False)

        log.info("Index built: %d students", len(idx))


# ── Token System ────────────────────────────────
def make_token(civil_id):
    sig = hmac.new(SECRET.encode(), civil_id.encode(), hashlib.sha256).hexdigest()
    payload = base64.urlsafe_b64encode(civil_id.encode()).decode()
    return f"{payload}.{sig}"

def verify_token(token):
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        civil_id = base64.urlsafe_b64decode(parts[0]).decode()
        expected = hmac.new(SECRET.encode(), civil_id.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(parts[1], expected):
            return civil_id

        return None
    except Exception:
        return None


# ── PDF Extract ────────────────────────────────
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
body{{font-family:Arial;background:#f0f4f8;display:flex;justify-content:center;align-items:center;min-height:100vh}}
.card{{background:#fff;padding:40px;border-radius:16px;max-width:480px;width:100%;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1)}}
input{{width:100%;padding:14px;border-radius:10px;border:2px solid #e2e8f0;text-align:center;direction:ltr;font-size:1rem}}
input:focus{{border-color:{color}}}
button{{width:100%;margin-top:15px;padding:14px;background:{color};color:#fff;border:none;border-radius:10px;font-weight:bold;cursor:pointer}}
#result{{margin-top:15px;display:none}}
footer{{margin-top:20px;font-size:.8rem;color:#94a3b8}}
</style>

</head>
<body>

<div class="card">
  <div style="font-size:2.5rem">{emoji}</div>
  <h2>{name}</h2>

  <input id="cid" placeholder="الرقم المدني" maxlength="15"
         oninput="this.value=this.value.replace(/\\D/g,'')"/>

  <button onclick="search()">بحث</button>

  <div id="result"></div>

  <footer>{FOOTER}</footer>
</div>

<script>
async function search(){{
  let cid=document.getElementById("cid").value;
  let r=document.getElementById("result");

  if(!/^\\d{{7,15}}$/.test(cid)){{
    r.innerHTML="رقم غير صحيح";
    r.style.display="block";
    return;
  }}

  let res=await fetch("/api/search",{{
    method:"POST",
    headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify({{civil_id:cid}})
  }});

  let data=await res.json();

  if(data.success){{
    r.innerHTML=`<a href="${{data.download_url}}" target="_blank">تحميل الشهادة</a>`;
  }} else {{
    r.innerHTML=data.message;
  }}

  r.style.display="block";
}}
</script>

</body>
</html>"""


# ── Routes ──────────────────────────────────────
@app.route("/")
def index():
    return render_page(SCHOOLS["sultanboos"])

@app.route("/school/<key>")
def school(key):
    s = SCHOOLS.get(key)
    if not s:
        abort(404)
    return render_page(s)


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True, silent=True) or {}
    cid = str(data.get("civil_id", "")).strip()

    if not re.fullmatch(r"\d{7,15}", cid):
        return jsonify({"success": False, "message": "رقم مدني غير صحيح"}), 400

    with _index_lock:
        entry = _civil_index.get(cid)

    if not entry:
        return jsonify({"success": False, "message": "لم يتم العثور على شهادة"}), 404

    token = make_token(cid)
    return jsonify({"success": True, "download_url": f"/download/{token}"})


@app.route("/download/<token>")
def download(token):
    cid = verify_token(token)
    if not cid:
        return "الرابط غير صحيح", 410

    with _index_lock:
        entry = _civil_index.get(cid)

    if not entry:
        abort(404)

    pdf_bytes = extract_page(entry["file"], entry["page"])

    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="{cid}.pdf"'
    return resp


@app.route("/health")
def health():
    return jsonify({"status": "ok", "students": len(_civil_index)})


# ── Startup ──────────────────────────────────────
load_index()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
