from sqlalchemy import text
from app.database import engine

def get_user(aadhaar):

    query = text("""
        SELECT *
        FROM users
        WHERE aadhaar_number = :aadhaar
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {"aadhaar": aadhaar}
        )

        row = result.fetchone()

        if row is None:
            return None

        return dict(row._mapping)
    
def find_user_by_fields(user):

    if not user:
        return None

    def fetch_by_query(query_text, params):
        with engine.connect() as conn:
            result = conn.execute(text(query_text), params)
            row = result.fetchone()
            if row is None:
                return None
            return dict(row._mapping)

    pan_number = user.get("pan_card_number")
    if pan_number:
        record = fetch_by_query(
            """
            SELECT *
            FROM users
            WHERE lower(trim(pan_card_number)) = lower(trim(:pan))
            """,
            {"pan": pan_number}
        )
        if record is not None:
            return record

    full_name = user.get("full_name")
    date_of_birth = user.get("date_of_birth")
    if full_name and date_of_birth:
        record = fetch_by_query(
            """
            SELECT *
            FROM users
            WHERE lower(trim(full_name)) = lower(trim(:name))
            AND lower(trim(date_of_birth)) = lower(trim(:dob))
            """,
            {"name": full_name, "dob": date_of_birth}
        )
        if record is not None:
            return record

    date_of_birth = user.get("date_of_birth")
    if date_of_birth:
        record = fetch_by_query(
            """
            SELECT *
            FROM users
            WHERE lower(trim(date_of_birth)) = lower(trim(:dob))
            """,
            {"dob": date_of_birth}
        )
        if record is not None:
            return record

    return None