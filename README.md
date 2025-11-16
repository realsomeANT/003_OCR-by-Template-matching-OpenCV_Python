## OCR-by-Template-matching-OpenCV_Pyton

  Using the template matching principle has significant limitations in OCR programming, as it requires creating a template for each character to be readable. Furthermore, the font of the text to be transcribed using OCR must be the same as the font used for the template. The font size must be the same as or approximately the same width and height as the template image to be readable.
OCR Program Creation Steps
1. Template Preparation\
This is the most important step in this method. You must create a "master" or "template" for every letter and number you want to recognize (A-Z and 0-9).
- ​​Image File Creation: Create a separate image file for each character, such as A.png, B.png, C.png, ..., 0.png, 1.png, ...
- Clarity: These template images must be very clear, with a single background color (e.g., black) and a different color for the text (e.g., white).
- Fixed Size: Very important! All templates should be the same size (e.g., 30x30 pixels) for easy comparison later. You can use cv2.resize() to force the size.
2. Input Image Processing\
Once you have an image to read (e.g., test_image.png), you must prepare it for analysis.
- Read the image: Use cv2.imread() to load your image.
- Convert to grayscale: Most analyses don't require color. Use cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) to simplify processing.
- Convert to black and white. (Binarization): This is a crucial step in clearly separating characters from the background.
o Use cv2.threshold() or cv2.adaptiveThreshold() to make the image appear to have only white (characters) and black (background).
3. Character Segmentation\
Now that your image is black and white, we need to figure out where the "lumps" of white pixels (characters) are.
4. Template Matching\
This is the heart of the program. You now have a rectangular box for each character from Step 3.
- Crop
- Scale the ROI
- Compare with all templates
- Find the highest score
5. Display Results\
Once you know what character is in the box (e.g., 'C' from the highest score in Step 4),<br/><br/>

> [!WARNING]
> # Considerations and Limitations
- Font: The program will work best if the font in the desired image is very similar to the font in your template.
- Scale: If the characters in the image are very different in size or size from the template, Comparison will fail.
- Rotation: If the text is tilted, even slightly, matchTemplate may not detect it.
- Text stuck together. (Overlapping): If two characters are too close together, findContours may consider them to be a single "block," causing recognition failure.

# What to prepare:
1. Font template: 30x30 px. Any font is required, but they must be identical.\
(Focus on fonts with clear characters, especially I i L l P p S s O o 0, which have high similarity.)
- Uppercase: A-Z (26 images)
- Lowercase: a-z (26 images)
- Digits: 0-9 (10 images)
2. Test images for OCR reading must contain text using the same font as the template and must have similar font sizes for effective recognition.\
Sample text
```
A a B b C c D d E e F f G g H h I i J j K k L l M m N n
O o P p Q q R r S s T t U u V v W w X x Y y Z z
0 1 2 3 4 5 6 7 8 9 
Cat is God
Cat creates world
Humans were born from the blessing of cats.

```
