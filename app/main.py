import logging
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.data_loader import get_user
from app.ocr import extract_text
from app.verifier import verify_user
from app.models import UserInput
from app.validators import validate_pan, validate_aadhaar
from app.document_parse import parse_document, extract_aadhaar_fields, extract_pan_fields
from app.image_checks import analyze_image
from app.trust_score import calculate_trust_score
from app.qr_extractor import extract_qr_data
from app.secure_qr_decoder import decode_secure_qr
from app.comparator import compare_ocr_qr
from app.identity_comparator import compare_identity
import json

from app.address_proof_service import parse_address_proof
from app.address_proof_comparator import compare_address_proof
from fastapi import Form


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
    aadhaar: UploadFile = File(...),
    pan: UploadFile = File(...)
):

    aadhaar_path = f"temp_{os.path.basename(aadhaar.filename)}"

    pan_path = f"temp_{os.path.basename(pan.filename)}"


    with open(aadhaar_path, "wb") as f:
        f.write(await aadhaar.read())

    with open(pan_path, "wb") as f:
        f.write(await pan.read())
    # ---------------- OCR ----------------

    aadhaar_ocr = extract_text(aadhaar_path)

    pan_ocr = extract_text(pan_path)
    # Use the OCR results from both documents
    aadhaar_text = aadhaar_ocr["text"]
    pan_text = pan_ocr["text"]
    text = "\n".join(filter(None, [aadhaar_text, pan_text]))
    file_path = aadhaar_path
    ocr_confidence = (aadhaar_ocr["ocr_confidence"] + pan_ocr["ocr_confidence"]) / 2

    logger.info("Extracted OCR text length=%d", len(text) if text else 0)

    # ---------------- Parse Document ----------------

    aadhaar_result = parse_document(aadhaar_ocr["text"])
    if aadhaar_result.get("document_type") != "aadhaar":
        regex_data = extract_aadhaar_fields(aadhaar_ocr["text"])
        from app.llm_extractor import extract_person_details
        llm_data = extract_person_details(aadhaar_ocr["text"])
        aadhaar_result = {
            "document_type": "aadhaar",
            **regex_data,
            **llm_data
        }

    pan_result = parse_document(pan_ocr["text"])
    if pan_result.get("document_type") not in ["pan", "pan card"]:
        regex_data = extract_pan_fields(pan_ocr["text"])
        from app.llm_extractor import extract_person_details
        llm_data = extract_person_details(pan_ocr["text"])
        if not regex_data.get("date_of_birth"):
            regex_data["date_of_birth"] = llm_data.get("date_of_birth")
        pan_result = {
            "document_type": "pan card",
            **regex_data,
            **llm_data
        }

    identity_result = compare_identity(
        aadhaar_result.get("full_name"),
        pan_result.get("full_name"),
        aadhaar_result.get("date_of_birth"),
        pan_result.get("date_of_birth")
    )

    logger.info("Parsed Aadhaar: %s", aadhaar_result)
    logger.info("Parsed PAN: %s", pan_result)

    # ---------------- Image Quality ----------------

    aadhaar_image_report = analyze_image(
        aadhaar_path,
        aadhaar_text,
        "aadhaar"
    )

    pan_image_report = analyze_image(
        pan_path,
        pan_text,
        "pan"
    )

    # ---------------- QR Extraction ----------------

    qr_result = extract_qr_data(aadhaar_path)

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

    # ---------------- Secure QR Decode ----------------

    qr_data = None

    if qr_payload:
        qr_data = decode_secure_qr(qr_payload)

    # QR couldn't be decoded
    # Ask frontend for Electricity Bill

    if qr_data is None:
        aadhaar_result["pan_card_number"] = pan_result.get("pan_card_number")
        return {
            "status": "NEED_ADDRESS_PROOF",
            "message": "Secure QR could not be decoded. Please upload an Electricity Bill.",
            "aadhaar_data": aadhaar_result,
            "pan_data": pan_result,
            "identity_comparison": identity_result,
            "aadhaar_ocr_confidence": aadhaar_ocr["ocr_confidence"],
            "pan_ocr_confidence": pan_ocr["ocr_confidence"],
            "aadhaar_image_quality": aadhaar_image_report,
            "pan_image_quality": pan_image_report,
            "ocr_confidence": ocr_confidence,
            "image_quality": aadhaar_image_report,
            "parsed_data": aadhaar_result
        }

    # ---------------- OCR vs QR ----------------

    comparison_result = compare_ocr_qr(
        aadhaar_result,
        qr_data
    )

    # ---------------- Validate Aadhaar ----------------

    if aadhaar_result.get("aadhaar_number"):
        if not validate_aadhaar(aadhaar_result["aadhaar_number"]):
            raise HTTPException(
                status_code=400,
                detail="Extracted Aadhaar number has invalid format"
            )

    # ---------------- Validate PAN ----------------

    if pan_result.get("pan_card_number"):
        if not validate_pan(pan_result["pan_card_number"]):
            raise HTTPException(
                status_code=400,
                detail="Extracted PAN number has invalid format"
            )

    # ---------------- Database Verification ----------------

    aadhaar_result["pan_card_number"] = pan_result.get("pan_card_number")

    combined_data = {
        "full_name": aadhaar_result.get("full_name"),
        "date_of_birth": aadhaar_result.get("date_of_birth"),
        "aadhaar_number": aadhaar_result.get("aadhaar_number"),
        "pan_card_number": pan_result.get("pan_card_number")
    }

    verification_result = verify_user(combined_data)

    # ---------------- Trust Score ----------------

    trust_score = calculate_trust_score(
        ocr_confidence,
        aadhaar_image_report
    )

    # ---------------- Risk Flags ----------------

    risk_flags = []

    if aadhaar_image_report.get("is_blurry"):
        risk_flags.append("Blurry document")

    if pan_image_report.get("is_blurry"):
        risk_flags.append("Blurry PAN document")

    if ocr_confidence < 70:
        risk_flags.append("Low OCR confidence")

    if not aadhaar_image_report.get("good_resolution"):
        risk_flags.append("Low resolution image")

    if not pan_image_report.get("good_resolution"):
        risk_flags.append("Low PAN resolution image")

    # ---------------- Final Response ----------------

    return {
        "raw_text": text,
        "ocr_confidence": ocr_confidence,
        "image_quality": aadhaar_image_report,
        "aadhaar_ocr_confidence": aadhaar_ocr["ocr_confidence"],
        "pan_ocr_confidence": pan_ocr["ocr_confidence"],
        "aadhaar_image_quality": aadhaar_image_report,
        "pan_image_quality": pan_image_report,
        "trust_score": trust_score,
        "qr_data": qr_data,
        "comparison": comparison_result,
        "identity_comparison": identity_result,
        "risk_flags": risk_flags,
        "parsed_data": aadhaar_result,
        "pan_data": pan_result,
        "payload_length": qr_payload_length,
        "payload_preview": qr_payload_preview,
        "verification_result": verification_result
    }

