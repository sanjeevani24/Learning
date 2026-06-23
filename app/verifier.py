def verify_user(df, user):
    record = df[df["aadhaar_number"] == str(user.get("aadhaar_number", ""))]

    if record.empty:
        return {
            "status": "REJECTED",
            "reason": "Aadhaar not found"
        }

    record = record.iloc[0]

    score = 0
    matched = []
    mismatched = []
    missing_fields = []
    compared_fields = 0

    for field in ["full_name", "phone_number", "pan_card_number", "date_of_birth"]:
        user_value = user.get(field)

        if user_value is None:
            missing_fields.append(field)
            continue

        compared_fields += 1
        record_value = record.get(field)

        if str(record_value).strip() == str(user_value).strip():
            score += 1
            matched.append(field)
        else:
            mismatched.append(field)

    trust = score / compared_fields if compared_fields else 0

    if compared_fields == 0:
        status = "REVIEW"
    elif trust >= 0.75:
        status = "VERIFIED"
    elif trust >= 0.5:
        status = "REVIEW"
    else:
        status = "REJECTED"

    result = {
        "status": status,
        "score": trust,
        "matched_fields": matched,
        "mismatched_fields": mismatched
    }

    if missing_fields:
        result["missing_fields"] = missing_fields

    return result
