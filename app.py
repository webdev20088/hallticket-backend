from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import json
import os
import uuid
import requests
from io import BytesIO
import urllib.parse

app = FastAPI()

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cvadmitcard.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- FIXED SETTINGS ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = os.path.join(BASE_DIR, "dummy.png")
JSON_FILE = os.path.join(BASE_DIR, "s.json")

FONT_REGULAR = os.path.join(BASE_DIR, "calibri.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "calibrib.ttf")

FONT_SIZE = 28

POS = {
    "reg": (840, 560),
    "name": (840, 680),
    "class": (490, 620),
    "section": (950, 620),
    "roll": (530, 800),
    "qr": (1320, 1320)
}

QR_SIZE = 200  # DO NOT CHANGE

# ---------------- CORE LOGIC ----------------

def generate_pdf(reg_no_input: str) -> str:

    if not os.path.exists(TEMPLATE):
        raise FileNotFoundError("Template image missing")
    if not os.path.exists(FONT_REGULAR):
        raise FileNotFoundError("Regular font missing")
    if not os.path.exists(FONT_BOLD):
        raise FileNotFoundError("Bold font missing")
    if not os.path.exists(JSON_FILE):
        raise FileNotFoundError("JSON file missing")

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    student = None
    student_class = None

    for class_key, students in data.items():
        for s in students:
            if str(s.get("registrationNo")).strip() == reg_no_input:
                student = s
                student_class = class_key
                break
        if student:
            break

    if not student:
        raise ValueError("Registration number not found")

    # ---------------- DATA ----------------

    name = student["name"].strip().upper()
    reg_no = student["registrationNo"]
    roll_no = str(student["rollNo"]).replace(".0", "")
    section = student["section"].strip().upper()
    class_ = student_class

    temp_img = os.path.join(BASE_DIR, f"{uuid.uuid4()}.png")
    output_pdf = os.path.join(BASE_DIR, f"{reg_no}_{uuid.uuid4()}.pdf")

    # ---------------- IMAGE ----------------

    img = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_regular = ImageFont.truetype(FONT_REGULAR, FONT_SIZE)
    font_bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE)

    draw.text(POS["reg"], reg_no, fill="black", font=font_regular)
    draw.text(POS["name"], name, fill="black", font=font_bold)
    draw.text(POS["class"], class_, fill="black", font=font_regular)
    draw.text(POS["section"], section, fill="black", font=font_regular)
    draw.text(POS["roll"], roll_no, fill="black", font=font_bold)

    # ---------------- FETCH QR (NO GENERATION) ----------------

    qr_text = f"{reg_no}({name}),Class:{class_},Sec:{section}/Exam:PRE BOARD-2/PRE BOARD-2-CHINMAYA"
    encoded_qr_text = urllib.parse.quote(qr_text)

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=200x200&data={encoded_qr_text}"
    )

    qr_response = requests.get(qr_url, timeout=10)

    if qr_response.status_code != 200:
        raise Exception("Failed to fetch QR image")

    qr_img = Image.open(BytesIO(qr_response.content)).convert("RGB")

    # 🔒 ENSURE EXACT SIZE (NO STRETCH)
    if qr_img.size != (QR_SIZE, QR_SIZE):
        qr_img = qr_img.resize((QR_SIZE, QR_SIZE), Image.LANCZOS)

    img.paste(qr_img, POS["qr"])

    # ---------------- SAVE IMAGE ----------------

    img.save(temp_img)

    # ---------------- PDF ----------------

    c = canvas.Canvas(output_pdf, pagesize=A4)
    w, h = A4
    c.drawImage(temp_img, 0, 0, width=w, height=h)
    c.showPage()
    c.save()

    os.remove(temp_img)

    return output_pdf

# ---------------- API ----------------

@app.get("/generate")
def generate(reg_no: str):
    try:
        pdf_path = generate_pdf(reg_no)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"hall_ticket_{reg_no}.pdf"
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid Registration Number")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
