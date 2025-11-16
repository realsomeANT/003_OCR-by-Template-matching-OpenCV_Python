import cv2
import numpy as np
import os
import string
import argparse
import time

# --- การตั้งค่า ---
# ถ้ามีเทมเพลตแยกโฟลเดอร์ตามชนิด ให้ใส่ชื่อโฟลเดอร์เหล่านั้นไว้ในลิสต์นี้
TEMPLATE_DIRS = ["Digits_templates", "Lowercase_templates", "Uppercase_templates"]
TEST_IMAGE_PATH = "sentence_image.png"  # สร้างไฟล์นี้เพื่อทดสอบ
TEMPLATE_WIDTH = 30
TEMPLATE_HEIGHT = 30
MATCH_THRESHOLD = 0.6  # ค่าความมั่นใจ (0.0 - 1.0) ยิ่งสูงยิ่งเข้มงวด — ปรับลดเล็กน้อยเมื่อใช้คะแนนเฉลี่ย

# ---- Command line options ----
parser = argparse.ArgumentParser(description="Simple template-matching OCR")
parser.add_argument('--no-gui', action='store_true', help='Do not show OpenCV windows')
parser.add_argument('--output-file', '-o', help='Write OCR result to a file')
args = parser.parse_args()

def load_templates(template_dirs):
    """โหลดเทมเพลตทั้งหมดจากโฟลเดอร์/หลายโฟลเดอร์มาเก็บใน Dictionary

    template_dirs can be a string (single folder) or a list of folders.
    Files with extensions .png/.jpg/.jpeg/.bmp/.tif/.tiff will be loaded.
    Each template is converted to binary (inverted so foreground = 255) and
    resized to (TEMPLATE_WIDTH, TEMPLATE_HEIGHT) for matching.
    """
    templates = {}

    # allow passing a single folder as string
    if isinstance(template_dirs, str):
        template_dirs = [template_dirs]

    print("กำลังโหลดเทมเพลต...")
    for tdir in template_dirs:
        if not os.path.isdir(tdir):
            print(f"คำเตือน: ไม่พบโฟลเดอร์เทมเพลตที่ {tdir}")
            continue

        for fname in os.listdir(tdir):
            name, ext = os.path.splitext(fname)
            if ext.lower() not in ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'):
                continue

            path = os.path.join(tdir, fname)
            template_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if template_img is None:
                print(f"คำเตือน: ไม่สามารถโหลดเทมเพลตที่ {path}")
                continue

            # Normalize: binarize and invert so foreground is white (255) like ROI
            try:
                _, template_bin = cv2.threshold(template_img, 0, 255,
                                                cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
            except Exception:
                # fallback: simple threshold
                _, template_bin = cv2.threshold(template_img, 127, 255, cv2.THRESH_BINARY)

            # Resize to match matcher size
            try:
                template_resized = cv2.resize(template_bin, (TEMPLATE_WIDTH, TEMPLATE_HEIGHT))
            except Exception as e:
                print(f"คำเตือน: ไม่สามารถปรับขนาดเทมเพลต {path}: {e}")
                continue

            templates[name] = template_resized

    print(f"โหลดเทมเพลตสำเร็จ {len(templates)} ตัว จาก {template_dirs}")
    return templates

def sort_contours(contours):
    """
    จัดเรียง Contours แบบรองรับหลายบรรทัด: แบ่งเป็น "rows" ตามค่า y-center
    แล้วเรียงแต่ละแถวจากซ้ายไปขวา
    """
    if not contours:
        return contours

    # เก็บ bounding boxes และ y-centers
    boxes = [cv2.boundingRect(c) for c in contours]
    centers_y = [y + h / 2 for (x, y, w, h) in boxes]

    # จัดกลุ่มเป็นแถว โดยใช้ tolerance เท่ากับค่าเฉลี่ยความสูง
    avg_h = np.mean([h for (x, y, w, h) in boxes]) if boxes else 0
    rows = []  # each row is list of (contour, box)

    for c, b, cy in zip(contours, boxes, centers_y):
        placed = False
        for row in rows:
            # compare with first box in the row
            _, ry, _, rh = row[0][1]
            if abs(cy - (ry + rh / 2)) <= max(10, avg_h * 0.5):
                row.append((c, b))
                placed = True
                break
        if not placed:
            rows.append([(c, b)])

    # sort rows by y, then within each row sort by x
    rows_sorted = sorted(rows, key=lambda r: r[0][1][1])
    sorted_contours = []
    for row in rows_sorted:
        row_sorted = sorted(row, key=lambda item: item[1][0])
        sorted_contours.extend([item[0] for item in row_sorted])

    return sorted_contours


def prepare_roi_for_matching(roi, width=TEMPLATE_WIDTH, height=TEMPLATE_HEIGHT):
    """Resize ROI to template size while preserving aspect ratio by padding.

    Input roi should be binary with foreground=255.
    """
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((height, width), dtype=np.uint8)

    # find bounding non-zero area to crop tight (optional)
    ys, xs = np.where(roi > 0)
    if len(xs) and len(ys):
        x1, x2 = xs.min(), xs.max()
        y1, y2 = ys.min(), ys.max()
        roi = roi[y1:y2+1, x1:x2+1]
        h, w = roi.shape[:2]

    # compute scaling while maintaining aspect ratio
    scale = min(width / w, height / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(roi, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # create padded image
    canvas = np.zeros((height, width), dtype=np.uint8)
    x_off = (width - new_w) // 2
    y_off = (height - new_h) // 2
    canvas[y_off:y_off+new_h, x_off:x_off+new_w] = resized

    return canvas


def group_chars_into_lines(detected_list):
    """Group detected characters into rows based on y-center (baseline) and
    sort each row left-to-right.

    detected_list: list of tuples (x, y, w, h, char)
    Returns list of strings (one string per row), ordered top-to-bottom.
    """
    if not detected_list:
        return []

    # compute y-centers and average height to choose a tolerance
    centers_y = [y + h / 2 for (x, y, w, h, c) in detected_list]
    avg_h = np.mean([h for (x, y, w, h, c) in detected_list]) if detected_list else 0

    rows = []  # each row is list of items (x,y,w,h,char)
    for item, cy in zip(detected_list, centers_y):
        placed = False
        for row in rows:
            ry = row[0][1]
            rh = row[0][3]
            row_cy = ry + rh / 2
            # tolerance: either a few pixels or a fraction of avg height
            if abs(cy - row_cy) <= max(10, avg_h * 0.5):
                row.append(item)
                placed = True
                break
        if not placed:
            rows.append([item])

    # sort rows by their y coordinate (top to bottom)
    rows_sorted = sorted(rows, key=lambda r: r[0][1])

    # within each row, sort by x (left to right) and join chars
    final_rows = []
    for row in rows_sorted:
        row_sorted = sorted(row, key=lambda it: it[0])
        final_rows.append(''.join([it[4] for it in row_sorted]))

    return final_rows

# --- 1. โหลดเทมเพลต (ทำครั้งเดียว) ---
templates = load_templates(TEMPLATE_DIRS)

# --- 2. โหลดและประมวลผลภาพทดสอบ ---
image = cv2.imread(TEST_IMAGE_PATH)
if image is None:
    print(f"Error: ไม่พบไฟล์ทดสอบ '{TEST_IMAGE_PATH}'")
    print("กรุณาสร้างไฟล์ภาพ ที่มีข้อความด้วยฟอนต์ที่ตรงกับเทมเพลตก่อน")
    exit()

# สร้างภาพสำหรับวาดผลลัพธ์
output_image = image.copy()

# แปลงเป็น Grayscale และ Binarization (ขาว-ดำ)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# ใช้ THRESH_BINARY_INV เพื่อให้ตัวอักษรเป็น "สีขาว" (255)
# และพื้นหลังเป็น "สีดำ" (0) เหมือนกับเทมเพลต
# THRESH_OTSU จะหาค่า threshold ที่เหมาะสมให้เราอัตโนมัติ
thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

# --- 3. ค้นหาตัวอักษร (Segmentation) ---
# ค้นหา Contours (รูปร่างของตัวอักษร)
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# จัดเรียง contours จากซ้ายไปขวา
if contours:
    contours = sort_contours(contours)

print(f"พบ {len(contours)} contours (ตัวอักษรที่อาจเป็นไปได้)")

detected_string = ""
detected_chars_with_pos = []
bad_roi_saved = False  # save only the first failing ROI for debugging

# --- 4. วนลูปเพื่อเปรียบเทียบ (Matching) ---
for cnt in contours:
    # หากรอบสี่เหลี่ยมของตัวอักษร
    x, y, w, h = cv2.boundingRect(cnt)

    # กรอง contours ที่เล็กเกินไป (อาจเป็นจุดรบกวน)
    if w < 2 or h < 10:
        continue

    # ตัดภาพเฉพาะส่วนของตัวอักษร (Region of Interest - ROI)
    roi = thresh[y:y+h, x:x+w]
    
    # เตรียม ROI โดยรักษาสัดส่วนและเติมขอบก่อน matching
    resized_roi = prepare_roi_for_matching(roi, TEMPLATE_WIDTH, TEMPLATE_HEIGHT)

    # เตรียมตัวแปรสำหรับเก็บค่าที่ Match ที่สุด
    best_match_score = -1
    best_match_char = "?"

    # --- 5. หัวใจหลัก: Template Matching ---
    # วนลูปเปรียบเทียบ ROI กับเทมเพลตทุกตัว
    for (char, template_img) in templates.items():
        # Use two match methods and average for robustness
        try:
            res1 = cv2.matchTemplate(resized_roi, template_img, cv2.TM_CCOEFF_NORMED)
            _, max1, _, _ = cv2.minMaxLoc(res1)
        except Exception:
            max1 = -1

        try:
            res2 = cv2.matchTemplate(resized_roi, template_img, cv2.TM_CCORR_NORMED)
            _, max2, _, _ = cv2.minMaxLoc(res2)
        except Exception:
            max2 = -1

        # combine scores (simple average) — both are in similar normalized ranges
        score = (max1 + max2) / 2.0

        if score > best_match_score:
            best_match_score = score
            best_match_char = char

    # --- 6. แสดงผลลัพธ์ ---
    # ถ้าคะแนนดีกว่าเกณฑ์ที่เราตั้งไว้ (เช่น 0.7)
    if best_match_score > MATCH_THRESHOLD:
        # เก็บผลลัพธ์ (พร้อมตำแหน่ง x, y, w, h, char) — เพื่อให้สามารถจัดกลุ่มตาม baseline ได้
        detected_chars_with_pos.append((x, y, w, h, best_match_char))
        
        # วาดกรอบและข้อความลงบนภาพ Output
        cv2.rectangle(output_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(output_image, best_match_char, (x, y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 2)
    else:
        # ถ้าคะแนนต่ำไป ให้แสดงเป็น '?'
        cv2.rectangle(output_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(output_image, '', (x, y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        # บันทึกภาพ ROI ที่จับคู่ไม่ผ่านครั้งแรกเพื่อตรวจสอบ (ต้นฉบับ + resized + template)
        if not bad_roi_saved:
            try:
                ts = int(time.time())
                fname_roi = f"bad_roi_{ts}.png"
                fname_resized = f"bad_roi_resized_{ts}.png"
                cv2.imwrite(fname_roi, roi)
                cv2.imwrite(fname_resized, resized_roi)
                # ถ้ามี template ที่ได้คะแนนสูงสุด ให้บันทึกเทมเพลตด้วย
                if best_match_char in templates:
                    try:
                        cv2.imwrite(f"bad_roi_template_{ts}.png", templates[best_match_char])
                    except Exception:
                        pass

                print(f"บันทึก ROI ที่จับคู่ไม่ผ่านไว้ที่: {fname_roi}, {fname_resized}")
                print(f"bbox=(x,y,w,h)={(x,y,w,h)} score={best_match_score:.3f} best_match_char={best_match_char}")
                bad_roi_saved = True
            except Exception as e:
                print(f"ไม่สามารถบันทึก ROI ผิดพลาด: {e}")


# จัดกลุ่มตัวอักษรตาม baseline (แถว) และเรียงภายในแถวจากซ้ายไปขวา
rows = group_chars_into_lines(detected_chars_with_pos)

print("-" * 30)
print("Detected (grouped by baseline):")
for r in rows:
    print(r)
print("-" * 30)

# ผลลัพธ์แบบเรียบ (ต่อกันเป็นสตริงเดียว) สำหรับการส่งออกหรือการใช้งานต่อ
final_string = ''.join(rows)

# ส่งออกแบบเรียบตรงไปยัง stdout (เหมาะสำหรับการจับผลลัพธ์จาก terminal)
print(final_string)

# ถ้าผู้ใช้ต้องการบันทึกผลลงไฟล์
if args.output_file:
    try:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(final_string)
        print(f"บันทึกผล OCR ลงไฟล์: {args.output_file}")
    except Exception as e:
        print(f"ไม่สามารถเขียนไฟล์ {args.output_file}: {e}")

# แสดงผลลัพธ์ (ถ้าไม่ได้ใช้ --no-gui)
if not args.no_gui:
    cv2.imshow("Test Image (Original)", image)
    cv2.imshow("Threshold (Processed)", thresh)
    cv2.imshow("OCR Result (Output)", output_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    # ผู้ใช้สั่งให้ไม่เปิดหน้าต่าง GUI
    pass