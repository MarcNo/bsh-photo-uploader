#!/usr/bin/env python3
"""
Generate a printable QR code for the BSH Picnic photo uploader.
Usage:  pip install qrcode[pil] Pillow
        python generate_qr.py
Output: qr_code.png  (print this and display at the picnic!)
"""

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw, ImageFont
import os

URL = "http://bull.nozell.com"
EVENT_CODE = os.environ.get("EVENT_CODE", "WELLSBULL159")
OUTPUT = "qr_code.png"

# ── Generate QR ──────────────────────────────────────────────
qr = qrcode.QRCode(
    version=3,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=12,
    border=3,
)
qr.add_data(URL)
qr.make(fit=True)

img_qr_raw = qr.make_image(
    image_factory=StyledPilImage,
    color_mask=SolidFillColorMask(
        back_color=(247, 243, 234),   # ivory
        front_color=(30, 58, 47),     # forest green
    ),
)

# Convert to plain RGB PIL Image so paste() can determine the region size
img_qr = img_qr_raw.convert("RGB")
qr_size = img_qr.size[0]

# ── Build poster card ────────────────────────────────────────
CARD_W, CARD_H = qr_size + 80, qr_size + 220
card = Image.new("RGB", (CARD_W, CARD_H), (247, 243, 234))
draw = ImageDraw.Draw(card)

# Green top bar
draw.rectangle([0, 0, CARD_W, 60], fill=(30, 58, 47))

# Title text in top bar
try:
    font_title  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 22)
    font_body   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_code   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 28)
    font_small  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
except OSError:
    font_title = font_body = font_code = font_small = ImageFont.load_default()

draw.text((CARD_W // 2, 30), "159th Annual BSH Family Picnic",
          fill=(201, 146, 42), font=font_title, anchor="mm")

# QR code centred — use 4-tuple box (left, top, right, bottom)
qr_x = (CARD_W - qr_size) // 2
card.paste(img_qr, (qr_x, 70, qr_x + qr_size, 70 + qr_size))

y = 70 + qr_size + 12

draw.text((CARD_W // 2, y + 10), "Scan to share your photos!",
          fill=(30, 58, 47), font=font_body, anchor="mm")

draw.text((CARD_W // 2, y + 38), "Then enter the event code:",
          fill=(74, 74, 58), font=font_small, anchor="mm")

# Code box
box_w, box_h = 280, 48
bx = (CARD_W - box_w) // 2
by = y + 55
draw.rectangle([bx, by, bx + box_w, by + box_h], fill=(30, 58, 47), outline=(201, 146, 42), width=2)
draw.text((CARD_W // 2, by + box_h // 2), EVENT_CODE,
          fill=(229, 184, 90), font=font_code, anchor="mm")

draw.text((CARD_W // 2, CARD_H - 16),
          URL,
          fill=(120, 120, 96), font=font_small, anchor="mm")

# Gold bottom border
draw.rectangle([0, CARD_H - 6, CARD_W, CARD_H], fill=(201, 146, 42))

card.save(OUTPUT)
print(f"QR code saved to {OUTPUT}")
print(f"URL:        {URL}")
print(f"Event code: {EVENT_CODE}")
print("Print this and display it at the picnic welcome table!")
