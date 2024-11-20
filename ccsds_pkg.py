from ctypes import *

class CCSDS_Packet_Header(BigEndianStructure):
    _pack_ = 1
    _fields_ = [
        #primary header
        ("version_number", c_uint16, 3),
        ("packet_type", c_uint16, 1),
        ("second_header_flag", c_uint16, 1),
        ("apid", c_uint16, 11),
        ("group_flag", c_uint16, 2),
        ("sequence_number", c_uint16, 14),
        ("data_length", c_uint16, 16),
        #second header
        ("timing_info", c_uint64, 48),
        ("segment_number", c_uint64, 8),
        ("function_code", c_uint64, 8),
        ("address_code", c_uint16, 16),
        # 256 uint8_t array
        ("data", c_uint8 * 16)
    ]

    def __str__(self):
        return (f"CCSDS_Packet_Header:\n"
                f"  Version Number: {self.version_number}\n"
                f"  Packet Type: {self.packet_type}\n"
                f"  Second Header Flag: {self.second_header_flag}\n"
                f"  Application ID: 0x{self.apid:04X}\n"
                f"  Group Flag: {self.group_flag}\n"
                f"  Sequence Number: {self.sequence_number}\n"
                f"  Data Length: {self.data_length}\n"
                f"  Timing Info: {self.timing_info}\n"
                f"  Segment Number: {self.segment_number}\n"
                f"  Function Code: 0x{self.function_code:02X}\n"
                f"  Address Code: 0x{self.address_code:04X}")
    


if __name__ == "__main__":
    # Create an instance of the structure
    header = CCSDS_Packet_Header()

    # Set some values
    header.version_number = 0
    header.packet_type = 0
    header.second_header_flag = 0
    header.app_id = 0xee
    header.group_flag = 0
    header.sequence_number = 0xcc
    header.data_length = 0xff

    header.timing_info = 0xff
    header.segment_number = 0x22
    header.function_code = 0x12
    header.address_code  = 0x23

    # Print the structure
    print(header)
    # Get the size in bytes
    size_of_header = sizeof(CCSDS_Packet_Header)

    # Print the size
    print(f"The size of CCSDS_Packet_Header is {size_of_header} bytes")

    # Access the data_length field
    print(f"Data Length: {header.data_length}")

    # Convert the structure to bytes and print
    raw_bytes = bytes(header)
    print("Raw bytes:")
    print(raw_bytes.hex())

    # Optionally, print each byte individually
    print("Individual bytes:")
    for byte in raw_bytes:
        print(f"{byte:02x}", end=" ")
    print()

r"""
PS C:\Users\x-luo\c_cpp\space\python> python .\ccsds_header.py
CCSDS_Packet_Header:
  Version Number: 0
  Packet Type: 0
  Second Header Flag: 0
  Application ID: 0
  Group Flag: 0
  Sequence Number: 204
  Data Length: 255
  Timing Info: 0
  Segment Number: 0
  Function Code: 0
  Address Code: 0
The size of CCSDS_Packet_Header is 16 bytes
Data Length: 255
Raw bytes:
000000cc00ff00000000000000000000
Individual bytes:
00 00 00 cc 00 ff 00 00 00 00 00 00 00 00 00 00
PS C:\Users\x-luo\c_cpp\space\python>

"""