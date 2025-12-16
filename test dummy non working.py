from PIL import Image, ImageDraw, ImageFont
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import json
import os
import sys

# ---------------- FIXED SETTINGS ----------------

TEMPLATE = "dummy.png"

FONT_REGULAR = "calibri.ttf"
FONT_BOLD = "calibrib.ttf"
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
TEMP_IMAGE = "__temp__.png"

# ---------------- LOAD JSON ----------------

JSON_FILE = "s.json"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# ---------------- INPUT ----------------

reg_no_input = input("Enter Registration No: ").strip()

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
    print("❌ Registration number not found.")
    sys.exit(1)

# ---------------- EXTRACT DETAILS ----------------

name = student["name"].strip().upper()
reg_no = student["registrationNo"]
roll_no = str(student["rollNo"]).replace(".0", "")
section = student["section"].strip().upper()
class_ = student_class

# ---------------- LOAD IMAGE & FONTS ----------------

img = Image.open(TEMPLATE).convert("RGB")
draw = ImageDraw.Draw(img)

font_regular = ImageFont.truetype(FONT_REGULAR, FONT_SIZE)
font_bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE)

# ---------------- DRAW TEXT ----------------

draw.text(POS["reg"], reg_no, fill="black", font=font_regular)
draw.text(POS["name"], name, fill="black", font=font_bold)
draw.text(POS["class"], class_, fill="black", font=font_regular)
draw.text(POS["section"], section, fill="black", font=font_regular)
draw.text(POS["roll"], roll_no, fill="black", font=font_bold)

# ---------------- QR GENERATION ----------------

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

# ---------------- TEMP IMAGE SAVE ----------------

img.save(TEMP_IMAGE)

# ---------------- PDF ONLY ----------------

OUTPUT_PDF = f"{reg_no}_{name.replace(' ', '_')}.pdf"

c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
page_width, page_height = A4

c.drawImage(
    TEMP_IMAGE,
    0,
    0,
    width=page_width,
    height=page_height,
    preserveAspectRatio=True,
    mask="auto"
)

c.showPage()
c.save()

# ---------------- CLEANUP ----------------

os.remove(TEMP_IMAGE)

print("\n✅ PDF GENERATED SUCCESSFULLY")
print("Saved:", OUTPUT_PDF)