@app.post("/verify-address-proof")
async def verify_address_proof(
    file: UploadFile = File(...),
    aadhaar_data: str = Form(...)
):

    # ---------------- Save Uploaded Bill ----------------

    safe_filename = os.path.basename(file.filename)
    file_path = f"temp_{safe_filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # ---------------- Convert Aadhaar JSON ----------------

    aadhaar_data = json.loads(aadhaar_data)

    # ---------------- OCR + Parse Electricity Bill ----------------

    bill_result = parse_address_proof(file_path)

    bill_data = bill_result["parsed_data"]

    raw_text = bill_result["raw_text"]

    ocr_confidence = bill_result["ocr_confidence"]

    # ---------------- Compare Aadhaar vs Bill ----------------

    comparison_result = compare_address_proof(
        aadhaar_data,
        bill_data
    )

   
    # ---------------- Analyze Bill Image ----------------

    image_report = analyze_image(
        file_path,
        raw_text,
        "electricity_bill"
    )

    # ---------------- Database Verification ----------------

    verification_result = verify_user(aadhaar_data)

    # ---------------- Trust Score ----------------

    trust_score = calculate_trust_score(
        ocr_confidence,
        image_report
    )

    # ---------------- Risk Flags ----------------

    risk_flags = []

    if image_report["is_blurry"]:
        risk_flags.append("Blurry Electricity Bill")

    if ocr_confidence < 70:
        risk_flags.append("Low OCR Confidence")

    if not image_report["good_resolution"]:
        risk_flags.append("Low Resolution")

    # ---------------- Final Response ----------------  

    return {

    "status": "VERIFIED_WITH_ADDRESS_PROOF",

    "raw_text": raw_text,

    "ocr_confidence": ocr_confidence,

    "image_quality": image_report,

    "trust_score": trust_score,

    "comparison": comparison_result,

    "risk_flags": risk_flags,

    "bill_data": bill_data,

    "verification_result": verification_result
}