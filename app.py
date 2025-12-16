from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import json
import os
import uuid

app = FastAPI()

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

QR_SIZE = 200

# ---------------- CORE LOGIC ----------------

def generate_pdf(reg_no_input: str) -> str:
    # Check essential files
    if not os.path.exists(TEMPLATE):
        raise FileNotFoundError(f"Template image not found: {TEMPLATE}")
    if not os.path.exists(FONT_REGULAR):
        raise FileNotFoundError(f"Regular font not found: {FONT_REGULAR}")
    if not os.path.exists(FONT_BOLD):
        raise FileNotFoundError(f"Bold font not found: {FONT_BOLD}")
    if not os.path.exists(JSON_FILE):
        raise FileNotFoundError(f"JSON file not found: {JSON_FILE}")

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

    name = student["name"].strip().upper()
    reg_no = student["registrationNo"]
    roll_no = str(student["rollNo"]).replace(".0", "")
    section = student["section"].strip().upper()
    class_ = student_class

    temp_image = os.path.join(BASE_DIR, f"{uuid.uuid4()}.png")
    output_pdf = os.path.join(BASE_DIR, f"{reg_no}_{uuid.uuid4()}.pdf")

    # Load template and fonts
    img = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_regular = ImageFont.truetype(FONT_REGULAR, FONT_SIZE)
    font_bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE)

    # Draw student details
    draw.text(POS["reg"], reg_no, fill="black", font=font_regular)
    draw.text(POS["name"], name, fill="black", font=font_bold)
    draw.text(POS["class"], class_, fill="black", font=font_regular)
    draw.text(POS["section"], section, fill="black", font=font_regular)
    draw.text(POS["roll"], roll_no, fill="black", font=font_bold)

    # Generate QR
    qr_data = (
        f"{reg_no}({name}),"
        f"Class:{class_},"
        f"Sec:{section}/"
        f"Exam:PRE BOARD-2/"
        f"PRE BOARD-2-CHINMAYA"
    )
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((QR_SIZE, QR_SIZE))
    img.paste(qr_img, POS["qr"])

    # Save temporary image
    img.save(temp_image)

    # Create PDF
    c = canvas.Canvas(output_pdf, pagesize=A4)
    page_width, page_height = A4
    c.drawImage(temp_image, 0, 0, width=page_width, height=page_height)
    c.showPage()
    c.save()

    # Cleanup temp image
    os.remove(temp_image)

    return output_pdf

# ---------------- API ENDPOINT ----------------

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
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
