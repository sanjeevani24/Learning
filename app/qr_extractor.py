import logging
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
import cv2

logger = logging.getLogger(__name__)


def extract_qr_data(image_path):
    logger.info("Extracting QR data from %s", image_path)
    try:
        image = Image.open(image_path)
        logger.info(
            "Opened image %s size=%s mode=%s",
            image_path,
            image.size,
            image.mode,
        )

        qr_codes = decode(image)
        logger.info("Pyzbar decode returned %d QR code(s)", len(qr_codes))

        if qr_codes:
            qr_data = qr_codes[0].data.decode("utf-8")
            logger.info("Decoded QR data via pyzbar: %s", qr_data)
            return qr_data

        logger.info("Pyzbar did not find a QR code, trying OpenCV fallback")
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(image_cv)

        if data:
            logger.info("Decoded QR data via OpenCV: %s", data)
            return data

        logger.info("No QR code found in %s", image_path)
        return None
    except Exception as exc:
        logger.exception("Failed to extract QR data from %s", image_path)
        return None
