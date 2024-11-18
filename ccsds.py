import struct
import time
import zlib


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

    @classmethod
    def from_file(cls, input_file):
        primary_header, secondary_header, data_field = cls.parse_text_file(input_file)

        # Use already processed fields directly
        apid = primary_header["APID"]
        segment_number = secondary_header["Segment Number"]
        function_code = secondary_header["Function Code"]
        address_code = secondary_header["Address Code"]  # Already an integer

        data = data_field["Data (Hex)"]  # Already a bytes object

        # Auto-generate fields if marked as "?"
        time_code = secondary_header.get("Time Code")
        custom_crc = data_field.get("CRC32")

        return cls(apid, segment_number, function_code, address_code, data)


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
    def parse_text_file(self, file_path):
        import zlib  # For CRC32 calculation
        import time  # For time generation

        with open(file_path, "r") as file:
            lines = file.readlines()

        primary_header = {}
        secondary_header = {}
        data_field = {}

        section = None
        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove comments (anything after #)
            if "#" in line:
                line = line.split("#", 1)[0].strip()

            # Identify section headers
            if line.startswith("---"):
                section = line
                continue

            # Parse key-value pairs
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if section == "--- Primary Header ---":
                    primary_header[key] = value
                elif section == "--- Secondary Header ---":
                    secondary_header[key] = value
                elif section == "--- Data Field ---":
                    data_field[key] = value

        # Update instance variables directly
        if "APID" in primary_header:
            self.apid = int(primary_header["APID"])
        if "Segment Number" in secondary_header:
            self.segment_number = int(secondary_header["Segment Number"])
        if "Function Code" in secondary_header:
            self.function_code = int(secondary_header["Function Code"])
        if "Address Code" in secondary_header:
            self.address_code = int(secondary_header["Address Code"], 16)
        if "Data (Hex)" in data_field:
            data_hex = data_field["Data (Hex)"].replace("0x", "").replace(",", "").split()
            self.data = bytes(int(byte, 16) for byte in data_hex)
        if "Time Code" in secondary_header:
            if secondary_header["Time Code"] == "?":
                # Auto-generate Time Code as current UTC time in microseconds
                self.time_code = int(time.time() * 1e6)
            else:
                self.time_code = int(secondary_header["Time Code"])
        else:
            self.time_code = int(time.time() * 1e6)
        if "Packet Data Length" in primary_header:
            if primary_header["Packet Data Length"] == "?":
                # Auto-calculate Packet Data Length: data length + secondary header size - 1
                self.packet_data_length = len(self.data) + 10 - 1
            else:
                self.packet_data_length = int(primary_header["Packet Data Length"])
        if "CRC32" in data_field:
            if data_field["CRC32"] == "?":
                # Auto-calculate CRC32
                packet_body = (
                    struct.pack(
                        ">HHH",
                        (0 << 13) | (0 << 12) | (1 << 11) | self.apid,
                        (3 << 14) | (0),  # Default sequence flags and count
                        self.packet_data_length,
                    )
                    + struct.pack(
                        ">IHBBH",
                        self.time_code & 0xFFFFFFFF,  # Lower 32 bits of time
                        (self.time_code >> 32) & 0xFFFF,  # Upper 16 bits
                        self.segment_number,
                        self.function_code,
                        self.address_code,
                    )
                    + self.data
                )
                self.crc32 = zlib.crc32(packet_body) & 0xFFFFFFFF
            else:
                # Convert provided CRC32
                self.crc32 = int(data_field["CRC32"], 16)

        # Update the packet after all fields are set
        self.packet = self._pack()

    def verify_crc(self, ccsds_package):
        """
        Verify the CRC32 of a given CCSDS package.

        Args:
            ccsds_package (bytes): The full CCSDS package to verify.

        Returns:
            bool: True if the CRC32 matches, False otherwise.
        """
        # Ensure the package is long enough to contain CRC32
        if len(ccsds_package) < 6 + 10 + 4:
            raise ValueError("The package is too short to contain a valid CRC32.")

        # Extract the CRC32 from the package (last 4 bytes)
        extracted_crc = int.from_bytes(ccsds_package[-4:], byteorder='big')

        # Calculate CRC32 of the package excluding the last 4 bytes (the CRC itself)
        calculated_crc = zlib.crc32(ccsds_package[:-4]) & 0xFFFFFFFF

        # Compare and return the result
        return extracted_crc == calculated_crc

    def show_fields(self):
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
        print(f"Data (Hex):                {self.data.hex()}")
        print(f"Data (ASCII):              {self.data.decode('ascii', errors='replace')}")
        print(f"CRC32:                     {hex(self.crc32)}")

    def print_hex(self):
        print("Full CCSDS Package (Hex):")
        print(" ".join([f"{byte:02X}" for byte in self.packet]))


import argparse

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="CCSDS Packet Generator and Verifier")
    parser.add_argument("--file", type=str, help="Path to the input file for CCSDS packet generation")
    args = parser.parse_args()

    if args.file:

        
        # Example usage with file input
        input_file = args.file
        print(f"\nProcessing file: {input_file}")
        ccsds_from_file = CCSDS(0, 0, 0, 0, b"")  # Create an empty instance
        ccsds_from_file.parse_text_file(input_file)  # Update fields from the file
        print("\nPacket from file:")
        ccsds_from_file.show_fields()
        ccsds_from_file.print_hex()
        # Verify CRC for the packet from the file
        is_valid_file = ccsds_from_file.verify_crc(ccsds_from_file.packet)
        print(f"\nCRC32 verification for file packet: {'Passed' if is_valid_file else 'Failed'}")
    else:
        # Example usage with manual input
        apid = 123
        segment_number = 1
        function_code = 5
        address_code = 0x1234
        data = b"CCSDS!"

        print("\nGenerating CCSDS packet with manual input:")
        ccsds_instance = CCSDS(apid, segment_number, function_code, address_code, data)
        ccsds_instance.show_fields()
        ccsds_instance.print_hex()
        # Verify CRC for the manually created packet
        is_valid = ccsds_instance.verify_crc(ccsds_instance.packet)
        print(f"\nCRC32 verification for manual packet: {'Passed' if is_valid else 'Failed'}")

