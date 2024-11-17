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

    @staticmethod
    def parse_text_file(file_path):
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

        # Post-process to ensure values are converted correctly or auto-generated
        if "APID" in primary_header:
            primary_header["APID"] = int(primary_header["APID"])
        if "Segment Number" in secondary_header:
            secondary_header["Segment Number"] = int(secondary_header["Segment Number"])
        if "Function Code" in secondary_header:
            secondary_header["Function Code"] = int(secondary_header["Function Code"])
        if "Address Code" in secondary_header:
            secondary_header["Address Code"] = int(secondary_header["Address Code"], 16)
        if "Data (Hex)" in data_field:
            data_hex = data_field["Data (Hex)"].replace("0x", "").replace(",", "").split()
            data_field["Data (Hex)"] = bytes(int(byte, 16) for byte in data_hex)
        if "Time Code" in secondary_header:
            if secondary_header["Time Code"] == "?":
                # Auto-generate Time Code as current UTC time in microseconds
                secondary_header["Time Code"] = int(time.time() * 1e6)
            else:
                secondary_header["Time Code"] = int(secondary_header["Time Code"])
        if "Packet Data Length" in primary_header:
            if primary_header["Packet Data Length"] == "?":
                # Auto-calculate Packet Data Length: data length + secondary header size - 1
                primary_header["Packet Data Length"] = len(data_field["Data (Hex)"]) + 10 - 1
            else:
                primary_header["Packet Data Length"] = int(primary_header["Packet Data Length"])
        if "CRC32" in data_field:
            if data_field["CRC32"] == "?":
                # Auto-calculate CRC32
                packet_body = (
                    struct.pack(
                        ">HHH",
                        (0 << 13) | (0 << 12) | (1 << 11) | primary_header["APID"],
                        (3 << 14) | (0),  # Default sequence flags and count
                        primary_header["Packet Data Length"],
                    )
                    + struct.pack(
                        ">IHBBH",
                        secondary_header["Time Code"] & 0xFFFFFFFF,  # Lower 32 bits of time
                        (secondary_header["Time Code"] >> 32) & 0xFFFF,  # Upper 16 bits
                        secondary_header["Segment Number"],
                        secondary_header["Function Code"],
                        secondary_header["Address Code"],
                    )
                    + data_field["Data (Hex)"]
                )
                calculated_crc = zlib.crc32(packet_body) & 0xFFFFFFFF
                data_field["CRC32"] = calculated_crc
            else:
                # Convert provided CRC32
                data_field["CRC32"] = int(data_field["CRC32"], 16)

        return primary_header, secondary_header, data_field


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
        print(f"Data Length:               {len(self.data)}")
        print(f"Data (Hex):                {self.data.hex()}")
        print(f"Data (ASCII):              {self.data.decode('ascii', errors='replace')}")
        print(f"CRC32:                     {hex(self.crc32)}")

    def print_hex(self):
        print("Full CCSDS Package (Hex):")
        print(" ".join([f"{byte:02X}" for byte in self.packet]))


if __name__ == "__main__":
    # Example usage with manual input
    apid = 123
    segment_number = 1
    function_code = 5
    address_code = 0x1234
    data = b"Hello, CCSDS!"

    ccsds_instance = CCSDS(apid, segment_number, function_code, address_code, data)
    ccsds_instance.show_fields()
    ccsds_instance.print_hex()

    # Example usage with file input
    input_file = "ccsds_input.txt"
    ccsds_from_file = CCSDS.from_file(input_file)
    print("\nPacket from file:")
    ccsds_from_file.show_fields()
    ccsds_from_file.print_hex()


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
Time Code:                 43021509055976
Segment Number:            1
Function Code:             5
Address Code:              0x1234

--- Data Field ---
Data Length:               13
Data (Hex):                48656c6c6f2c20434353445321
Data (ASCII):              Hello, CCSDS!
CRC32:                     0x7059d39
Full CCSDS Package (Hex):
08 7B C0 00 00 1A B9 C3 D5 E8 27 20 01 05 12 34 48 65 6C 6C 6F 2C 20 43 43 53 44 53 21 07 05 9D 39

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
Time Code:                 43021509057480
Segment Number:            1
Function Code:             5
Address Code:              0x1234

--- Data Field ---
Data Length:               3
Data (Hex):                5678ab
Data (ASCII):              Vx�
CRC32:                     0xca4abe04
Full CCSDS Package (Hex):
08 7B C0 01 00 10 B9 C3 DB C8 27 20 01 05 12 34 56 78 AB CA 4A BE 04
PS C:\Users\xianw\py1>
"""
