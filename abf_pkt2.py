import ctypes
import zlib
import struct  # for packing/unpacking binary data
import time
import sys
import os
from typing import Tuple, ByteString, Dict # For type hints in get_packet


class ABF_Packet_Header(ctypes.Structure):
    """
    Defines the structure of the ABF packet header.
    Updated: 'count' removed, 'reserved' is now 1 byte.
    """
    _pack_ = 1  # Ensure no padding between fields
    _fields_ = [
        ("pkt_sync", ctypes.c_uint8 * 2),  # Sync bytes (0x55, 0xAA)
        ("packet_length", ctypes.c_uint16), # Length of (function + reserved + data + crc)
        ("function", ctypes.c_uint8),      # Function code
        # ("count", ctypes.c_uint8),      # Removed
        ("reserved", ctypes.c_uint8),      # Now 1 byte (was c_uint16)
    ]

    def __str__(self):
        return (f"ABF_Packet_Header:\n"
                f"  Sync:            0x{self.pkt_sync[0]:02X} 0x{self.pkt_sync[1]:02X}\n"
                f"  Packet Length: {self.packet_length}\n"
                f"  Function:        0x{self.function:02X}\n"
                f"  Reserved:        0x{self.reserved:02X}") # Changed format to 02X for 1 byte


class ABF_Packet:
    """
    Represents a complete ABF packet.
    Updated: 'count' removed, 'reserved' is now 1 byte.
    """
    SYNC_WORD = 0xAA55 # Little-endian representation 0x55 0xAA

    # Define meaningful names for the states as class attributes
    STATE_IDLE = 0
    STATE_SYNC = 1
    STATE_LENGTH = 2
    STATE_FUNCTION = 3
    STATE_COUNT = 4 # Kept for consistency with original states, though 'count' field is removed
    STATE_RESERVED = 5
    STATE_DATA = 6
    STATE_CRC = 7
    STATE_VALID = 8

    STATE_SYNC_ERR = 0x81
    STATE_LENGTH_ERR = 0x82
    STATE_FUNCTION_ERR = 0x83
    STATE_COUNT_ERR = 0x84 # Kept for consistency
    STATE_CRC_ERR = 0x85
    STATE_FRAME_ERR = 0x86

    MAX_DATA_SIZE = 256 # Maximum allowed data payload size

    def __init__(self, function: int, reserved: int, data: bytes = b''): # 'count' removed from signature
        """
        Initializes an ABF packet.

        Args:
            function: The function code.
            reserved: The reserved field (now 1 byte).
            data: The payload data (excluding CRC).
        """
        self.header = ABF_Packet_Header()
        self.header.pkt_sync[0] = 0x55
        self.header.pkt_sync[1] = 0xAA
        self.header.function = function
        self.header.reserved = reserved # Now 1 byte

        self.data = data if data is not None else b""
        
        # packet_length = (function_size + reserved_size + data_size + crc_size)
        # 1 (func) + 1 (reserved) + len(data) + 4 (crc) = 6 + len(data)
        self.header.packet_length = 1 + 1 + len(self.data) + 4
        
        self.crc32 = self.calculate_crc()

    def calculate_crc(self):
        """
        Calculates the CRC32 checksum over the data_length field, function, reserved, and data.
        """
        # The C code calculates CRC over (data_length field itself + function + reserved + data)
        # header_bytes[2:] gives (packet_length field + function + reserved)
        # So, crc_data = packet_length_field + function + reserved + data
        header_bytes_part = bytes(self.header)[2:] # This gets data_length, function, reserved
        crc_data = header_bytes_part + self.data
        return zlib.crc32(crc_data) & 0xFFFFFFFF

    def to_bytes(self):
        """
        Serializes the ABF packet to bytes.

        Returns:
            bytes: The serialized packet.
        """
        header_bytes = bytes(self.header) # This will be 6 bytes (sync, length, func, reserved)
        crc_bytes = self.crc32.to_bytes(4, byteorder='little')  # CRC is 4 bytes, little-endian
        return header_bytes + self.data + crc_bytes

    def __str__(self):
        return (f"ABF_Packet:\n"
                f"{str(self.header)}\n"
                f"  Data (Hex):    {' '.join(f'{b:02X}' for b in self.data)}\n"
                f"  CRC32:         0x{self.crc32:08X}")

    @staticmethod
    def from_bytes(buffer: bytes):
        """
        Deserializes an ABF packet from bytes and validates the CRC.
        Updated: 'count' removed, 'reserved' is now 1 byte.

        Args:
            buffer: The received byte stream.

        Returns:
            ABF_Packet: The deserialized ABF packet.

        Raises:
            ValueError: If the buffer is too short or the CRC is invalid.
        """
        HEADER_SIZE_BYTES = ctypes.sizeof(ABF_Packet_Header) # Now 6 bytes (was 8)
        CRC_SIZE_BYTES = 4
        MIN_PACKET_SIZE = HEADER_SIZE_BYTES + CRC_SIZE_BYTES # 6 + 4 = 10 (was 12)

        if len(buffer) < MIN_PACKET_SIZE:
            raise ValueError(f"Invalid packet: Too short. Expected at least {MIN_PACKET_SIZE} bytes, got {len(buffer)}")

        header_bytes = buffer[:HEADER_SIZE_BYTES]
        header = ABF_Packet_Header.from_buffer_copy(header_bytes)
        
        packet_length_from_header = header.packet_length # This is the length of (func + reserved + data + crc)

        # Validate packet_length from header
        # Minimum packet_length value (func+reserved+crc) is 1+1+4 = 6
        if packet_length_from_header < (1 + 1 + CRC_SIZE_BYTES):
            raise ValueError(f"Invalid packet: packet_length ({packet_length_from_header}) is too small.")
        
        # Total expected bytes in buffer = SYNC_SIZE (2) + LENGTH_FIELD_SIZE (2) + packet_length_from_header
        total_expected_buffer_len = 2 + 2 + packet_length_from_header
        if len(buffer) < total_expected_buffer_len:
            raise ValueError(f"Invalid packet: Buffer length ({len(buffer)}) is less than total expected ({total_expected_buffer_len}) based on header's packet_length.")


        # Calculate actual data payload length
        # data_length_from_header = (function + reserved + data + crc)
        # So, data_payload_len = data_length_from_header - (function + reserved + crc)
        data_payload_len = packet_length_from_header - (1 + 1 + CRC_SIZE_BYTES) # 1 func + 1 reserved + 4 crc = 6
        
        data_start_idx = HEADER_SIZE_BYTES # Data starts after the fixed header (offset 6)
        data_end_idx = data_start_idx + data_payload_len
        
        data = buffer[data_start_idx:data_end_idx]

        # Extract CRC
        crc_bytes_start_idx = data_end_idx
        crc_bytes_end_idx = crc_bytes_start_idx + CRC_SIZE_BYTES
        crc_bytes = buffer[crc_bytes_start_idx:crc_bytes_end_idx]
        received_crc = int.from_bytes(crc_bytes, byteorder='little')
        # print(f"Received CRC: 0x{received_crc:08X}") # Commented out for cleaner output

        # Calculate CRC over (data_length field + function + reserved + data)
        # This corresponds to buffer[2 : crc_bytes_start_idx]
        calculated_crc_data_segment = buffer[2:crc_bytes_start_idx]
        calculated_crc = zlib.crc32(calculated_crc_data_segment) & 0xFFFFFFFF

        if received_crc != calculated_crc:
            raise ValueError(f"Invalid CRC: Expected 0x{received_crc:08X}, Calculated 0x{calculated_crc:08X}")

        # Reconstruct ABF_Packet object
        return ABF_Packet(header.function, header.reserved, data) # 'count' removed

    @staticmethod
    def from_file(file_path: str):
        """
        Reads an ABF packet from a text file.
        Handles multi-line 'Data (Hex)' section with hex values and comments,
        converting each hex value to little-endian bytes.
        """
        with open(file_path, "r") as f:
            lines = f.readlines()

        file_dict = {}
        data_content_lines = []
        in_data_section = False

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.lower().startswith("data (hex):"):
                in_data_section = True
                data_hex_part = stripped_line[len("data (hex):"):].strip()
                if data_hex_part.startswith('"'):
                    data_hex_part = data_hex_part[1:]
                data_content_lines.append(data_hex_part)
                continue

            if in_data_section:
                if stripped_line.endswith('"'):
                    data_content_lines.append(stripped_line[:-1])
                    in_data_section = False
                    continue
                
                if ":" in stripped_line and not stripped_line.startswith("#") and not stripped_line.lower().startswith("data (hex):"):
                    in_data_section = False
                    key, value_with_comment = stripped_line.split(":", 1)
                    key = key.lower().replace(" ", "_")
                    value = value_with_comment.split("#")[0].strip()
                    file_dict[key] = value
                    continue
                
                data_content_lines.append(stripped_line)
                continue

            if ":" in stripped_line:
                key, value_with_comment = stripped_line.split(":", 1)
                key = key.lower().replace(" ", "_")
                value = value_with_comment.split("#")[0].strip()
                file_dict[key] = value
            elif not stripped_line.startswith("#"):
                pass

        data = b""
        if data_content_lines:
            all_raw_hex_numbers = []
            for line_part in data_content_lines:
                line_without_comment = line_part.split("#")[0].strip()
                individual_hex_strings = [h.strip() for h in line_without_comment.split(',') if h.strip()]
                all_raw_hex_numbers.extend(individual_hex_strings)
            
            for hex_val_str in all_raw_hex_numbers:
                cleaned_hex_val = hex_val_str.replace("0x", "").strip()
                
                if not cleaned_hex_val:
                    continue

                try:
                    if len(cleaned_hex_val) % 2 != 0:
                        cleaned_hex_val = '0' + cleaned_hex_val
                    
                    byte_val = bytes.fromhex(cleaned_hex_val)
                    data += byte_val[::-1] # Reverse bytes for little-endian
                except ValueError as e:
                    raise ValueError(f"Invalid hex data in input file ('{cleaned_hex_val}'): {e}")

        crc_str = file_dict.get("crc32", "?")
        crc = None
        if crc_str != "?":
            try:
                crc = int(crc_str, 16)
            except ValueError:
                crc = None

        try:
            sync_bytes_str = file_dict.get("sync")
            if sync_bytes_str:
                # This line is just to validate the sync bytes format, not used in packet construction
                _ = bytes.fromhex(sync_bytes_str.replace("0x", "").replace(",", "").replace(" ", ""))
            else:
                raise KeyError("'sync' key is missing or empty.")

            function_code = int(file_dict["function"].replace("0x", ""), 16)
            reserved_value = int(file_dict["reserved"].replace("0x", ""), 16)
        except KeyError as e:
            raise ValueError(f"Missing key in input file: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid value in input file: {e}")

        packet = ABF_Packet(function_code, reserved_value, data)

        if file_dict.get("packet_length") != "?":
            try:
                packet.header.packet_length = int(file_dict["packet_length"])
            except ValueError as e:
                raise ValueError(f"Invalid packet_length in input file: {e}")
        else:
            packet.header.packet_length = 1 + 1 + len(data) + 4

        if crc is not None:
            if packet.calculate_crc() != crc:
                raise ValueError(f"Invalid CRC in file: Calculated 0x{packet.calculate_crc():08X}, Expected 0x{crc:08X}.")
            packet.crc32 = crc

        return packet

    @staticmethod # <--- get_packet is now a static method of ABF_Packet
    def get_packet(ser) -> Dict[str, any]:
        """
        Receives an ABF packet from the serial port and returns a dictionary
        containing the packet data and reception status.
        Updated: 'count' removed, 'reserved' is now 1 byte.

        Args:
            ser: The serial port object (pyserial.Serial).

        Returns:
            dict: A dictionary with the following keys:
                - "state": The final state of the packet reception (int).  Use the STATE_... constants.
                - "bytes_received": The total number of bytes received (int).
                - "packet_length": The length of the packet as indicated in the header (int).
                - "rec_packet": The raw bytearray of the received packet (bytearray).
        """
        rec_packet = bytearray()
        current_state = ABF_Packet.STATE_IDLE
        received_bytes = 0
        packet_length_from_header = 0 # Renamed to avoid conflict with function arg
        total_packet_size_expected = 0 # Initialize to 0, will be calculated later
        print("\nReceive Packet...")

        HEADER_SIZE_BYTES = ctypes.sizeof(ABF_Packet_Header) # Now 6 bytes (was 8)
        CRC_SIZE_BYTES = 4
        MIN_PACKET_LENGTH_VALUE = 1 + 1 + CRC_SIZE_BYTES # func (1) + reserved (1) + crc (4) = 6

        while True:
            byte = ser.read(1)
            if not byte:
                break # No more bytes from serial

            rec_packet.extend(byte)
            received_bytes += 1
            print(byte.hex().upper() + " ", end="")

            if current_state == ABF_Packet.STATE_IDLE:
                current_state = ABF_Packet.STATE_SYNC

            if current_state == ABF_Packet.STATE_SYNC:
                if received_bytes == 1: # First byte received
                    if rec_packet[0] != 0x55:
                        current_state = ABF_Packet.STATE_SYNC_ERR
                        break # Exit on error
                elif received_bytes == 2: # Second byte received
                    if rec_packet[1] != 0xAA:
                        current_state = ABF_Packet.STATE_SYNC_ERR
                        break # Exit on error
                    else:
                        current_state = ABF_Packet.STATE_LENGTH
                # No 'else' for received_bytes > 2 here, as it's handled by the break on error
                # or the state transition.

            elif current_state == ABF_Packet.STATE_LENGTH:
                # Packet length field is at offset 2 (bytes 2 and 3)
                if received_bytes == 4: # After receiving sync (2) + length (2) = 4 bytes
                    packet_length_from_header = rec_packet[2] + (rec_packet[3] << 8) # Little-endian

                    if packet_length_from_header < MIN_PACKET_LENGTH_VALUE:
                        print(f"\nLength Error: Packet length ({packet_length_from_header}) too short. Min is {MIN_PACKET_LENGTH_VALUE}.")
                        current_state = ABF_Packet.STATE_LENGTH_ERR
                        break # Exit on error
                    
                    # Check if announced length exceeds max buffer size
                    # Total packet size = SYNC_SIZE (2) + LENGTH_FIELD_SIZE (2) + packet_length_from_header
                    total_packet_size_expected = 2 + 2 + packet_length_from_header
                    # MAX_DATA_SIZE + HEADER_SIZE_BYTES + CRC_SIZE_BYTES is the max total packet size
                    # The maximum value for packet_length_from_header is (1 + 1 + ABF_Packet.MAX_DATA_SIZE + 4)
                    # So, the maximum total_packet_size_expected is 4 + 6 + ABF_Packet.MAX_DATA_SIZE = 10 + ABF_Packet.MAX_DATA_SIZE
                    if total_packet_size_expected > (10 + ABF_Packet.MAX_DATA_SIZE):
                        print(f"\nLength Error: Packet length ({packet_length_from_header}) too large for buffer.")
                        current_state = ABF_Packet.STATE_LENGTH_ERR
                        break # Exit on error

                    current_state = ABF_Packet.STATE_FUNCTION

            elif current_state == ABF_Packet.STATE_FUNCTION:
                # Function byte is at offset 4
                if received_bytes == 5: # After sync (2) + length (2) + function (1) = 5 bytes
                    # No validation for function code in this generic receiver, just transition
                    current_state = ABF_Packet.STATE_RESERVED # Transition to STATE_RESERVED

            elif current_state == ABF_Packet.STATE_RESERVED:
                # Reserved byte is at offset 5
                if received_bytes == 6: # After sync (2) + length (2) + function (1) + reserved (1) = 6 bytes
                    # Now we have received the entire fixed header.
                    # The remaining bytes are data + CRC.
                    # Total bytes expected = 2 (sync) + 2 (length_field) + packet_length_from_header
                    # If there's no data, we transition directly to CRC state.
                    # Otherwise, we transition to DATA state.
                    if received_bytes < (total_packet_size_expected - CRC_SIZE_BYTES):
                        current_state = ABF_Packet.STATE_DATA
                    elif received_bytes == (total_packet_size_expected - CRC_SIZE_BYTES):
                        current_state = ABF_Packet.STATE_CRC # No data, directly to CRC
                    else:
                        print("Packet size invalid after reserved byte.")
                        current_state = ABF_Packet.STATE_FRAME_ERR
                        break # Exit on error

            elif current_state == ABF_Packet.STATE_DATA:
                # Data bytes are from offset 6 up to (total_packet_size - CRC_SIZE_BYTES)
                # Check if we've received all data bytes + header
                total_packet_size_expected = 2 + 2 + packet_length_from_header
                if received_bytes == (total_packet_size_expected - CRC_SIZE_BYTES):
                    current_state = ABF_Packet.STATE_CRC
                elif received_bytes > total_packet_size_expected :
                    print("\nFrame Error: Received more bytes than expected based on packet length (before CRC).")
                    current_state = ABF_Packet.STATE_FRAME_ERR
                    break # Exit on error

            elif current_state == ABF_Packet.STATE_CRC:
                # CRC bytes are the last 4 bytes of the total packet
                total_packet_size_expected = 2 + 2 + packet_length_from_header
                if received_bytes == total_packet_size_expected:
                    print(f"\nReceived {received_bytes} bytes.")

                    # CRC is calculated over (data_length field + function + reserved + data)
                    # This segment starts at rec_packet[2] and has a length of packet_length_from_header
                    # The actual segment for CRC calculation is from index 2 up to (total_packet_size_expected - CRC_SIZE_BYTES)
                    crc_data_segment = rec_packet[2 : total_packet_size_expected - CRC_SIZE_BYTES]
                    crc_calculated = zlib.crc32(crc_data_segment) & 0xFFFFFFFF

                    crc_received = int.from_bytes(rec_packet[-CRC_SIZE_BYTES:], 'little')

                    if crc_calculated == crc_received:
                        print("Packet CRC valid")
                        current_state = ABF_Packet.STATE_VALID
                    else:
                        print(f"Packet CRC: 0x{crc_received:08X}, calculated CRC: 0x{crc_calculated:08X}")
                        current_state = ABF_Packet.STATE_CRC_ERR
                    break # Packet fully received or error, exit loop

            elif current_state in [ABF_Packet.STATE_SYNC_ERR, ABF_Packet.STATE_LENGTH_ERR, ABF_Packet.STATE_FUNCTION_ERR, ABF_Packet.STATE_COUNT_ERR, ABF_Packet.STATE_CRC_ERR, ABF_Packet.STATE_FRAME_ERR]:
                print("\nError state. Exiting packet reception.")
                break # Exit on error

        return {
            "state": current_state,
            "bytes_received": received_bytes,
            "packet_length": packet_length_from_header, # Return the value from header
            "rec_packet": rec_packet
        }


