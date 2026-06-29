import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(image_path):

    image = Image.open(image_path)

    # Return full extracted text as a single string so downstream
    # parsing functions receive a string (not a dict).
    try:
        text = pytesseract.image_to_string(image)
    except Exception:
        # Fallback: if image_to_string fails, try extracting data dict
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        text = " ".join([t for t in data.get("text", []) if t])

    return text