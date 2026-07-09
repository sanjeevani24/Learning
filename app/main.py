import logging
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.data_loader import get_user
from app.ocr import extract_text
from app.verifier import verify_user
from app.models import UserInput
from app.validators import validate_pan, validate_aadhaar
from app.document_parse import parse_document
from app.image_checks import analyze_image
from app.trust_score import calculate_trust_score
from app.qr_extractor import extract_qr_data
from app.secure_qr_decoder import decode_secure_qr
from app.comparator import compare_ocr_qr


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = FastAPI(title="DOC Verification Agent")

# ── CORS ──────────────────────────────────────────────────────────────────
# Allow the Vite dev server and any localhost origin to call the API.
# In production, replace "*" with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "KYC Agent Running"}

@app.get("/user/{aadhaar}")
def user_details(aadhaar: str):

    user = get_user(aadhaar)

    if user is None:
        return {
            "status": "User not found"
        }

    return user

@app.post("/verify")
def verify(user: UserInput):

    # Aadhaar Validation
    if not validate_aadhaar(user.aadhaar_number):
        raise HTTPException(
            status_code=400,
            detail="Invalid Aadhaar format. Aadhaar must be a 12-digit number."
        )

    # PAN Validation
    if not validate_pan(user.pan_card_number):
        raise HTTPException(
            status_code=400,
            detail="Invalid PAN format. Example: ABCDE1234F"
        )

    # Only if formats are valid
    return verify_user(
    user.model_dump()
    )

@app.post("/extract-document")
async def extract_document(
    file: UploadFile = File(...)
):

    

    safe_filename = os.path.basename(file.filename)
    file_path = f"temp_{safe_filename}"

    logger.info("Received document upload: filename=%s file_path=%s", file.filename, file_path)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    qr_info = extract_qr_data(file_path)
    qr_data = None

    if qr_info["payload"]:
        qr_data = decode_secure_qr(qr_info["payload"])

        if qr_data is None:
         raise HTTPException(
            status_code=400,
            detail={
            "status": "QR_NOT_READABLE",
            "message": "Unable to read the Aadhaar Secure QR Code. Please upload a clearer image with the QR code fully visible."
        }
    )

    print(qr_data)

    ocr_result = extract_text(file_path)

    text = ocr_result["text"]
    logger.info("Extracted OCR text length=%d", len(ocr_result) if text else 0)

    ocr_confidence = ocr_result["ocr_confidence"]

    result = parse_document(text)
    logger.info("Parsed document result: %s", result)

    qr_result = extract_qr_data(file_path)
    qr_payload = None
    qr_payload_length = None
    qr_payload_preview = None
    qr_debug = None

    if isinstance(qr_result, dict):
        qr_payload = qr_result.get("payload")
        qr_payload_length = qr_result.get("payload_length")
        qr_debug = qr_result.get("debug")
    else:
        qr_payload = qr_result
        if isinstance(qr_payload, str):
            qr_payload_length = len(qr_payload)

    if isinstance(qr_payload, (bytes, bytearray)):
        qr_payload_preview = qr_payload[:40].hex()
    elif isinstance(qr_payload, str):
        qr_payload_preview = qr_payload[:40]

    logger.info("QR extraction returned: %s", qr_payload)
    logger.info("QR debug info: %s", qr_debug)

    image_report = analyze_image(
    file_path,
    text,
    result["document_type"]
    )
    result = parse_document(text)
    logger.info("Parsed document result: %s", result)

        # Compare OCR data with Secure QR data
    comparison_result = None

    if qr_data:
        comparison_result = compare_ocr_qr(result, qr_data)

    image_report = analyze_image(
    file_path,
    text,
    result["document_type"]
    )

    # Validate extracted Aadhaar
    if (
        result.get("document_type") == "aadhaar"
        and result.get("aadhaar_number")
    ):

        if not validate_aadhaar(result["aadhaar_number"]):
            raise HTTPException(
                status_code=400,
                detail="Extracted Aadhaar number has invalid format"
            )

    # Validate extracted PAN
    if (
        result.get("document_type") == "pan"
        and result.get("pan_card_number")
    ):

        if not validate_pan(result["pan_card_number"]):
            raise HTTPException(
                status_code=400,
                detail="Extracted PAN number has invalid format"
            )
        
        print(result)

    verification_result = verify_user(result)

    trust_score = calculate_trust_score(
    ocr_confidence,
    image_report
    )

    risk_flags = []

    if image_report["is_blurry"]:
        risk_flags.append("Blurry document")

    if ocr_confidence < 70:
        risk_flags.append("Low OCR confidence")

    if not image_report["good_resolution"]:
        risk_flags.append("Low resolution image")

    return {
        "raw_text": text,
        "ocr_confidence": ocr_confidence,
        "image_quality": image_report,
        "trust_score": trust_score,
        "qr_data": qr_data,
        "comparison": comparison_result,   # <-- Add this
        "risk_flags": risk_flags,
        "parsed_data": result,
        "payload_length": qr_payload_length,
        "payload_preview": qr_payload_preview,
        "verification_result": verification_result
    }