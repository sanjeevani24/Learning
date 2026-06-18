def verify_user(df, user):
    record = df[df["aadhaar_number"] == str(user["aadhaar_number"])]

    if record.empty:
        return {
            "status": "REJECTED",
            "reason": "Aadhaar not found"
        }

    record = record.iloc[0]

    score = 0
    matched = []
    mismatched = []

    if record["full_name"] == user["full_name"]:
        score += 1
        matched.append("full_name")
    else:
        mismatched.append("full_name")

    if record["phone_number"] == user["phone_number"]:
        score += 1
        matched.append("phone_number")
    else:
        mismatched.append("phone_number")

    if record["pan_card_number"] == user["pan_card_number"]:
        score += 1
        matched.append("pan_card_number")
    else:
        mismatched.append("pan_card_number")

    if record["date_of_birth"] == user["date_of_birth"]:
        score += 1
        matched.append("date_of_birth")
    else:
        mismatched.append("date_of_birth")

    trust = score / 4

    if trust >= 0.75:
        status = "VERIFIED"
    elif trust >= 0.5:
        status = "REVIEW"
    else:
        status = "REJECTED"

    return {
        "status": status,
        "score": trust,
        "matched_fields": matched,
        "mismatched_fields": mismatched
    }