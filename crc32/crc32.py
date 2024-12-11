import zlib

data = bytes([1, 2, 3, 4, 5])
crc32_result = zlib.crc32(data)
print(f"CRC32: {crc32_result:08X}")