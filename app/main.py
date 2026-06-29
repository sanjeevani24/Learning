import logging
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from app.data_loader import load_data
from app.ocr import extract_text
from app.verifier import verify_user
from app.models import UserInput
from app.validators import validate_pan, validate_aadhaar
from app.document_parse import parse_document
from app.qr_extractor import extract_qr_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = FastAPI(title="DOC Verification Agent")

# Load dataset once
df = load_data()

@app.get("/")
def home():
    return {"message": "KYC Agent Running"}

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
    return verify_user(df, user.model_dump())


@app.post("/extract-document")
async def extract_document(
    file: UploadFile = File(...)
):

    

    safe_filename = os.path.basename(file.filename)
    file_path = f"temp_{safe_filename}"

    logger.info("Received document upload: filename=%s file_path=%s", file.filename, file_path)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = extract_text(file_path)
    logger.info("Extracted OCR text length=%d", len(text) if text else 0)

    result = parse_document(text)
    logger.info("Parsed document result: %s", result)

    qr_result = extract_qr_data(file_path)
    qr_data = qr_result.get("data") if isinstance(qr_result, dict) else qr_result
    qr_debug = qr_result.get("debug") if isinstance(qr_result, dict) else None
    logger.info("QR extraction returned: %s", qr_data)
    logger.info("QR debug info: %s", qr_debug)

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

    verification_result = verify_user(df, result)

    return {
        "raw_text": text,
        "parsed_data": result,
        "qr_data": qr_data,
        "qr_debug": qr_debug,
        "verification_result": verification_result,
    }