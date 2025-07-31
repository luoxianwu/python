import ctypes
import zlib
import struct  # for packing/unpacking binary data
import time
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
        # ("count", ctypes.c_uint8),       # Removed
        ("reserved", ctypes.c_uint8),      # Now 1 byte (was c_uint16)
    ]

    def __str__(self):
        return (f"ABF_Packet_Header:\n"
                f"  Sync:          0x{self.pkt_sync[0]:02X} 0x{self.pkt_sync[1]:02X}\n"
                f"  Packet Length: {self.packet_length}\n"
                f"  Function:      0x{self.function:02X}\n"
                f"  Reserved:      0x{self.reserved:02X}") # Changed format to 02X for 1 byte


class ABF_Packet:
    """
    Represents a complete ABF packet.
    Updated: 'count' removed, 'reserved' is now 1 byte.
    """
    SYNC_WORD = 0xAA55 # Little-endian representation 0x55 0xAA

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
        print(f"Received CRC: 0x{received_crc:08X}")

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
        Updated: 'count' removed, 'reserved' is now 1 byte.

        Args:
            file_path: Path to the text file.

        Returns:
            ABF_Packet: The ABF packet read from the file.
        """
        with open(file_path, "r") as f:
            lines = f.readlines()

        file_dict = {}
        data = b"" # Default to empty bytes
        crc = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value_with_comment = line.split(":", 1)
                key = key.lower().replace(" ", "_")
                value = value_with_comment.split("#")[0].strip()
                file_dict[key] = value

        # Handle data (hex)
        data_hex_str = file_dict.get("data_(hex)", "").replace("0x", "").replace(",", "").replace(" ", "").replace('"', "").strip()
        if data_hex_str:
            try:
                data = bytes.fromhex(data_hex_str)
            except ValueError as e:
                raise ValueError(f"Invalid hex data in input file: {e}")

        # Handle CRC
        crc_str = file_dict.get("crc32", "?")
        if crc_str != "?":
            try:
                crc = int(crc_str, 16)
            except ValueError:
                crc = None # Keep as None if parsing fails

        # Construct header fields
        try:
            sync_bytes = bytes.fromhex(file_dict["sync"].replace("0x", "").replace(",", ""))
            function_code = int(file_dict["function"].replace("0x", ""), 16)
            reserved_value = int(file_dict["reserved"].replace("0x", ""), 16) # Now 1 byte
        except KeyError as e:
            raise ValueError(f"Missing key in input file: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid value in input file: {e}")

        # Create ABF_Packet instance (CRC will be calculated if None)
        packet = ABF_Packet(function_code, reserved_value, data) # 'count' removed

        # Overwrite packet_length if explicitly provided and not '?'
        if file_dict.get("packet_length") != "?":
            try:
                packet.header.packet_length = int(file_dict["packet_length"])
            except ValueError as e:
                raise ValueError(f"Invalid packet_length in input file: {e}")
        else:
            # Recalculate packet_length based on actual data if '?'
            # packet_length = (function + reserved + data + crc) = 1 + 1 + len(data) + 4
            packet.header.packet_length = 1 + 1 + len(data) + 4


        # If CRC was provided in file, use it and validate
        if crc is not None:
            if packet.calculate_crc() != crc:
                raise ValueError(f"Invalid CRC in file: Calculated 0x{packet.calculate_crc():08X}, Expected 0x{crc:08X}.")
            packet.crc32 = crc # Set the CRC to the one from file if valid

        return packet
    
    import zlib
    from typing import Tuple, ByteString, Dict

    # Define meaningful names for the states
    STATE_IDLE = 0
    STATE_SYNC = 1
    STATE_LENGTH = 2
    STATE_FUNCTION = 3
    STATE_COUNT = 4
    STATE_RESERVED = 5
    STATE_DATA = 6
    STATE_CRC = 7
    STATE_VALID = 8

    STATE_SYNC_ERR = 0x81
    STATE_LENGTH_ERR = 0x82
    STATE_FUNCTION_ERR = 0x83
    STATE_COUNT_ERR = 0x84
    STATE_CRC_ERR = 0x85
    STATE_FRAME_ERR = 0x86

    MAX_DATA_SIZE = 256


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
        total_packet_size_expected = 2 + 2 + packet_length_from_header;
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
                    if total_packet_size_expected > (2 + 2 + ABF_Packet.MAX_DATA_SIZE + (1 + 1 + CRC_SIZE_BYTES)): # 2 sync + 2 len_field + MAX_DATA_SIZE + (func + reserved + crc)
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
                # Reserved byte is at offset 5 (was 6)
                if received_bytes == 6: # After sync (2) + length (2) + function (1) + reserved (1) = 6 bytes (was 8)
                    # Now we have received the entire fixed header.
                    # The remaining bytes are data + CRC.
                    # Total bytes expected = 2 (sync) + 2 (length_field) + packet_length_from_header
                    if received_bytes < (total_packet_size_expected - CRC_SIZE_BYTES):
                        current_state = ABF_Packet.STATE_DATA
                    elif received_bytes == (total_packet_size_expected - CRC_SIZE_BYTES):
                        current_state = ABF_Packet.STATE_CRC # No data, directly to CRC
                    else:
                        print("Packet size invalid")

            elif current_state == ABF_Packet.STATE_DATA:
                # Data bytes are from offset 6 (was 8) up to (total_packet_size - CRC_SIZE_BYTES)
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
                    # This segment starts at rec_packet[2] and has a length of packet_length_from_header - CRC_SIZE_BYTES
                    crc_data_segment_len = 2 + packet_length_from_header - CRC_SIZE_BYTES
                    crc_calculated = zlib.crc32(rec_packet[2 : 2 + crc_data_segment_len]) & 0xFFFFFFFF

                    crc_received = int.from_bytes(rec_packet[-CRC_SIZE_BYTES:], 'little')

                    if crc_calculated == crc_received:
                        print("Packet CRC valid")
                        current_state = ABF_Packet.STATE_VALID
                    else:
                        print(f"Packet CRC: 0x{crc_received:08X}, calculated CRC: 0x{crc_calculated:08X}")
                        current_state = ABF_Packet.STATE_CRC_ERR
                    break # Packet fully received or error, exit loop

            elif current_state in [ABF_Packet.STATE_SYNC_ERR, ABF_Packet.STATE_LENGTH_ERR, ABF_Packet.STATE_FUNCTION_ERR, ABF_Packet.STATE_COUNT_ERR, ABF_Packet.STATE_CRC_ERR, STATE_FRAME_ERR]:
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
    # This data_for_crc_test now represents:
    # (data_length_low_byte, data_length_high_byte, function, reserved, data_byte1, data_byte2)
    # Example: data_length=0x0008, function=0x02, reserved=0x01, data=0x0000
    # For the C-side crc32: abf_crc32( (uint8_t*)&abf_pkt_response.data_length, crc_cal_len )
    # If crc_cal_len is 6 (func+reserved+crc), then data_length is 1+1+4 = 6
    # If data_length is 8, then it implies (func+reserved+data+crc), where data is 2 bytes.
    # Let's assume data_for_crc_test is (data_length_field + function + reserved + data)
    # The C code calculates CRC over (data_length field itself + function + reserved + data)
    # So, data_for_crc_test should be:
    # [Length_L, Length_H, Function, Reserved, Data_0, Data_1, ...]
    # Example: Length=6 (func+res+crc), Func=0x02, Res=0x00, Data=""
    # Then crc_data is [0x06, 0x00, 0x02, 0x00]
    # If Length=8 (func+res+data[2]+crc), Func=0x02, Res=0x01, Data=0x0000
    # Then crc_data is [0x08, 0x00, 0x02, 0x01, 0x00, 0x00]
    # This matches your original test data.
    data_for_crc_test = bytes([0x08, 0x00, 0x02, 0x01, 0x00, 0x00]) # This is (data_length, function, reserved, data)
    crc_test = zlib.crc32(data_for_crc_test) & 0xFFFFFFFF
    print(f"Data for CRC Test (Hex): {' '.join([f'{b:02X}' for b in data_for_crc_test])}")
    print(f"CRC32 (Python zlib, default - likely non-reversed): 0x{crc_test:08X}")
    print("----------------------------------------------\n\n")

    # Create an ABF packet
    # Adjusted to new structure: function, reserved, data
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

    # Create ABF packet from file
    # tlm1.abf content (from your original query):
    # #ABF_Packet:
    # #  Sync:          0x55, 0xAA
    # #  Packet Length: ?
    # #  Function:      0x02
    # #  Count:         1  <--- This 'Count' field is now removed from protocol
    # #  Reserved:      0    <--- This 'Reserved' is now 1 byte
    # #  Data (Hex):    ""
    # #  CRC32:         ?

    # For tlm1.abf, you'll need to update the file to match the new structure
    # Example tlm1.abf for the new protocol:
    # ABF_Packet:
    #   Sync: 0x55, 0xAA
    #   Packet Length: ?
    #   Function: 0x02
    #   Reserved: 0x00
    #   Data (Hex): ""
    #   CRC32: ?
    try:
        # Create a dummy tlm1.abf file for testing if it doesn't exist
        try:
            with open("tlm1.abf", "x") as f:
                f.write("ABF_Packet:\n")
                f.write("  Sync: 0x55, 0xAA\n")
                f.write("  Packet Length: ?\n")
                f.write("  Function: 0x02\n")
                f.write("  Reserved: 0x00\n")
                f.write("  Data (Hex): \"\"\n")
                f.write("  CRC32: ?\n")
            print("Created dummy tlm1.abf for testing.")
        except FileExistsError:
            pass # File already exists, proceed

        packet_from_file = ABF_Packet.from_file("tlm1.abf")
        print("\nPacket from file:")
        print(packet_from_file)
    except ValueError as e:
        print(f"Error: {e}")

