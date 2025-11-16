from PIL import Image

def invert_black_white(image_path, output_path):
    # Open the image
    image = Image.open(image_path).convert("L")  # Convert to grayscale

    # Invert the colors: white (255) -> black (0), black (0) -> white (255)
    inverted_image = image.point(lambda p: 255 - p)

    # Save the output image
    inverted_image.save(output_path)

# Example usage
if __name__ == "__main__":
    input_image_path = "bad_roi_resized_1763240029.png"  # Replace with your input image path
    output_image_path = "p.png"  # Replace with your desired output path
    invert_black_white(input_image_path, output_image_path)
    print("Image processing complete. Saved to", output_image_path)