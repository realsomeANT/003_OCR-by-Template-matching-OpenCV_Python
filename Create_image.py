import os
from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
OUTPUT_IMAGE_PATH = "sentence_image.png"
FONT_PATH = "BKANT.TTF"  # Path to the font file
FONT_SIZE = 26
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 300
BG_COLOR = (255, 255, 255)  # White background
TEXT_COLOR = (0, 0, 0)  # Black text
LETTER_SPACING = 1  # Space between letters in pixels

# Sentence to render
SENTENCE = """\n A a B b C c D d E e F f G g    H h I i J j K k L l M m N n \nO o P p Q  q R r S s T t U u V v    W w X x Y y Z z \n 0 1 2 3 4 5 6 7 8 9   \n Cat is God   \nCat creates world\nHumans were born from the blessing of cats."""

# --- Create Image ---
def create_sentence_image():
    try:
        # Load font
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except IOError:
        print(f"Error: Font file '{FONT_PATH}' not found.")
        return

    # Create blank image
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Calculate text position
    x, y = 10, 10  # Starting position

    # Draw text with pixel spacing between letters
    for line in SENTENCE.split("\n"):
        for char in line:
            if char != " ":  # Skip spaces for spacing consistency
                draw.text((x, y), char, font=font, fill=TEXT_COLOR)
            bbox = font.getbbox(char)  # Get bounding box of the character
            x += (bbox[2] - bbox[0]) + LETTER_SPACING
        x = 10  # Reset x for the next line
        y += (font.getbbox("Hg")[3] - font.getbbox("Hg")[1]) + 10  # Move to the next line with line spacing

    # Save image
    img.save(OUTPUT_IMAGE_PATH)
    print(f"Image saved to {OUTPUT_IMAGE_PATH}")

if __name__ == "__main__":
    create_sentence_image()
