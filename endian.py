import sys
print(sys.byteorder)

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

