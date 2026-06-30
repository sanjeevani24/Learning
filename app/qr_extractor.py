import cv2

def extract_qr_data(image_path):

    image = cv2.imread(image_path)

    if image is None:
        return None

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.GaussianBlur(
        gray,
        (3,3),
        0
    )

    detector = cv2.QRCodeDetector()

    data, bbox, _ = detector.detectAndDecode(
        gray
    )

    print("QR DATA:", data)
    print("QR BBOX:", bbox)

    return data if data else None