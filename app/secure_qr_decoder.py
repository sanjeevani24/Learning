def decimal_to_bytes(payload: str):
    number = int(payload)
    length = (number.bit_length() + 7) // 8
    return number.to_bytes(length, "big")

from pathlib import Path

payload_path = Path(__file__).parent / "payload.txt"

with open(payload_path, "r", encoding="utf-8") as f:
    payload = "".join(f.read().split())

print("Length:", len(payload))
print("Is digit:", payload.isdigit())
#bytes_data = decimal_to_bytes(payload)

#print(type(bytes_data))
#print("Byte Length:", len(bytes_data))
#print(bytes_data[:50])
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
        