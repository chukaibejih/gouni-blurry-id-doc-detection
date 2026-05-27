"""
SYNTHETIC ID GENERATOR
======================
Generates fully synthetic, PII-free ID-card-style images for evaluating
blur detection. All data is procedurally generated from fake pools.

Output: source_001.jpg ... source_NNN.jpg in --out folder.
Each image is suitable as input to: python evaluate.py --generate --source <out>

Reproducible: fixed random seed by default.
"""

import argparse
import random
import string
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_W, CARD_H = 850, 540
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD    = "C:/Windows/Fonts/arialbd.ttf"
FONT_MONO    = "C:/Windows/Fonts/consola.ttf"

FIRST_NAMES = [
    "ADAEZE", "BAYO", "CHIDI", "DAMILOLA", "EMEKA", "FATIMA", "GBENGA",
    "HAUWA", "IFEOMA", "JIDE", "KEMI", "LANRE", "MAYOWA", "NGOZI",
    "OLUWATOBI", "PATIENCE", "QUEEN", "RAHEEM", "SADE", "TUNDE",
    "UCHE", "VICTORIA", "WALE", "YEMI", "ZAINAB", "ABIODUN", "BIODUN",
    "CHIOMA", "DAYO", "EBUKA",
]
LAST_NAMES = [
    "ADEYEMI", "BAKARE", "CHUKWU", "DANJUMA", "EZEKWESILI", "FALANA",
    "GBAJABIAMILA", "HASSAN", "IBRAHIM", "JOHNSON", "KALU", "LAWAL",
    "MOHAMMED", "NWOSU", "OKAFOR", "PETERS", "QURESHI", "RAJI",
    "SANUSI", "THOMPSON", "UMARU", "VINCENT", "WILLIAMS", "YUSUF", "ZUBAIR",
]
PLACES_OF_BIRTH = [
    "LAGOS", "ABUJA", "KANO", "IBADAN", "PORT HARCOURT", "BENIN CITY",
    "ENUGU", "KADUNA", "JOS", "ABEOKUTA", "WARRI", "OWERRI", "CALABAR",
]
NATIONALITIES = ["NIGERIAN", "GHANAIAN", "KENYAN", "SOUTH AFRICAN"]
SEXES = ["M", "F"]

TEMPLATES = ["national_id", "drivers_license", "passport"]

COLOR_SCHEMES = [
    {"bg": (245, 248, 240), "header": ( 30,  80,  50), "accent": (180, 30,  40), "text": (20, 25, 35)},
    {"bg": (240, 244, 250), "header": ( 25,  55, 120), "accent": (200, 150, 20), "text": (15, 20, 35)},
    {"bg": (250, 245, 235), "header": (120,  30,  35), "accent": ( 30,  90, 50), "text": (25, 20, 15)},
    {"bg": (235, 240, 235), "header": ( 50, 100,  70), "accent": (200,  80, 30), "text": (20, 30, 25)},
    {"bg": (248, 240, 245), "header": ( 90,  30, 100), "accent": (210, 170, 40), "text": (25, 15, 30)},
]


def rand_id_number(length: int = 11) -> str:
    return "".join(random.choices(string.digits, k=length))


