import ctypes
import zlib
import struct  # for packing/unpacking binary data
import time

class ABF_Packet_Header(ctypes.Structure):
    """
    Defines the structure of the ABF packet header.
    """
    _pack_ = 1  # Ensure no padding between fields
    _fields_ = [
        ("pkt_sync", ctypes.c_uint8 * 2),  # Sync bytes (0x55, 0xAA)
        ("packet_length", ctypes.c_uint16),  # Length of the data field (including CRC)
        ("function", ctypes.c_uint8),     # Function code
        ("count", ctypes.c_uint8),        # Packet count
        ("reserved", ctypes.c_uint16),      # Reserved field
    ]

    def __str__(self):
        return (f"ABF_Packet_Header:\n"
                f"  Sync:          \t0x{self.pkt_sync[0]:02X} 0x{self.pkt_sync[1]:02X}\n"
                f"  Packet Length: \t{self.packet_length}\n"
                f"  Function:      \t0x{self.function:02X}\n"
                f"  Count:         \t{self.count}\n"
                f"  Reserved:      \t0x{self.reserved:04X}")

class ABF_Packet:
    """
    Represents a complete ABF packet.
    """
    def __init__(self, header: ABF_Packet_Header, data: bytes = None, crc: int = None):
        """
        Initializes an ABF packet.

        Args:
            header: The ABF packet header.
            data: The payload data (excluding CRC).
            crc: The CRC32 checksum.  If None, it will be calculated.
        """
        self.header = header
        self.data = data if data is not None else b""
        self.crc32 = crc if crc is not None else self.calculate_crc()

    def calculate_crc(self):
        """
        Calculates the CRC32 checksum of the header and data.
        """
        header_bytes = bytes(self.header)
        # CRC is calculated over header + data
        crc_data = header_bytes + self.data
        return zlib.crc32(crc_data) & 0xFFFFFFFF

    def to_bytes(self):
        """
        Serializes the ABF packet to bytes.

        Returns:
            bytes: The serialized packet.
        """
        header_bytes = bytes(self.header)
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

        Args:
            buffer: The received byte stream.

        Returns:
            ABF_Packet: The deserialized ABF packet.

        Raises:
            ValueError: If the buffer is too short or the CRC is invalid.
        """
        if len(buffer) < ctypes.sizeof(ABF_Packet_Header) + 4:  # Header + CRC
            raise ValueError("Invalid packet: Data is too short for header and CRC")

        header_bytes = buffer[:ctypes.sizeof(ABF_Packet_Header)]
        header = ABF_Packet_Header.from_buffer_copy(header_bytes)
        packet_length = header.packet_length
        header_plus_crc_len = ctypes.sizeof(ABF_Packet_Header) + 4

        if packet_length < header_plus_crc_len:
            print( {packet_length}, {header_plus_crc_len})
            raise ValueError("Invalid packet: packet_length is too small")
        
        # Extract data.  The packet_length includes 4 bytes in header and 4 bytes CRC, so subtract.
        packet_length_without_crc = packet_length - 4 - 4
        data_start = ctypes.sizeof(ABF_Packet_Header)
        data_end = data_start + packet_length_without_crc
        
        if data_end > len(buffer):
            print( data_start, packet_length_without_crc, data_end, len(buffer) )
            raise ValueError("Invalid packet: packet_length exceeds buffer length")
        
        data = buffer[data_start:data_end]


        # Extract CRC
        crc_bytes = buffer[data_end:]
        received_crc = int.from_bytes(crc_bytes, byteorder='little')  # CRC is now read as little-endian
        print(f"Received CRC: 0x{received_crc:08X}") # print received crc


        # Calculate CRC
        calculated_crc = zlib.crc32(header_bytes + data) & 0xFFFFFFFF

        if received_crc != calculated_crc:
            raise ValueError(f"Invalid CRC: Expected 0x{received_crc:08X}, Calculated 0x{calculated_crc:08X}")

        return ABF_Packet(header, data, received_crc)

    @staticmethod
    def from_file(file_path: str):
        """
        Reads an ABF packet from a text file.

        Args:
            file_path: Path to the text file.

        Returns:
            ABF_Packet: The ABF packet read from the file.
        """
        with open(file_path, "r") as f:
            lines = f.readlines()

        file_dict = {}
        data = None
        crc = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split(":", 1)
            key = key.lower().replace(" ", "_")
            value = value.strip()
            file_dict[key] = value

        # Handle data (hex)
        print(f"data_(hex): {file_dict.get('data_(hex)')}") # Print the value here
        if "data_(hex)" in file_dict and file_dict["data_(hex)"] == "": # added condition
            print(f"data_(hex): {file_dict.get('data_(hex)')}") # Print the value here
            data = bytes.fromhex(file_dict["data_(hex)"])
        else:
            data = b""  #  set default value

        # Construct header
        header = ABF_Packet_Header()
        try:
            sync_bytes = bytes.fromhex(file_dict["sync"].replace("0x", "").replace(",", ""))
            header.pkt_sync = (sync_bytes[0], sync_bytes[1]) # Assign as tuple of ints
            if file_dict["packet_length"] == "?":
                header.packet_length =  ctypes.sizeof(ABF_Packet_Header) - 4 + len(data) + 4 # Calculate packet_length here
            else:
                header.packet_length = int(file_dict["packet_length"])
            header.function = int(file_dict["function"].replace("0x", ""), 16)
            header.count = int(file_dict["count"])
            header.reserved = int(file_dict["reserved"].replace("0x", ""), 16)
            
        except KeyError as e:
             raise ValueError(f"Missing key in input file: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid value in input file: {e}")

        packet = ABF_Packet(header, data)

        #append CRC        
        if crc is None:
            packet.crc32 = packet.calculate_crc()
        else:
            packet.crc32 = crc
        
        return packet
    
import zlib

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


def get_packet(ser) -> Dict[str, any]:
    rec_packet = bytearray()
    current_state = STATE_IDLE
    received_bytes = 0
    packet_length = 0
    print("\nReceive Packet...")
    while True:
        byte = ser.read(1)
        if not byte:
            break

        rec_packet.extend(byte)
        received_bytes += 1
        print(byte.hex().upper() + " ", end="")

        if current_state == STATE_IDLE:
            current_state = STATE_SYNC

        elif current_state == STATE_SYNC:
            if received_bytes == 2:
                if rec_packet[0] == 0x55 and rec_packet[1] == 0xAA:
                    current_state = STATE_LENGTH
                else:
                    print("\nSync Error. Discarding first byte and looking for sync...")
                    rec_packet = rec_packet[1:]  # Discard the first byte
                    received_bytes = 1
            elif received_bytes > 2:
                print("\nSync Error. Discarding packet and looking for sync...")
                rec_packet = bytearray(byte) # Start over with the current byte
                received_bytes = 1

        elif current_state == STATE_LENGTH:
            if received_bytes == 4:
                packet_length = rec_packet[-2] + (rec_packet[-1] << 8)
                if packet_length < 8: # Minimum length should include Function, Count, Reserved, CRC
                    print(f"\nLength Error: Packet length too short ({packet_length})")
                    current_state = STATE_LENGTH_ERR # Or reset to STATE_IDLE depending on desired behavior
                    break
                current_state = STATE_FUNCTION

        elif current_state == STATE_FUNCTION:
            if received_bytes == 5:
                print(f"\nFunction: 0x{rec_packet[4]:02X}")
                current_state = STATE_COUNT

        elif current_state == STATE_COUNT:
            if received_bytes == 6:
                print(f"Count: 0x{rec_packet[5]:02X}")
                current_state = STATE_RESERVED

        elif current_state == STATE_RESERVED:
            if received_bytes == 8:
                reserved = int.from_bytes(rec_packet[6:8], 'little')
                print(f"Reserved: 0x{reserved:04X}")
                if packet_length > 8:
                    current_state = STATE_DATA
                else:
                    current_state = STATE_CRC

        elif current_state == STATE_DATA:
            if received_bytes == 4 + packet_length - 4: # Sync + Length + Function + Count + Reserved + Data
                print(f"Data (Hex): {' '.join([f'{b:02X}' for b in rec_packet[8:-4]])}")
                current_state = STATE_CRC
            elif received_bytes > 4 + packet_length - 4:
                print("\nFrame Error: Received more bytes than expected based on packet length.")
                current_state = STATE_FRAME_ERR
                break

        elif current_state == STATE_CRC:
            if received_bytes == 4 + packet_length:
                print(f"Received {received_bytes} bytes.")
                if packet_length >= 4: # Ensure there's enough data for CRC
                    crc_calculated = zlib.crc32(rec_packet[2:-4]) & 0xFFFFFFFF  # exclusive sync word and crc
                    crc_received = int.from_bytes(rec_packet[-4:], 'little')

                    if crc_calculated == crc_received:
                        print("Packet CRC valid")
                        current_state = STATE_VALID
                    else:
                        print(f"Packet CRC: 0x{crc_received:08X}, calculated CRC: 0x{crc_calculated:08X}")
                        current_state = STATE_CRC_ERR
                else:
                    print("Error: Insufficient data for CRC check.")
                    current_state = STATE_FRAME_ERR
                break

        elif current_state in [STATE_SYNC_ERR, STATE_LENGTH_ERR, STATE_FUNCTION_ERR, STATE_COUNT_ERR, STATE_CRC_ERR, STATE_FRAME_ERR]:
            print("\nError state. Exiting packet reception.")
            break # Or potentially add logic to try and resynchronize

    return {
        "state": current_state,
        "bytes_received": received_bytes,
        "packet_length": packet_length,
        "rec_packet": rec_packet
    }

if __name__ == "__main__":
    # Create an ABF packet
    header = ABF_Packet_Header()
    header.pkt_sync = (0x55, 0xAA)
    header.packet_length = 12 # 4 (header - packet_length) + 4 (data) + 4 (CRC)
    header.function = 0x01
    header.count = 1
    header.reserved = 0x1234
    data = b"Test"
    packet = ABF_Packet(header, data)

    # Print the packet
    print(packet)

    # Serialize to bytes
    packet_bytes = packet.to_bytes()
    print(f"Serialized Packet: {' '.join(f'{b:02X}' for b in packet_bytes)}")

    # Deserialize from bytes
    try:
        received_packet = ABF_Packet.from_bytes(packet_bytes)
        print("\n Packet from bytes:")
        print(received_packet)
    except ValueError as e:
        print(f"Error: {e}")

    # Create ABF packet from file
    try:
        packet_from_file = ABF_Packet.from_file("tlm1.abf")
        print("\nPacket from file:")
        print(packet_from_file)
    except ValueError as e:
        print(f"Error: {e}")




#tlm1.abf
#ABF_Packet:
#  Sync:                0x55, 0xAA
#  Packet Length:       ?
#  Function:            0x02
#  Count:               1
#  Reserved:            0
#  Data (Hex):          ""      
#  CRC32:               ?


#
#PS C:\Users\x-luo\python> python abf_pkt.py
#ABF_Packet:
#ABF_Packet_Header:
#  Sync:                 0x55 0xAA
#  Packet Length:        12
#  Function:             0x01
#  Count:                1
#  Reserved:             0x1234
#  Data (Hex):    54 65 73 74
#  CRC32:         0x60FC6D6C
#Serialized Packet: 55 AA 0C 00 01 01 34 12 54 65 73 74 6C 6D FC 60
#Received CRC: 0x60FC6D6C
#
# Packet from bytes:
#ABF_Packet:
#ABF_Packet_Header:
#  Sync:                 0x55 0xAA
#  Packet Length:        12
#  Function:             0x01
#  Count:                1
#  Reserved:             0x1234
#  Data (Hex):    54 65 73 74
#  CRC32:         0x60FC6D6C
#data_(hex): ""
#
#Packet from file:
#ABF_Packet:
#ABF_Packet_Header:
#  Sync:                 0x55 0xAA
#  Packet Length:        8
#  Function:             0x02
#  Count:                1
#  Reserved:             0x0000
#  Data (Hex):
#  CRC32:         0xDCA78E3A
#PS C:\Users\x-luo\python>
#