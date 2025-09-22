import struct
import binascii

def parse_memory_data(data_bytes: bytes) -> bool:
    """
    Parses a byte string containing data from multiple memory peek/read
    commands, prints the results in a simplified format, and returns
    True if successful, or False otherwise.
    """
    try:
        data_ptr = 0
        total_len = len(data_bytes)

        # Loop until all bytes in the response packet are consumed
        while data_ptr < total_len:
            # Check for a minimum 5-byte header for the next command unit
            if total_len - data_ptr < 5:
                print("Parse failed: Remaining data is too short for a command header.")
                return False

            # Parse the address and size from the current command unit
            address = struct.unpack('<I', data_bytes[data_ptr : data_ptr + 4])[0]
            size_code = data_bytes[data_ptr + 4]
            data_ptr += 5  # Advance pointer past the header

            # Determine the expected length of the data payload based on the address
            address_high_16 = (address >> 16) & 0xFFFF
            if address_high_16 == 0x4001:
                expected_data_len = size_code * 4
            else:
                expected_data_len = size_code

            # Check if the remaining data matches the expected payload length
            if total_len - data_ptr < expected_data_len:
                print(f"Parse failed: Data payload mismatch. Expected {expected_data_len} bytes, got {total_len - data_ptr}.")
                return False
            
            # Slice the payload for the current command
            data_payload = data_bytes[data_ptr : data_ptr + expected_data_len]

            # Print the parsed data
            if address_high_16 == 0x4001:
                if expected_data_len % 4 != 0:
                    print("Parse failed: Payload length not a multiple of 4.")
                    return False
                
                num_words = expected_data_len // 4
                format_string = f'<{num_words}I'
                data_values = struct.unpack(format_string, data_payload)
                
                for i, val in enumerate(data_values):
                    current_address = address + (i * 4)
                    print(f"0x{current_address:08X}: 0x{val:08X}")
            else:
                formatted_hex = ' '.join(f'{b:02X}' for b in data_payload)
                print(f"0x{address:08X}: {formatted_hex}")

            # Advance the pointer past the current command's payload
            data_ptr += expected_data_len

        return True
    
    except (struct.error, ValueError, IndexError) as e:
        print(f"Parse failed: An error occurred. Details: {e}")
        return False