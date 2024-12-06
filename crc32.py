import zlib

# The byte sequence
byte_sequence = bytes.fromhex("2F FF C0 64 00 14 00 00 00 01 81 CD 01 05 12 34 48 65 6C 6C 6F 21")

print(" ".join([f"{b:02X}" for b in byte_sequence]))

# Calculate CRC32 using zlib
crc32_value = zlib.crc32(byte_sequence)

# Print the result in decimal and hexadecimal
print(f"CRC32 (decimal): {crc32_value}")
print(f"CRC32 (hexadecimal): 0x{crc32_value:08X}")