def rand_alphanum(length: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def rand_date(year_start: int, year_end: int) -> str:
    y = random.randint(year_start, year_end)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{d:02d}/{m:02d}/{y}"


def make_face_placeholder(w: int, h: int, seed_rgb: tuple) -> Image.Image:
    """Generate a simple face-like image so the photo region has realistic
    edge content (matters for Laplacian/Tenengrad scoring)."""
    img = Image.new("RGB", (w, h), seed_rgb)
    d = ImageDraw.Draw(img)

    skin = (
        min(255, seed_rgb[0] + random.randint(-15, 15)),
        min(255, seed_rgb[1] + random.randint(-15, 15)),
        min(255, seed_rgb[2] + random.randint(-15, 15)),
    )
    d.rectangle([(0, 0), (w, h)], fill=skin)

    head_w = int(w * 0.7)
    head_h = int(h * 0.75)
    head_x = (w - head_w) // 2
    head_y = int(h * 0.10)
    head_color = (max(0, skin[0] - 25), max(0, skin[1] - 20), max(0, skin[2] - 20))
    d.ellipse([(head_x, head_y), (head_x + head_w, head_y + head_h)], fill=head_color)

    hair_color = (random.randint(10, 60), random.randint(10, 50), random.randint(10, 40))
    d.chord(
        [(head_x, head_y - 10), (head_x + head_w, head_y + int(head_h * 0.55))],
        180, 360, fill=hair_color,
    )

    eye_y = head_y + int(head_h * 0.42)
    eye_w = int(head_w * 0.10)
    d.ellipse([(head_x + int(head_w * 0.27), eye_y),
               (head_x + int(head_w * 0.27) + eye_w, eye_y + eye_w)], fill=(255, 255, 255))
    d.ellipse([(head_x + int(head_w * 0.63), eye_y),
               (head_x + int(head_w * 0.63) + eye_w, eye_y + eye_w)], fill=(255, 255, 255))
    pupil = (15, 15, 25)
    pw = max(2, eye_w // 2)
    d.ellipse([(head_x + int(head_w * 0.30), eye_y + 2),
               (head_x + int(head_w * 0.30) + pw, eye_y + 2 + pw)], fill=pupil)
    d.ellipse([(head_x + int(head_w * 0.66), eye_y + 2),
               (head_x + int(head_w * 0.66) + pw, eye_y + 2 + pw)], fill=pupil)

    nose_x = head_x + head_w // 2
    nose_y = eye_y + int(head_h * 0.18)
    d.line([(nose_x, nose_y), (nose_x - 5, nose_y + 25), (nose_x + 5, nose_y + 28)],
           fill=(max(0, head_color[0] - 30),) * 3, width=2)

    mouth_y = nose_y + 50
    d.arc([(head_x + int(head_w * 0.32), mouth_y - 10),
           (head_x + int(head_w * 0.68), mouth_y + 20)], 0, 180, fill=(80, 30, 30), width=3)

    return img


def render_mrz(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int):
    """Render two lines of MRZ-style monospace text at the bottom."""
    font = ImageFont.truetype(FONT_MONO, 22) if Path(FONT_MONO).exists() \
           else ImageFont.truetype(FONT_REGULAR, 22)
    line1 = "P<" + "".join(random.choices(string.ascii_uppercase + "<", k=42))
    line2 = rand_alphanum(9) + "<" + "".join(random.choices(string.ascii_uppercase + string.digits + "<", k=34))
    draw.rectangle([(x, y), (x + w, y + h)], fill=(255, 255, 255))
    draw.text((x + 10, y + 4),  line1[:44], fill=(0, 0, 0), font=font)
    draw.text((x + 10, y + 30), line2[:44], fill=(0, 0, 0), font=font)


def render_field(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str,
                 label_font: ImageFont.FreeTypeFont, value_font: ImageFont.FreeTypeFont,
                 label_color: tuple, value_color: tuple):
    draw.text((x, y), label, fill=label_color, font=label_font)
    draw.text((x, y + 18), value, fill=value_color, font=value_font)


def generate_card(template: str, scheme: dict) -> Image.Image:
    img = Image.new("RGB", (CARD_W, CARD_H), scheme["bg"])
    draw = ImageDraw.Draw(img)

    title_font  = ImageFont.truetype(FONT_BOLD,    28)
    label_font  = ImageFont.truetype(FONT_REGULAR, 13)
    value_font  = ImageFont.truetype(FONT_BOLD,    20)
    small_font  = ImageFont.truetype(FONT_REGULAR, 11)

    draw.rectangle([(0, 0), (CARD_W, 70)], fill=scheme["header"])

    if template == "national_id":
        title = "FEDERAL REPUBLIC NATIONAL IDENTITY CARD"
    elif template == "drivers_license":
        title = "REPUBLIC OF NIGERIA  -  DRIVER'S LICENCE"
    else:
        title = "PASSPORT  -  REPUBLIC OF NIGERIA"

    draw.text((20, 22), title, fill=(255, 255, 255), font=title_font)

    seal_x, seal_y = CARD_W - 60, 15
    draw.ellipse([(seal_x, seal_y), (seal_x + 40, seal_y + 40)], outline=scheme["accent"], width=3)
    draw.ellipse([(seal_x + 8, seal_y + 8), (seal_x + 32, seal_y + 32)], outline=scheme["accent"], width=2)

    photo_w, photo_h = 220, 280
    photo_x, photo_y = 30, 100
    face_seed = (
        scheme["bg"][0] - 20, scheme["bg"][1] - 15, scheme["bg"][2] - 25
    )
    face = make_face_placeholder(photo_w, photo_h, face_seed)
    img.paste(face, (photo_x, photo_y))
    draw.rectangle([(photo_x, photo_y), (photo_x + photo_w, photo_y + photo_h)],
                   outline=scheme["text"], width=2)

    first = random.choice(FIRST_NAMES)
    last  = random.choice(LAST_NAMES)
    middle = random.choice(FIRST_NAMES)
    dob = rand_date(1970, 2005)
    issue = rand_date(2018, 2024)
    expiry = rand_date(2026, 2034)
    pob = random.choice(PLACES_OF_BIRTH)
    nat = random.choice(NATIONALITIES)
    sex = random.choice(SEXES)
    id_no = rand_id_number()

    fx = photo_x + photo_w + 30
    fy = 105
    row_gap = 56

    if template == "national_id":
        fields = [
            ("SURNAME",       last),
            ("GIVEN NAMES",   f"{first} {middle}"),
            ("DATE OF BIRTH", dob),
            ("SEX",           sex),
            ("NIN",           id_no),
            ("DATE OF ISSUE", issue),
            ("EXPIRY",        expiry),
        ]
    elif template == "drivers_license":
        fields = [
            ("SURNAME",       last),
            ("FORENAMES",     f"{first} {middle}"),
            ("DATE OF BIRTH", dob),
            ("LICENCE NO.",   rand_alphanum(11)),
            ("CLASS",         random.choice(["A", "B", "C", "D", "E"])),
            ("ISSUED",        issue),
            ("EXPIRY",        expiry),
        ]
    else:
        fields = [
            ("SURNAME",        last),
            ("GIVEN NAMES",    f"{first} {middle}"),
            ("NATIONALITY",    nat),
            ("DATE OF BIRTH",  dob),
            ("PLACE OF BIRTH", pob),
            ("PASSPORT NO.",   "A" + rand_id_number(8)),
            ("DATE OF ISSUE",  issue),
            ("DATE OF EXPIRY", expiry),
        ]

    col_x = [fx, fx + 270]
    for i, (label, value) in enumerate(fields):
        col = i // 4
        row = i % 4
        x = col_x[col]
        y = fy + row * row_gap
        render_field(draw, x, y, label, value, label_font, value_font,
                     scheme["accent"], scheme["text"])

    sig_y = 410
    draw.line([(fx, sig_y), (fx + 220, sig_y)], fill=scheme["text"], width=1)
    draw.text((fx, sig_y + 4), "SIGNATURE", fill=scheme["accent"], font=small_font)

    render_mrz(draw, 20, CARD_H - 70, CARD_W - 40, 60)

    for _ in range(3):
        x1 = random.randint(0, CARD_W)
        y1 = random.randint(80, CARD_H - 80)
        x2 = x1 + random.randint(40, 120)
        y2 = y1 + random.randint(20, 60)
        draw.line([(x1, y1), (x2, y2)],
                  fill=(scheme["accent"][0], scheme["accent"][1], scheme["accent"][2]), width=1)

    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=25, help="Number of source images to generate")
    parser.add_argument("--out", type=str, default="synthetic_sources", help="Output folder")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, args.count + 1):
        template = TEMPLATES[i % len(TEMPLATES)]
        scheme = random.choice(COLOR_SCHEMES)
        card = generate_card(template, scheme)
        out_path = out_dir / f"source_{i:03d}.jpg"
        card.save(out_path, "JPEG", quality=95)

    print(f"Generated {args.count} synthetic ID images in {out_dir}/")


if __name__ == "__main__":
    main()
