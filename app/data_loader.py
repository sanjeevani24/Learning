import pandas as pd

def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1oXe4nlw-d2-74pUeM6Sz8kgcQaDHoQFHvbScA8mDzPw/export?format=xlsx"
    
    df = pd.read_excel(sheet_url)

    # Clean column names
    df.columns = df.columns.str.strip().str.lower()

    # Fix datatypes
    df["aadhaar_number"] = df["aadhaar_number"].astype(str)
    df["phone_number"] = df["phone_number"].astype(str)
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"]).dt.strftime('%Y-%m-%d')

    return df