import zlib

data = bytes([1, 2, 3, 4, 5])

print(" ".join([f"{b:02X}" for b in data]))
crc32_result = zlib.crc32(data)
print(f"CRC32: {crc32_result:08X}")