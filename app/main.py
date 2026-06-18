from fastapi import FastAPI, HTTPException
from app.data_loader import load_data
from app.verifier import verify_user
from app.models import UserInput
from app.validators import validate_pan, validate_aadhaar

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