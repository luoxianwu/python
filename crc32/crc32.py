import zlib

def reflect(data, width):
    """Reflect the bits of data (e.g., convert little-endian to big-endian)."""
    result = 0
    for i in range(width):
        if data & (1 << i):
            result |= 1 << (width - 1 - i)
    return result

def big_endian_crc32(data):
    """Compute CRC32 in big-endian mode using zlib.crc32."""
    # Reflect each byte in the input data
    reflected_data = bytes(reflect(byte, 8) for byte in data)
    
    # Compute the CRC32 on the reflected data
    crc = zlib.crc32(reflected_data) & 0xFFFFFFFF  # Ensure 32-bit unsigned
    
    # Reflect the final CRC result to convert it to big-endian order
    return reflect(crc, 32)

# Input data
data = bytes([1, 2, 3, 4, 5])

# Compute big-endian CRC32
crc32_value = big_endian_crc32(data)

# Output the result
print(hex(crc32_value))  # Should match big-endian calculations



def crc32_c(data, initial=0xFFFFFFFF, polynomial=0x04C11DB7, final_xor=0xFFFFFFFF):
    crc = initial
    for byte in data:
        crc ^= (byte << 24)
        for _ in range(8):
            if crc & 0x80000000:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFFFFFFFF  # Ensure 32-bit value
    return crc ^ final_xor

data = [1, 2, 3, 4, 5]
print(hex(crc32_c(data)))  # Expected output: 0x1D70B47C


import struct

def crc32_big_endian(data, polynomial=0x04C11DB7, initial=0xFFFFFFFF, final_xor=0xFFFFFFFF):
    """
    Calculate the CRC32 for a big-endian input data stream.
    """
    crc = initial  # Initialize the CRC value
    for byte in data:
        crc ^= byte << 24  # Align the byte to the top 8 bits of the CRC
        for _ in range(8):  # Process each bit
            if crc & 0x80000000:  # Check if the MSB is set
                crc = (crc << 1) ^ polynomial  # Apply the polynomial
            else:
                crc <<= 1  # Just shift left
            crc &= 0xFFFFFFFF  # Ensure CRC stays within 32 bits
    return crc ^ final_xor  # Apply the final XOR step

# Data to send
data = bytes([1, 2, 3, 4, 5])  # Big-endian data stream

# Calculate CRC32 for the data
crc32_value = crc32_big_endian(data)

# Append CRC32 to the data
data_with_crc = data + struct.pack(">I", crc32_value)  # ">I" ensures big-endian CRC

# Print the data with CRC32
print(f"Data to send (hex): {data_with_crc.hex()}")