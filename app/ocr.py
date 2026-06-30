import pytesseract
from PIL import Image


def extract_text(image_path):

    image = Image.open(image_path)

    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT
    )

    text = pytesseract.image_to_string(image)

    confidences = []

    for conf in data["conf"]:

        try:
            conf = float(conf)

            if conf >= 0:
                confidences.append(conf)

        except:
            pass

    ocr_confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0
    )

    return {
    "text": text,
    "ocr_confidence": round(
        ocr_confidence,
        2
    )
    }