if __name__ == "__main__":
    # Test CRC calculation with known data (from your original code)
    data_for_crc_test = bytes([0x08, 0x00, 0x02, 0x01, 0x00, 0x00]) # This is (data_length, function, reserved, data)
    crc_test = zlib.crc32(data_for_crc_test) & 0xFFFFFFFF
    print(f"Data for CRC Test (Hex): {' '.join([f'{b:02X}' for b in data_for_crc_test])}")
    print(f"CRC32 (Python zlib, default - likely non-reversed): 0x{crc_test:08X}")
    print("----------------------------------------------\n\n")

    # Create an ABF packet
    header_function = 0x01
    header_reserved = 0x00 # 1 byte reserved
    payload_data = b"Test"

    # packet_length will be calculated automatically in ABF_Packet.__init__
    packet = ABF_Packet(header_function, header_reserved, payload_data)

    # Print the packet
    print(packet)

    # Serialize to bytes
    packet_bytes = packet.to_bytes()
    print(f"Serialized Packet: {' '.join(f'{b:02X}' for b in packet_bytes)}")

    # Deserialize from bytes
    try:
        received_packet = ABF_Packet.from_bytes(packet_bytes)
        print("\nPacket from bytes:")
        print(received_packet)
    except ValueError as e:
        print(f"Error: {e}")

    # --- Main file parsing and byte array generation starts here ---
    if len(sys.argv) < 2:
        print("Usage: python your_script_name.py <filename>")
        print("Example: python your_script_name.py tlm1.abf")
        sys.exit(1)

    file_to_parse = sys.argv[1]

    try:
        # Create a dummy file for testing if it doesn't exist.
        if not os.path.exists(file_to_parse):
             print(f"'{file_to_parse}' not found. Creating a dummy file for testing.")
             with open(file_to_parse, "w") as f:
                 f.write("ABF_Packet:\n")
                 f.write("  Sync: 0x55, 0xAA\n")
                 f.write("  Packet Length: ?\n")
                 f.write("  Function: 0x01 # tele command\n")
                 f.write("  Reserved: 0\n")
                 f.write("  Data (Hex): \"0x2200, 0x0010,\n")
                 f.write("                0x0e66, 0x0005,      #90%, 5 pulse\n")
                 f.write("                0x07ff, 0x0008,      #50%, 8 pulse\n")
                 f.write("                0x0333, 0x0003,      #20%, 3 pulse\n")
                 f.write("               \"\n")
                 f.write("  CRC32: ?\n")
             print(f"Dummy file '{file_to_parse}' created.")

        # Open and print the content of the file
        print(f"\n--- Content of '{file_to_parse}' ---")
        with open(file_to_parse, "r") as f:
            file_content = f.read()
            print(file_content)
        print(f"--- End of '{file_to_parse}' content ---\n")

        # Parse the file into an ABF_Packet object
        packet_from_file = ABF_Packet.from_file(file_to_parse)
        print(f"\nPacket object parsed from '{file_to_parse}':")
        print(packet_from_file)

        # Generate the byte array from the parsed packet
        generated_byte_array = packet_from_file.to_bytes()
        print(f"\nGenerated byte array from '{file_to_parse}':")
        print(f"Byte Array (Hex): {' '.join(f'{b:02X}' for b in generated_byte_array)}")
        print(f"Length: {len(generated_byte_array)} bytes")

    except FileNotFoundError:
        print(f"Error: File '{file_to_parse}' not found. Please ensure the file exists or is correctly named.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error processing file '{file_to_parse}': {e}")
        sys.exit(1)