r"""
PS C:\Users\xianw\py1> python3 .\ccsds.py

--- Primary Header ---
Version Number:            0
Packet Type:               Telemetry
Secondary Header Flag:     Present
APID:                      123
Sequence Flags:            3
Sequence Count:            0
Packet Data Length:        26

--- Secondary Header ---
Time Code:                 43023421685677
Segment Number:            1
Function Code:             5
Address Code:              0x1234

--- Data Field ---
Data Length:               13
Data (Hex):                48656c6c6f2c20434353445321
Data (ASCII):              Hello, CCSDS!
CRC32:                     0xe420ffd5
Full CCSDS Package (Hex):
08 7B C0 00 00 1A 2B C4 3F AD 27 21 01 05 12 34 48 65 6C 6C 6F 2C 20 43 43 53 44 53 21 E4 20 FF D5

CRC32 verification for manual packet: Passed

Packet from file:

--- Primary Header ---
Version Number:            0
Packet Type:               Telemetry
Secondary Header Flag:     Present
APID:                      123
Sequence Flags:            3
Sequence Count:            1
Packet Data Length:        16

--- Secondary Header ---
Time Code:                 43023421687181
Segment Number:            1
Function Code:             5
Address Code:              0x1234

--- Data Field ---
Data Length:               3
Data (Hex):                5678ab
Data (ASCII):              Vx�
CRC32:                     0xf5bb7725
Full CCSDS Package (Hex):
08 7B C0 01 00 10 2B C4 45 8D 27 21 01 05 12 34 56 78 AB F5 BB 77 25

CRC32 verification for file packet: Passed
"""
