import struct
import time
import zlib  # For CRC32 calculation
import json

class CCSDS:
    sequence_counter = 0  # Class-level counter for sequence count

    def __init__(self, apid, segment_number, function_code, address_code, data):
        # Validate data size
        max_data_length = 0xFFFF - 14  # Max CCSDS packet length minus headers + CRC
        if len(data) > max_data_length:
            raise ValueError(f"Data size exceeds the maximum of {max_data_length} bytes")

        # Primary header fields
        self.version = 0
        self.type = 0
        self.secondary_header_flag = 1
        self.apid = apid & 0x7FF
        self.sequence_flags = 3
        self.sequence_count = CCSDS.sequence_counter
        CCSDS.sequence_counter = (CCSDS.sequence_counter + 1) & 0x3FFF  # Increment safely
        self.packet_data_length = len(data) + 14 - 1  # 10 bytes secondary header + 4 bytes CRC

        # Secondary header fields
        self.time_code = int(time.time() * 1e6) & 0xFFFFFFFFFFFF  # 48-bit time
        self.segment_number = segment_number & 0xFF
        self.function_code = function_code & 0xFF
        self.address_code = address_code & 0xFFFF

        # Data field
        self.data = data
        self.crc32 = 0

        # Construct the packet
        self.packet = self._pack()

    def _pack(self):
        # Construct primary header (6 bytes)
        primary_header = struct.pack(
            '>HHH',
            (self.version << 13) | (self.type << 12) |
            (self.secondary_header_flag << 11) | self.apid,
            (self.sequence_flags << 14) | self.sequence_count,
            self.packet_data_length
        )

        # Construct secondary header (10 bytes)
        secondary_header = struct.pack(
            '>IHBBH',
            self.time_code & 0xFFFFFFFF,  # Lower 32 bits
            (self.time_code >> 32) & 0xFFFF,  # Upper 16 bits
            self.segment_number,
            self.function_code,
            self.address_code
        )

        # Combine all parts without CRC
        packet_without_crc = primary_header + secondary_header + self.data

        # Calculate CRC32
        self.crc32 = zlib.crc32(packet_without_crc) & 0xFFFFFFFF  # Ensure it's unsigned

        # Append CRC32 to the packet
        return packet_without_crc + struct.pack('>I', self.crc32)

    @staticmethod
    def decompose(packet):
        if len(packet) < 20:  # Minimum length validation: 16 bytes header + 4 bytes CRC
            raise ValueError("Packet is too short to be a valid CCSDS packet")

        # Extract and verify CRC32
        packet_body = packet[:-4]
        received_crc32 = struct.unpack('>I', packet[-4:])[0]
        calculated_crc32 = zlib.crc32(packet_body) & 0xFFFFFFFF

        if received_crc32 != calculated_crc32:
            raise ValueError(f"CRC mismatch! Received: {received_crc32:08X}, Calculated: {calculated_crc32:08X}")

        # Unpack primary header
        primary_header = struct.unpack('>HHH', packet[:6])
        version = (primary_header[0] >> 13) & 0x07
        packet_type = (primary_header[0] >> 12) & 0x01
        secondary_header_flag = (primary_header[0] >> 11) & 0x01
        apid = primary_header[0] & 0x7FF
        sequence_flags = (primary_header[1] >> 14) & 0x03
        sequence_count = primary_header[1] & 0x3FFF
        packet_data_length = primary_header[2]

        # Unpack secondary header
        secondary_header = struct.unpack('>IHBBH', packet[6:16])
        time_code = secondary_header[0] | (secondary_header[1] << 32)
        segment_number = secondary_header[2]
        function_code = secondary_header[3]
        address_code = secondary_header[4]

        # Extract data
        data = packet[16:-4]

        return {
            "primary_header": {
                "version": version,
                "packet_type": "Command" if packet_type else "Telemetry",
                "secondary_header_flag": bool(secondary_header_flag),
                "apid": apid,
                "sequence_flags": sequence_flags,
                "sequence_count": sequence_count,
                "packet_data_length": packet_data_length
            },
            "secondary_header": {
                "time_code": time_code,
                "segment_number": segment_number,
                "function_code": function_code,
                "address_code": f"0x{address_code:04X}"  # Show in hexadecimal
            },
            "data": {
                "length": len(data),
                "hex": data.hex(),
                "ascii": data.decode('ascii', errors='replace')
            },
            "crc32": f"0x{received_crc32:08X}"  # Display CRC32 in hexadecimal
        }

    def show_fields(self):
        print("CCSDS Packet Fields:")
        print("\n--- Primary Header ---")
        print(f"Version Number:            {self.version}")
        print(f"Packet Type:               {'Telemetry' if self.type == 0 else 'Command'}")
        print(f"Secondary Header Flag:     {'Present' if self.secondary_header_flag else 'Absent'}")
        print(f"APID:                      {self.apid}")
        print(f"Sequence Flags:            {self.sequence_flags}")
        print(f"Sequence Count:            {self.sequence_count}")
        print(f"Packet Data Length:        {self.packet_data_length}")
        
        print("\n--- Secondary Header ---")
        print(f"Time Code:                 {self.time_code}")
        print(f"Segment Number:            {self.segment_number}")
        print(f"Function Code:             {self.function_code}")
        print(f"Address Code:              {hex(self.address_code)}")
        
        print("\n--- Data Field ---")
        print(f"Data Length:               {len(self.data)}")
        print(f"Data (Hex):                {self.data.hex()}")
        print(f"Data (ASCII):              {self.data.decode('ascii', errors='replace')}")
        print(f"crc32:                     {hex(self.crc32)}")

if __name__ == "__main__":
    apid = 123
    segment_number = 1
    function_code = 5
    address_code = 0x1234
    data = b"Hello, CCSDS!"

    ccsds_instance = CCSDS(apid, segment_number, function_code, address_code, data)
    ccsds_packet = ccsds_instance.packet

    print("CCSDS Packet with CRC32:")
    print(" ".join([f"{b:02X}" for b in ccsds_packet]))

    # Decompose the packet
    decomposed = CCSDS.decompose(ccsds_packet)
    print("\nDecomposed CCSDS Packet (Aligned):")

    for section, fields in decomposed.items():
        print(f"{section}:")
        if isinstance(fields, dict):  # Check if fields is a dictionary
            for key, value in fields.items():
                print(f"    {key:20s} : {value}")
        else:  # Handle non-dictionary fields like crc32
            print(f"    {fields:20s}")


    # Verify by showing fields from the original packet
    print("\nOriginal Packet Fields:")
    ccsds_instance.show_fields()