import struct
import binascii

def parse_memory_data(data_bytes: bytes) -> bool:
    """
    Parses a byte string containing memory peek/read data and prints the results
    in a simplified format. Returns True if successful, or False otherwise.
    """
    try:
        if len(data_bytes) < 5:
            print("Parse failed: Data is too short.")
            return False

        address = struct.unpack('<I', data_bytes[0:4])[0]
        size_code = data_bytes[4]
        data_payload = data_bytes[5:]
        payload_len = len(data_payload)
        address_high_16 = (address >> 16) & 0xFFFF

        expected_data_len = size_code
        if address_high_16 == 0x4001:
            expected_data_len = size_code * 4

        if payload_len != expected_data_len:
            print(f"Parse failed: Data length mismatch. Expected {expected_data_len} bytes, got {payload_len}.")
            return False

        if address_high_16 == 0x4001:
            if payload_len % 4 != 0:
                print("Parse failed: Payload length not a multiple of 4.")
                return False
            
            num_words = payload_len // 4
            format_string = f'<{num_words}I'
            data_values = struct.unpack(format_string, data_payload)
            
            for i, val in enumerate(data_values):
                current_address = address + (i * 4)
                print(f"0x{current_address:08X}: 0x{val:08X}")
        else:
            # Handle the case for addresses outside the 0x4001xxxx range
            # with the requested spaced hexadecimal output
            formatted_hex = ' '.join(f'{b:02X}' for b in data_payload)
            print(f"0x{address:08X}: {formatted_hex}")

        return True
    
    except (struct.error, ValueError, IndexError) as e:
        print(f"Parse failed: An error occurred. Details: {e}")
        return False