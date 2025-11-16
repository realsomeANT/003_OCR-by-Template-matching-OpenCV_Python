import os
import string
from PIL import Image, ImageDraw, ImageFont

# --- 1. การตั้งค่า (Configuration) ---

IMG_WIDTH = 30
IMG_HEIGHT = 30
OUTPUT_DIR_UPPER = "Uppercase_templates"
OUTPUT_DIR_LOWER = "Lowercase_templates"
OUTPUT_DIR_DIGITS = "Digits_templates"
BG_COLOR = (255, 255, 255) # สีขาว
TEXT_COLOR = (0, 0, 0)      # สีดำ
FONT_SIZE = 50

# --- 2. ค้นหาตำแหน่งฟอนต์ (สำหรับ Windows โดยเฉพาะ) ---

# เราจะใช้ Environment Variable 'WINDIR' (ซึ่งปกติคือ C:\Windows)
# เพื่อสร้าง path ไปยังโฟลเดอร์ Fonts
font_path = ""
windir = os.environ.get('WINDIR') # ดึงค่า (เช่น C:\Windows)

if windir and os.path.exists(windir):
    # สร้าง path ที่ถูกต้องโดยอัตโนมัติ (เช่น C:\Windows\Fonts\calibri.ttf)
    font_path = os.path.join(windir, 'Fonts', 'BKANT.TTF')
else:
    # กรณีฉุกเฉิน หากหา WINDIR ไม่เจอ
    print("ไม่พบตัวแปร WINDIR ของระบบ, ใช้ตำแหน่งมาตรฐาน C:/Windows/Fonts/THSarabunNew.ttf")
    font_path = "C:/Windows/Fonts/Calibri.ttf"

print(f"กำลังใช้ฟอนต์จาก: {font_path}")

# --- 3. ตรวจสอบฟอนต์และสร้างโฟลเดอร์ ---

custom = input("หากต้องการระบุฟอนต์เอง ให้พิมพ์ path ไปยังไฟล์ .ttf แล้วกด Enter (หรือเว้นว่างเพื่อใช้ค่าเดิม): ").strip()
if custom:
    font_path = custom

try:
    # โหลดฟอนต์
    font = ImageFont.truetype(font_path, FONT_SIZE)
except IOError:
    print(f"!!! ข้อผิดพลาด: ไม่พบไฟล์ฟอนต์ที่ '{font_path}'")
    print("โปรดตรวจสอบ path ฟอนต์หรือคัดลอกไฟล์ .ttf มาวาง และลองใหม่อีกครั้ง")
    exit() # จบการทำงานถ้าไม่เจอฟอนต์

# สร้างโฟลเดอร์สำหรับเก็บผลลัพธ์ถ้ายังไม่มี
os.makedirs(OUTPUT_DIR_UPPER, exist_ok=True)
os.makedirs(OUTPUT_DIR_LOWER, exist_ok=True)
os.makedirs(OUTPUT_DIR_DIGITS, exist_ok=True)

print("กำลังสร้าง template... บันทึกลงโฟลเดอร์ตามประเภทตัวอักษร")

# --- 4. เลือกประเภทตัวอักษร ---
print("เลือกประเภทตัวอักษรที่ต้องการสร้าง:")
print("1: ตัวพิมพ์ใหญ่ (A-Z)")
print("2: ตัวพิมพ์เล็ก (a-z)")
print("3: ตัวเลข (0-9)")
print("4: ตัวพิมพ์ใหญ่และพิมพ์เล็ก (A-Z, a-z)")
print("5: ทั้งหมด (A-Z, a-z, 0-9)")
print("6: ระบุเอง (พิมพ์ตัวอักษรที่ต้องการ เช่น ABCabc123)")

choice = input("กรุณาเลือก (1/2/3/4/5): ").strip()

if choice == "1":
    characters = string.ascii_uppercase
elif choice == "2":
    characters = string.ascii_lowercase
elif choice == "3":
    characters = string.digits
elif choice == "4":
    characters = string.ascii_letters
elif choice == "5":
    characters = string.ascii_letters + string.digits
