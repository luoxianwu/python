from ctypes import BigEndianStructure, c_uint16, c_uint64, c_uint8, sizeof
import zlib
import re

import time


class CCSDS_Packet_Header(BigEndianStructure):
    _pack_ = 1
    _fields_ = [
        # Primary header
        ("version_number", c_uint16, 3),
        ("packet_type", c_uint16, 1),
        ("second_header_flag", c_uint16, 1),
        ("apid", c_uint16, 11),
        ("group_flag", c_uint16, 2),
        ("sequence_number", c_uint16, 14),
        ("data_length", c_uint16, 16),
        # Secondary header
        ("timing_info", c_uint8 * 6 ),
        ("segment_number", c_uint16, 8),
        ("function_code", c_uint16, 8),
        ("address_code", c_uint16, 16)
    ]

    def __str__(self):
        return (f"CCSDS_Packet_Header({sizeof(CCSDS_Packet_Header)}) bytes:\n"
                f"  Version Number:      {self.version_number}\n"
                f"  Packet Type:         {self.packet_type}\n"
                f"  Second Header Flag:  {self.second_header_flag}\n"
                f"  Application ID:      0x{self.apid:04X}\n"
                f"  Group Flag:          {self.group_flag}\n"
                f"  Sequence Number:     {self.sequence_number}\n"
                f"  Data Length:         {self.get_data_length()}\n"
                f"  Timing Info:         {self.timing_info}\n"
                f"  Segment Number:      {self.segment_number}\n"
                f"  Function Code:       {self.function_code:02X}\n"
                f"  Address Code:        0x{self.address_code:04X}\n")
    
    def set_timing_info(self, value):
        # Convert integer to 6 bytes in big-endian order
        timing_bytes = value.to_bytes(6, byteorder='big')
        for i in range(6):
            self.timing_info[i] = timing_bytes[i]

    def get_timing_info(self):
        # Convert 6 bytes back to integer
        return int.from_bytes(bytes(self.timing_info), byteorder='big')
    
    def get_data_length(self):
        """
        Get data length field converted to little-endian.
        Returns the data length value in little-endian format.
        """
        return int.from_bytes(self.data_length.to_bytes(2, byteorder='big'), byteorder='little')
    def set_data_length(self, length):
        """
        Set data length field, converting from little-endian to big-endian if needed.
        Args:
            length (int): The data length value to set
        """
        # Convert little-endian input to big-endian for storage
        self.data_length = ((length & 0xFF) << 8) | ((length >> 8) & 0xFF)

