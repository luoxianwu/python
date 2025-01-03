from ctypes import *
import zlib
import re

import time
import socket


class CCSDS_Packet_Header(BigEndianStructure):
    PRI_HDR_LEN  = 6  #primary header length
    SEC_HDR_LEN  = 10 #secondary header length
    CRC_LEN      = 4  # Constant for CRC32 length in bytes
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
                f"  Data Length:         {self.data_length}\n"
                f"  Timing Info:         {self.get_timing_info()}\n"
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
        Get data length field converted to host byte order (little-endian).
        """
        return socket.ntohs(self.data_length)
    
    def set_data_length(self, length):
        """
        Set data length field, converting from host byte order to big-endian.
        """
        self.data_length = socket.htons(length)


class CCSDS_Packet:
    STATE_IDLE = 0
    STATE_SYNC = 1
    STATE_PRIMARY_HEADER = 2
    STATE_SECONDARY_HEADER = 3
    STATE_DATA = 4
    STATE_VALID = 5
    STATE_CRC_ERR = 6

    SYNC_BYTES = 2

    def __init__(self, header: CCSDS_Packet_Header, data: bytes = None, crc: int = None):
        """
        Initialize the CCSDS packet with a header and dynamic-length data.

        Args:
            header (CCSDS_Packet_Header): The fixed-length header.
            data (bytes): The variable-length payload data.
            crc (int, optional): CRC32 checksum value. If None, will be calculated.
        """
        self.pkt_sync = 0x55AA
        self.header = header
        self.data = data if data is not None else bytes()
        if (self.header.data_length == 0):
            self.header.data_length = self.header.SEC_HDR_LEN + len(self.data) + self.header.CRC_LEN
        self.crc32 = crc if crc is not None else self.calculate_crc()
        
        self.rx_state = CCSDS_Packet.STATE_IDLE
        self.rx_count = 0
        

    def calculate_crc(self):
        """
        Calculate and update the CRC32 field, which includes the header and data.
        """

        # Pack the header into bytes
        header_bytes = bytes(self.header)

        # Combine header and data for CRC calculation
        packet_body = header_bytes + self.data
        print(" ".join([f"{b:02X}" for b in packet_body]))    
        crc = zlib.crc32(packet_body) & 0xFFFFFFFF
        print(f"{crc:08X}")
        return crc

    def to_bytes(self):
        """
        Convert the entire packet (header + data + CRC) to bytes.

        Returns:
            bytes: The serialized packet.
        """
        # Pack the sync word into bytes (2 bytes, little-endian)
        sync_bytes = self.pkt_sync.to_bytes(2, byteorder='big')

        # Convert the header to bytes
        header_bytes = bytes(self.header)

        # Combine header, data, and CRC into a single byte array
        crc_bytes = self.crc32.to_bytes(4, byteorder='big')
        return sync_bytes + header_bytes + self.data + crc_bytes

    def __str__(self):
        """
        Return a human-readable representation of the CCSDS packet.
        """
        return (f"SYNC:       \t0x{self.pkt_sync:04X}\n" +
                str(self.header) +
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
        user_data_len = header.data_length - header.SEC_HDR_LEN - header.CRC_LEN + 1

        data = buffer[sizeof(header):sizeof(header) + user_data_len]
        # Extract CRC
        received_crc = int.from_bytes(buffer[-4:], byteorder='big')

        print(f"{sizeof(header)}, {len(data)}")
        ba = header_bytes + data
        print(" ".join([f"{b:02X}" for b in ba]))

        # Recalculate CRC ( exclude SYNC word and CRC32 )
        crc_cal_data = buffer[ :-4 ]
        calculated_crc = zlib.crc32(crc_cal_data) & 0xFFFFFFFF
        # Verify CRC
        if received_crc != calculated_crc:
            print(f"Invalid CRC: ExpectedReceived CRC 0x{received_crc:08X}, Calculated CRC 0x{calculated_crc:08X}.")
        else:
             print(f"Valid CRC : 0x{received_crc:08X}")
                   
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
            # Include length of secondary header + length of the data + the CRC (4 bytes), - 1 by define
            file_dic["data_length"] = 10 + len(data) + 4 - 1

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
        header.data_length = length
        time = int(file_dic["timing_info"])
        header.set_timing_info(time)
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
    

    def reset_receive_packet(self):
        self.state = CCSDS_Packet.STATE_IDLE
        self.bytes_received = 0
        self.data_length = 0

    def get_packet(ser):
        packet = bytearray()
        state = CCSDS_Packet.STATE_IDLE
        bytes_received = 0
        data_length = 0
        valid = False
        print("\nReceive Packet...")
        while True:
            byte = ser.read(1)
            if not byte:
                break
            
            packet.extend(byte)
            bytes_received += 1
            print( byte.hex().upper() + " ", end="")

            if state == CCSDS_Packet.STATE_IDLE:
                state = CCSDS_Packet.STATE_SYNC

            elif state == CCSDS_Packet.STATE_SYNC:
                if bytes_received == 2:
                    if packet[0] == 0x55 and packet[1] == 0xAA:
                        state = CCSDS_Packet.STATE_PRIMARY_HEADER
                    else:
                        packet[0] = packet[1]
                        bytes_received = 1

            elif state == CCSDS_Packet.STATE_PRIMARY_HEADER:
                if bytes_received == CCSDS_Packet.SYNC_BYTES + CCSDS_Packet_Header.PRI_HDR_LEN:
                    data_length = (packet[-2] << 8) + packet[-1] + 1
                    state = CCSDS_Packet.STATE_SECONDARY_HEADER

            elif state == CCSDS_Packet.STATE_SECONDARY_HEADER:
                if bytes_received == (CCSDS_Packet.SYNC_BYTES + 
                                      CCSDS_Packet_Header.PRI_HDR_LEN + 
                                      CCSDS_Packet_Header.SEC_HDR_LEN):
                    state = CCSDS_Packet.STATE_DATA

            elif state == CCSDS_Packet.STATE_DATA:
                if bytes_received == (CCSDS_Packet.SYNC_BYTES + 
                                      CCSDS_Packet_Header.PRI_HDR_LEN + 
                                      data_length):
                    print(f"\nreceived {bytes_received} bytes.")
                    crc_calculated = zlib.crc32(packet[2:-CCSDS_Packet_Header.CRC_LEN]) & 0xFFFFFFFF
                    crc_received = int.from_bytes(packet[-CCSDS_Packet_Header.CRC_LEN:], 'big')

                    if crc_calculated == crc_received:
                        print("packet CRC valid")
                        valid = True
                    else:
                        print(f"packet CRC: 0x{crc_received:08X}, calculated CRC: 0x{crc_calculated:08X}")
                        valid = False

        
        return valid, packet





if __name__ == "__main__":
    # Create a CCSDS packet header
    header = CCSDS_Packet_Header()
    header.version_number = 1
    header.packet_type = 0
    header.second_header_flag = 1
    header.apid = 0x7FF
    header.group_flag = 3
    header.sequence_number = 100
    header.set_timing_info(98765)
    header.segment_number = 1
    header.function_code = 5
    header.address_code = 0x1234

    # Create data payload
    data = b"Hello!"

    # Create a CCSDS packet with the header and data
    packet = CCSDS_Packet(header, data)

    # Display the packet
    print(packet)

    # Serialize to bytes
    packet_bytes = packet.to_bytes()
    print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")

    print("\n---- create CCSDS package from buffer(exclusive SYNC word) ----")
    try:
        received_packet = CCSDS_Packet.from_bytes(packet_bytes[2:])
        #received_packet.header.version_number = 0
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
PS C:\Users\x-luo\python> python ccsds_pkg.py
2F FF C0 64 00 14 00 00 00 01 81 CD 01 05 12 34 48 65 6C 6C 6F 21
B535F593
SYNC:           0x55AA
CCSDS_Packet_Header(16) bytes:
  Version Number:      1
  Packet Type:         0
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         20
  Timing Info:         98765
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0xB535F593

Serialized Packet (Hex): 55 AA 2F FF C0 64 00 14 00 00 00 01 81 CD 01 05 12 34 48 65 6C 6C 6F 21 B5 35 F5 93

---- create CCSDS package from buffer(exclusive SYNC word) ----
16, 6
2F FF C0 64 00 14 00 00 00 01 81 CD 01 05 12 34 48 65 6C 6C 6F 21
Received Packet is valid:
SYNC:           0x55AA
CCSDS_Packet_Header(16) bytes:
  Version Number:      1
  Packet Type:         0
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         20
  Timing Info:         98765
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0xB535F593

Serialized Packet (Hex): 55 AA 2F FF C0 64 00 14 00 00 00 01 81 CD 01 05 12 34 48 65 6C 6C 6F 21 B5 35 F5 93

---- create CCSDS package from file ----
19 23 C0 64 00 13 00 00 00 00 00 00 01 01 00 01 48 65 6C 6C 6F 21
A963B27B
19 23 C0 64 00 13 00 00 00 00 00 00 01 01 00 01 48 65 6C 6C 6F 21
A963B27B
Successfully loaded packet:
SYNC:           0x55AA
CCSDS_Packet_Header(16) bytes:
  Version Number:      0
  Packet Type:         1
  Second Header Flag:  1
  Application ID:      0x0123
  Group Flag:          3
  Sequence Number:     100
  Data Length:         19
  Timing Info:         0
  Segment Number:      1
  Function Code:       01
  Address Code:        0x0001
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0xA963B27B

PS C:\Users\x-luo\python>
"""