elif choice == "6":
    custom_chars = input("พิมพ์ตัวอักษรที่ต้องการสร้าง (เช่น ABCabc123 หรือ ใส่คั่นด้วยช่องว่าง/คอมม่า): ").strip()
    # ลบช่องว่างและคอมม่า ถ้าว่างให้ fallback เป็นค่าเริ่มต้นทั้งหมด
    if custom_chars:
        # Remove common separators (spaces, commas)
        cleaned = custom_chars.replace(',', '').replace(' ', '')
        if cleaned:
            characters = cleaned
        else:
            print("ไม่พบตัวอักษรที่ถูกต้องในอินพุต, ใช้ค่าเริ่มต้นทั้งหมด")
            characters = string.ascii_letters + string.digits
    else:
        print("ไม่ได้ป้อนตัวอักษร, ใช้ค่าเริ่มต้นทั้งหมด")
        characters = string.ascii_letters + string.digits
else:
    print("ตัวเลือกไม่ถูกต้อง! ใช้ค่าเริ่มต้นคือทั้งหมด (A-Z, a-z, 0-9)")
    characters = string.ascii_letters + string.digits

# --- 5. วนลูปสร้างตัวอักษร ---

def render_and_save(char, out_dir):
    # Sanitize filename: keep alnum as-is, otherwise use Unicode codepoint
    if char.isalnum():
        filename = f"{char}.png"
    else:
        filename = f"u{ord(char):04X}.png"
    filepath = os.path.join(out_dir, filename)

    # Padding requested by user: 1 px
    
    padding = 0

    # Render glyph on a large temporary grayscale canvas to get clean mask
    # Choose a sufficiently large size to preserve detail
    large_canvas = 512

    # Try to create a large font; fall back to decreasing sizes if necessary
    large_font_size = min(large_canvas - 4, 512)
    tmp_font = None
    while large_font_size > 8:
        try:
            tmp_font = ImageFont.truetype(font_path, large_font_size)
            break
        except Exception:
            large_font_size = large_font_size // 2

    if tmp_font is None:
        # Fallback: use the previously loaded font (smaller)
        tmp_font = font

    mask_img = Image.new('L', (large_canvas, large_canvas), 0)
    draw_mask = ImageDraw.Draw(mask_img)
    # Draw the glyph white on black background, centered in the large canvas
    draw_mask.text((large_canvas / 2, large_canvas / 2), char, font=tmp_font, fill=255, anchor='mm')

    # Get bounding box of the glyph mask
    bbox = mask_img.getbbox()
    if not bbox:
        # Empty glyph? create a blank 30x30 image
        out = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), BG_COLOR)
        out.save(filepath)
        return

    glyph = mask_img.crop(bbox)
    gw, gh = glyph.size

    # Compute scale to fit target minus padding, preserving aspect ratio
    target_w = IMG_WIDTH - 2 * padding
    target_h = IMG_HEIGHT - 2 * padding
    scale = min(target_w / gw, target_h / gh)
    if scale <= 0:
        scale = 1.0

    new_w = max(1, int(round(gw * scale)))
    new_h = max(1, int(round(gh * scale)))

    # Resize glyph mask with high-quality resampling
    glyph_resized = glyph.resize((new_w, new_h), resample=Image.LANCZOS)

    # Prepare final RGB image and paste the glyph (using mask) centered
    out = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), BG_COLOR)
    # Create a colored glyph image (black text) same size as glyph_resized
    colored = Image.new('RGB', (new_w, new_h), TEXT_COLOR)
    # Compute top-left coordinate to center the glyph
    left = (IMG_WIDTH - new_w) // 2
    top = (IMG_HEIGHT - new_h) // 2
    out.paste(colored, (left, top), glyph_resized)

    out.save(filepath)

for char in characters:
    if char.isdigit():
        render_and_save(char, OUTPUT_DIR_DIGITS)
    elif char.isalpha() and char.isupper():
        render_and_save(char, OUTPUT_DIR_UPPER)
    elif char.isalpha() and char.islower():
        render_and_save(char, OUTPUT_DIR_LOWER)
    else:
        render_and_save(char, OUTPUT_DIR_DIGITS)

print(f"สร้าง template ตัวอักษรเสร็จสิ้น! (ทั้งหมด {len(characters)} ไฟล์)")