class CCSDS_Packet:
    def __init__(self, header: CCSDS_Packet_Header, data: bytes = None, crc: int = None):
        """
        Initialize the CCSDS packet with a header and dynamic-length data.

        Args:
            header (CCSDS_Packet_Header): The fixed-length header.
            data (bytes): The variable-length payload data.
            crc (int, optional): CRC32 checksum value. If None, will be calculated.
        """
        self.header = header
        self.data = data if data is not None else bytes()
        self.crc32 = crc if crc is not None else self.calculate_crc()

    def calculate_crc(self):
        """
        Calculate and update the CRC32 field, which includes the header and data.
        """
        # Pack the header into bytes
        header_bytes = bytes(self.header)

        # Combine header and data for CRC calculation
        packet_body = header_bytes + self.data
        print("Complete packet bytes:")
        print(" ".join([f"{b:02X}" for b in packet_body]))
    
        return zlib.crc32(packet_body) & 0xFFFFFFFF

    def to_bytes(self):
        """
        Convert the entire packet (header + data + CRC) to bytes.

        Returns:
            bytes: The serialized packet.
        """
        # Convert the header to bytes
        header_bytes = bytes(self.header)

        # Combine header, data, and CRC into a single byte array
        crc_bytes = self.crc32.to_bytes(4, byteorder='big')
        return header_bytes + self.data + crc_bytes

    def __str__(self):
        """
        Return a human-readable representation of the CCSDS packet.
        """
        return (str(self.header) +
                f"Data (Hex): \t{' '.join(f'{b:02X}' for b in self.data)}\n"
                f"CRC32:      \t0x{self.crc32:08X}\n")

    @staticmethod
    def from_bytes(buffer: bytes):
        """
        Deserialize a chunk of bytes into a CCSDS packet and validate its CRC.

        Args:
            data (bytes): The received binary data.

        Returns:
            CCSDS_Packet: The deserialized packet object if valid.

        Raises:
            ValueError: If the data is invalid or the CRC does not match.
        """
        # Ensure the data is at least long enough for a header and CRC
        if len(buffer) < sizeof(CCSDS_Packet_Header) + 4 :
            raise ValueError("Invalid packet: Data is too short.")
        if len(buffer) > 16 + 256 + 4:
            raise ValueError("Invalid packet: Data is too long.")
        
        # Extract the header
        header_bytes = buffer[:sizeof(CCSDS_Packet_Header)]
        header = CCSDS_Packet_Header.from_buffer_copy(header_bytes)
        # Extract the data, 10 is sencond header , 4 is crc
        data = buffer[sizeof(header):sizeof(header) + header.get_data_length() - 10 - 4]
        # Extract CRC
        received_crc = int.from_bytes(buffer[-4:], byteorder='big')

        # Recalculate CRC
        print(f"{sizeof(header)}, {len(data)}")
        ba = header_bytes + data
        print(" ".join([f"{b:02X}" for b in ba]))
        recalculated_crc = zlib.crc32(header_bytes + data) & 0xFFFFFFFF

        # Verify CRC
        if received_crc != recalculated_crc:
            raise ValueError(f"Invalid CRC: Expected 0x{received_crc:08X}, got 0x{recalculated_crc:08X}.")

        # Create and return the packet object
        packet = CCSDS_Packet(header, data, received_crc)
        
        return packet





    @staticmethod
    def from_file(file_path: str):
        """
        Create a CCSDS_Packet object from a text file.

        Args:
            file_path (str): Path to the text file containing the CCSDS packet details.

        Returns:
            CCSDS_Packet: The reconstructed packet.

        Raises:
            ValueError: If the text file is improperly formatted.
        """
        with open(file_path, "r") as file:
            lines = file.readlines()

        # Dictionary to hold parsed fields
        file_dic = {}
        data = None
        crc = None

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Remove inline comments
            line = line.split("#", 1)[0].strip()

            # Separate key and value by the first occurrence of ":"
            if ":" in line:
                key, value = line.split(":", 1)  # Split only on the first ":"
                key = key.lower().replace(" ", "_")  # Normalize key
                value = value.strip()  # Clean up whitespace around the value
                file_dic[key] = value

        # Handle dynamic values and conversions
        if "packet_type" in file_dic:
            if file_dic["packet_type"] == "TC":
                file_dic["packet_type"] = 1
            elif file_dic["packet_type"] == "TM":
                file_dic["packet_type"] = 0
            else:
                raise ValueError("Invalid Packet Type: Must be 'TC' or 'TM'.")

        if "timing_info" in file_dic and file_dic["timing_info"] == "?":
            # Use current UTC time in microseconds
            file_dic["timing_info"] = int(time.time() * 1e6)

        if "dynamic_data_(hex)" in file_dic:
            data = bytes.fromhex(file_dic["dynamic_data_(hex)"])
        else:
            raise ValueError("Missing Dynamic Data (Hex).")

        if "crc32" in file_dic and file_dic["crc32"] == "?":
            crc = None  # Will calculate later
        elif "crc32" in file_dic:
            crc = int(file_dic["crc32"], 16)

        if "data_length" in file_dic and file_dic["data_length"] == "?":
            # Include length of secondary header + length of the data + the CRC (4 bytes)
            file_dic["data_length"] = 10 + len(data) + 4

        # Ensure required fields are present
        required_fields = [
            "version_number", "packet_type", "second_header_flag",
            "application_id", "group_flag", "sequence_number",
            "data_length", "timing_info", "segment_number",
            "function_code", "address_code"
        ]
        for field in required_fields:
            if field not in file_dic:
                raise ValueError(f"Missing required field: {field}")

        # Construct the header
        header = CCSDS_Packet_Header()
        header.version_number = int(file_dic["version_number"])
        header.packet_type = int(file_dic["packet_type"])
        header.second_header_flag = int(file_dic["second_header_flag"])
        header.apid = int(file_dic["application_id"], 16)
        header.group_flag = int(file_dic["group_flag"])
        header.sequence_number = int(file_dic["sequence_number"])
        length = int(file_dic["data_length"])
        header.set_data_length(length)
        header.segment_number = int(file_dic["segment_number"])
        header.function_code = int(file_dic["function_code"], 16)
        header.address_code = int(file_dic["address_code"], 16)

        # Create the packet
        packet = CCSDS_Packet(header, data)

        # Calculate CRC if needed
        if crc is None:
            packet.calculate_crc()
        else:
            packet.crc32 = crc

        # Validate the calculated CRC against the file
        if crc is not None and packet.crc32 != crc:
            raise ValueError(f"Invalid CRC: Calculated 0x{packet.crc32:08X}, Expected 0x{crc:08X}.")

        return packet


