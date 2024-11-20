import struct
import time
import zlib
import argparse
import serial  # Import serial for the standalone function
from ctypes import *
from ccsds_pkg import *

class CCSDS:

    packet = CCSDS_Packet_Header()
    data = b""
    pkg_crc:c_int32 = 0

    sequence_counter = 0  # Class-level counter for sequence count

    def __init__(self, apid, segment_number, function_code, address_code, data):
        # Validate data size
        max_data_length = 0xFFFF - 14  # Max CCSDS packet length minus headers + CRC
        if len(data) > max_data_length:
            raise ValueError(f"Data size exceeds the maximum of {max_data_length} bytes")

        # Primary header fields
        self.packet.version_number = 0
        self.packet.packet_type = 0
        self.packet.second_header_flag = 1
        self.packet.app_id = 0x55
        self.packet.group_flag = 3   #single package
        self.packet.sequence_number = 0xcc
        self.packet.data_length = 10

        # Secondary header fields
        self.packet.timing_info = 0xff
        self.packet.segment_number = 0x22
        self.packet.function_code = 0x12
        self.packet.address_code  = 0x23

        # Data field
        for i, byte in enumerate(data):
            self.packet.data[i] = byte
        self.crc32 = 0


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
    
    @classmethod
    def from_buffer(cls, buffer: bytearray) -> 'cls':
        """Create an instance from a bytearray buffer.

        Args:
            buffer: Raw bytearray data to initialize the object

        Returns:
            New instance initialized from the buffer data

        Raises:
            ValueError: If buffer validation fails
        """
        # Validate buffer format/content
        if not isinstance(buffer, bytearray):
            raise TypeError("Buffer must be a bytearray")

        # Validate buffer size
        min_size = 20  # Example minimum size
        if len(buffer) < min_size:
            raise ValueError(f"Buffer too small, minimum {min_size} bytes required")

        # Validate CCSDS format
        if not CCSDS.is_valid(buffer):
            raise ValueError("Invalid CCSDS buffer format")

        # Create new instance
        instance = cls( 0,0,0,0, b"")

        # Copy buffer data into instance
        instance.packet = bytearray(buffer)  # Make a copy

        return instance


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
    
    def is_valid(package):
        return True


    def show_fields(self):

        print(self.packet)
        print("\n--- Data Field ---")
        # Assuming self.packet.data contains the byte data
        print(f"Data (Hex):\n{' '.join([f'{b:02X}' for b in self.packet.data[:16]])}")
        print(f"Data (ASCII):              {bytes(self.packet.data).decode('ascii', errors='replace')}")
        print(f"CRC32:                     {hex(self.crc32)}")

    
    def print_hex(self):
        print("Full CCSDS Package (Hex):")
        print(" ".join([f"{byte:02X}" for byte in self.packet.data[:16]]))        

def send_packet(packet, port="COM5", baudrate=9600):
    """
    Send a CCSDS packet through a serial COM port.

    Args:
        packet (bytes): The CCSDS packet to send.
        port (str): The COM port to use (e.g., "COM5").
        baudrate (int): The baud rate for serial communication.

    Returns:
        None
    """
    try:
        with serial.Serial(port, baudrate, timeout=5) as ser:
            print(f"Sending packet to {port} at {baudrate} baud...")
            ser.write(packet)
            print("Packet sent successfully!")
    except serial.SerialException as e:
        print(f"Error in serial communication: {e}")


def receive_packet(port="COM5", baudrate=9600, timeout=55):
    """
    Receive a CCSDS packet through a serial COM port.

    Args:
        port (str): The COM port to use (e.g., "COM5").
        baudrate (int): The baud rate for serial communication.
        timeout (int): The read timeout in seconds.

    Returns:
        bytes: The received response packet.
    """
    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            print(f"Waiting for response on {port} at {baudrate} baud...")
            response = ser.read(10)  # Adjust buffer size as needed
            print(f"Response received: {len(response)} bytes")
            return response
    except serial.SerialException as e:
        print(f"Error in serial communication: {e}")
        return None


if __name__ == "__main__":
    # Example usage with manual input
    apid = 123
    segment_number = 1
    function_code = 5
    address_code = 0x1234
    data = b"CCSDS!"
    ccsds = CCSDS(apid, segment_number, function_code, address_code, data)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="CCSDS Packet Generator and Verifier")
    parser.add_argument("--file", type=str, help="Path to the input file for CCSDS packet generation")
    args = parser.parse_args()
    if args.file:
        print(f"\nProcessing file: {args.file}")
        ccsds.parse_text_file(args.file)

    ccsds.show_fields()
    ccsds.print_hex()   

    with serial.Serial(port="COM8", baudrate=115200, timeout=0.05) as ser: #if did not receive char in 100ms, then break out
        bytes_written = ser.write(ccsds.packet)  # Send a test string
        #response = ser.read(1024)  # Read response

        print(f"Send {bytes_written} bytes")

        response = bytearray()
        while True:
            byte = ser.read(1)  # Read 1 byte at a time
            if not byte:  # Timeout occurred (no data received within 1us)
                break
            response.extend(byte)
        hex_output = " ".join(f"{byte:02X}" for byte in response)

        print("Received Packet (Hex):")
        print(hex_output)

        ret_ccsds = CCSDS.from_buffer(response)
        hex_output = " ".join(f"{byte:02X}" for byte in ret_ccsds.packet )
        print("Received Packet (Hex):")
        print(hex_output)




r"""
PS C:\Users\x-luo\c_cpp\space\python> python ccsds.py
CCSDS_Packet_Header:
  Version Number: 0
  Packet Type: 0
  Second Header Flag: 1
  Application ID: 0x0000
  Group Flag: 3
  Sequence Number: 204
  Data Length: 10
  Timing Info: 255
  Segment Number: 34
  Function Code: 0x12
  Address Code: 0x0023

--- Data Field ---
Data (Hex):
43 43 53 44 53 21 00 00 00 00 00 00 00 00 00 00
Data (ASCII):              CCSDS!
CRC32:                     0x0
Full CCSDS Package (Hex):
43 43 53 44 53 21 00 00 00 00 00 00 00 00 00 00
Send 32 bytes
Received Packet (Hex):
08 00 C0 CC 00 0A 00 00 00 00 00 FF 22 12 00 23 43 43 53 44 53 21 00 00 00 00 00 00 00 00 00 00
Received Packet (Hex):
08 00 C0 CC 00 0A 00 00 00 00 00 FF 22 12 00 23 43 43 53 44 53 21 00 00 00 00 00 00 00 00 00 00
PS C:\Users\x-luo\c_cpp\space\python>
"""
