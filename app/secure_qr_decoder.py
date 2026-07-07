def decimal_to_bytes(payload: str):
    number = int(payload)
    length = (number.bit_length() + 7) // 8
    return number.to_bytes(length, "big")

import gzip

def decompress_payload(byte_data: bytes):
    return gzip.decompress(byte_data)

def parse_secure_qr(decompressed):

    fields = [
        f.decode("utf-8", errors="ignore")
        for f in decompressed.split(b"\xff")[:18]
    ]

    address = ", ".join(
        filter(
            None,
            [
                fields[9],
                fields[10],
                fields[14],
                fields[15],
                fields[12],
                fields[13],
                fields[11]
            ]
        )
    )

    return {
        "version": fields[0],
        "qr_version": fields[1],
        "reference_id": fields[2],
        "full_name": fields[3],
        "date_of_birth": fields[4],
        "gender": fields[5],
        "care_of": fields[6],
        "city": fields[7],
        "address": address,
        "masked_mobile": fields[17]
    }
def decode_secure_qr(payload: str):

    bytes_data = decimal_to_bytes(payload)

    decompressed = decompress_payload(bytes_data)

    return parse_secure_qr(decompressed)


'''from pathlib import Path


payload_path = Path(__file__).parent / "payload.txt"

with open(payload_path, "r", encoding="utf-8") as f:
    payload = "".join(f.read().split())

print("Length:", len(payload))
print("Is digit:", payload.isdigit())
bytes_data = decimal_to_bytes(payload)

print(type(bytes_data))
print("Byte Length:", len(bytes_data))
print(bytes_data[:50])
print("Length:", len(payload))
print("Is digit:", payload.isdigit())
print("First 50:", repr(payload[:50]))
print("Last 50 :", repr(payload[-50:]))

for i, ch in enumerate(payload):
    if not ch.isdigit():
        print("Found non-digit!")
        print("Index:", i)
        print("Character:", repr(ch))
        print("ASCII:", ord(ch))
    try:

            decompressed = decompress_payload(bytes_data)

            qr_data = parse_secure_qr(decompressed)

            print("\nDecoded QR Data:\n")
            print(qr_data)

    except Exception as e:

        print("\nFAILED")
        print(type(e).__name__)
        print(e)'''