if __name__ == "__main__":
    # Create a CCSDS packet header
    header = CCSDS_Packet_Header()
    header.version_number = 1
    header.packet_type = 0
    header.second_header_flag = 1
    header.apid = 0x7FF
    header.group_flag = 3
    header.sequence_number = 100
    header.set_timing_info(0x123456789ABC)
    header.segment_number = 1
    header.function_code = 5
    header.address_code = 0x1234

    # Create data payload
    data = b"Hello!"

    # Create a CCSDS packet with the header and data
    packet = CCSDS_Packet(header, data)

    # Calculate CRC for the entire packet
    packet.calculate_crc()

    # Display the packet
    print(packet)

    # Serialize to bytes
    packet_bytes = packet.to_bytes()
    print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")

    print("\n---- create CCSDS package from buffer ----")
    try:
        received_packet = CCSDS_Packet.from_bytes(packet_bytes)
        received_packet.header.version_number = 0
        print("Received Packet is valid:")
        print(received_packet)

        # Serialize to bytes
        packet_bytes = received_packet.to_bytes()
        print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")
    except ValueError as e:
        print("Error:", e)
    
    print("\n---- create CCSDS package from file ----")
    try:
        packet = CCSDS_Packet.from_file("y.sds")
        print("Successfully loaded packet:")
        print(packet)
    except ValueError as e:
        print("Error:", e)

r"""
PS C:\Users\xianw\py2> python3 ccsds_pkg.py
CCSDS_Packet_Header:
  Version Number:      1
  Packet Type:         0
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         6
  Timing Info:         20015998343868
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0x7EA4C02B

Serialized Packet (Hex): 2F FF C0 64 00 06 12 34 56 78 9A BC 00 00 01 05 12 34 48 65 6C 6C 6F 21 7E A4 C0 2B

---- create CCSDS package from buffer ----
Received Packet is valid:
CCSDS_Packet_Header:
  Version Number:      0
  Packet Type:         0
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         6
  Timing Info:         20015998343868
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0x7EA4C02B

Serialized Packet (Hex): 0F FF C0 64 00 06 12 34 56 78 9A BC 00 00 01 05 12 34 48 65 6C 6C 6F 21 7E A4 C0 2B

---- create CCSDS package from file ----
Successfully loaded packet:
CCSDS_Packet_Header:
  Version Number:      0
  Packet Type:         1
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         6
  Timing Info:         43285971460208
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0x142DFA9A

PS C:\Users\xianw\py2>
"""