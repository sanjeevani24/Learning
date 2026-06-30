'''from app.data_loader import load_data
from app.verifier import verify_user

df = load_data()

user = {
    "aadhaar_number": "472980699016",
    "full_name": "Elina Dalal",
    "phone_number": "7734670656",
    "pan_card_number": "DMBJF3737N",
    "date_of_birth": "1982-08-19"
}

result = verify_user(user)
print(result)'''

# test_qr.py

from app.qr_extractor import extract_qr_data

print(
    extract_qr_data(
        "temp_Aadhaar.jpeg"
    )
)