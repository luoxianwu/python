from ctypes import *

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
        ("timing_info", c_uint8 * 6),
        ("segment_number", c_uint16, 8),
        ("function_code", c_uint16, 8),
        ("address_code", c_uint16, 16)
    ]

# Your byte array
byte_array = b'\x09\x23\x0C\x00\x1D\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

# Create an instance of CCSDS_Packet_Header from the byte array
header = CCSDS_Packet_Header.from_buffer_copy(byte_array)

# Now you can access the fields of the structure
print(f"Version Number: {header.version_number}")
print(f"Packet Type: {header.packet_type}")
print(f"Second Header Flag: {header.second_header_flag}")
print(f"APID: {header.apid}")
print(f"Group Flag: {header.group_flag}")
print(f"Sequence Number: {header.sequence_number}")
print(f"Data Length: {header.data_length}")
print(f"Timing Info: {list(header.timing_info)}")
print(f"Segment Number: {header.segment_number}")
print(f"Function Code: {header.function_code}")
print(f"Address Code: {header.address_code}")