from fastapi import FastAPI, HTTPException, UploadFile, File
from app.data_loader import load_data
from app.ocr import extract_text
from app.verifier import verify_user
from app.models import UserInput
from app.validators import validate_pan, validate_aadhaar
from app.ocr import extract_text
from app.document_parse import parse_document

app = FastAPI(title="KYC Verification Agent")

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

    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = extract_text(file_path)

    result = parse_document(text)

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
        "verification_result": verification_result
    }
