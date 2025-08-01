import ctypes
import zlib
import struct
import sys
import os
from typing import Dict, ByteString
import time
import yaml

class ABF_Packet_Header(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("pkt_sync", ctypes.c_uint8 * 2),
        ("packet_length", ctypes.c_uint16),
        ("function", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8),
    ]

    def __str__(self):
        return (f"ABF_Packet_Header:\n"
                f"  Sync:            0x{self.pkt_sync[0]:02X} 0x{self.pkt_sync[1]:02X}\n"
                f"  Packet Length: {self.packet_length}\n"
                f"  Function:        0x{self.function:02X}\n"
                f"  Reserved:        0x{self.reserved:02X}")

class ABF_Packet:
    SYNC_WORD = 0xAA55
    STATE_IDLE = 0
    STATE_SYNC = 1
    STATE_LENGTH = 2
    STATE_FUNCTION = 3
    STATE_RESERVED = 5
    STATE_DATA = 6
    STATE_CRC = 7
    STATE_VALID = 8
    STATE_SYNC_ERR = 0x81
    STATE_LENGTH_ERR = 0x82
    STATE_FRAME_ERR = 0x86
    STATE_CRC_ERR = 0x85

    MAX_DATA_SIZE = 256
    MAX_TOTAL_SIZE = ctypes.sizeof(ABF_Packet_Header) + MAX_DATA_SIZE + 4

    def __init__(self, function: int, reserved: int, data: bytes = b''):
        self.header = ABF_Packet_Header()
        self.header.pkt_sync[0] = 0x55
        self.header.pkt_sync[1] = 0xAA
        self.header.function = function
        self.header.reserved = reserved
        self.data = data if data is not None else b""
        self.header.packet_length = 1 + 1 + len(self.data) + 4
        self.crc32 = self.calculate_crc()

    def calculate_crc(self):
        header_bytes_part = bytes(self.header)[2:]
        crc_data = header_bytes_part + self.data
        return zlib.crc32(crc_data) & 0xFFFFFFFF

    def to_bytes(self):
        header_bytes = bytes(self.header)
        crc_bytes = self.crc32.to_bytes(4, byteorder='little')
        return header_bytes + self.data + crc_bytes

    def __str__(self):
        return (f"ABF_Packet:\n"
                f"{str(self.header)}\n"
                f"  Data (Hex):    {' '.join(f'{b:02X}' for b in self.data)}\n"
                f"  CRC32:         0x{self.crc32:08X}")

    @staticmethod
    def from_bytes(buffer: bytes):
        HEADER_SIZE_BYTES = ctypes.sizeof(ABF_Packet_Header)
        CRC_SIZE_BYTES = 4
        MIN_PACKET_SIZE = HEADER_SIZE_BYTES + CRC_SIZE_BYTES
        if len(buffer) < MIN_PACKET_SIZE:
            raise ValueError(f"Invalid packet: Too short. Expected at least {MIN_PACKET_SIZE} bytes, got {len(buffer)}")
        header_bytes = buffer[:HEADER_SIZE_BYTES]
        header = ABF_Packet_Header.from_buffer_copy(header_bytes)
        packet_length_from_header = header.packet_length
        if packet_length_from_header > ABF_Packet.MAX_TOTAL_SIZE:
            raise ValueError(f"Invalid packet: Header packet_length ({packet_length_from_header}) is too large.")
        if packet_length_from_header < (1 + 1 + CRC_SIZE_BYTES):
            raise ValueError(f"Invalid packet: packet_length ({packet_length_from_header}) is too small.")
        total_expected_buffer_len = 2 + 2 + packet_length_from_header
        if len(buffer) < total_expected_buffer_len:
            raise ValueError(f"Invalid packet: Buffer length ({len(buffer)}) is less than total expected ({total_expected_buffer_len}) based on header's packet_length.")
        data_payload_len = packet_length_from_header - (1 + 1 + CRC_SIZE_BYTES)
        data_start_idx = HEADER_SIZE_BYTES
        data_end_idx = data_start_idx + data_payload_len
        data = buffer[data_start_idx:data_end_idx]
        crc_bytes = buffer[data_end_idx:data_end_idx + CRC_SIZE_BYTES]
        received_crc = int.from_bytes(crc_bytes, byteorder='little')
        calculated_crc_data_segment = buffer[2:data_end_idx]
        calculated_crc = zlib.crc32(calculated_crc_data_segment) & 0xFFFFFFFF
        if received_crc != calculated_crc:
            raise ValueError(f"Invalid CRC: Expected 0x{received_crc:08X}, Calculated 0x{calculated_crc:08X}")
        return ABF_Packet(header.function, header.reserved, data)

    @staticmethod
    def from_file(file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
            file_dict = {}
            data_hex_parts = []
            in_data_section = False
            for line in lines:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("#"):
                    continue
                if stripped_line.lower().startswith("data (hex):"):
                    in_data_section = True
                    line_without_comment = stripped_line.split("#")[0].strip()
                    data_part = line_without_comment[len("data (hex):"):].strip().strip('"')
                    data_hex_parts.append(data_part)
                    if not stripped_line.endswith('"'):
                        in_data_section = False
                    continue
                if in_data_section:
                    line_without_comment = stripped_line.split("#")[0].strip()
                    data_part = line_without_comment.strip().strip('"')
                    data_hex_parts.append(data_part)
                    if stripped_line.endswith('"'):
                        in_data_section = False
                    continue
                if ":" in stripped_line:
                    line_without_comment = stripped_line.split("#")[0].strip()
                    key, value = line_without_comment.split(":", 1)
                    key = key.lower().replace(" ", "_")
                    file_dict[key] = value.strip()
            data = b""
            full_data_string = "".join(data_hex_parts).replace("0x", "").replace(",", "").replace(" ", "").strip()
            if full_data_string:
                if len(full_data_string) % 2 != 0:
                    full_data_string = '0' + full_data_string
                data = bytes.fromhex(full_data_string)
            function_code = int(file_dict.get("function", "0").replace("0x", ""), 16)
            reserved_value = int(file_dict.get("reserved", "0").replace("0x", ""), 16)
            packet = ABF_Packet(function_code, reserved_value, data)
            if file_dict.get("packet_length") != "?":
                try:
                    packet.header.packet_length = int(file_dict["packet_length"])
                except ValueError as e:
                    raise ValueError(f"Invalid packet_length in input file: {e}")
            else:
                packet.header.packet_length = 1 + 1 + len(data) + 4
            crc_str = file_dict.get("crc32", "?")
            if crc_str != "?":
                try:
                    crc = int(crc_str.replace("0x",""), 16)
                    if packet.calculate_crc() != crc:
                        raise ValueError(f"Invalid CRC in file: Calculated 0x{packet.calculate_crc():08X}, Expected 0x{crc:08X}.")
                    packet.crc32 = crc
                except ValueError as e:
                    raise ValueError(f"Invalid CRC value in input file: {e}")
            return packet
        except Exception as e:
            print(f"Text parsing failed with error: {e}. Attempting binary parsing...")
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            return ABF_Packet.from_bytes(file_bytes)

    @staticmethod
    def from_yaml_file(file_path: str):
        """
        Parses a standard YAML file into an ABF_Packet object.
        Fills in '~' (null) values for packet_length and crc32.
        """
        print(f"DEBUG: Now parsing YAML file: {file_path}") # <--- ADD THIS LINE
        with open(file_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        if yaml_data is None:
            raise ValueError(f"YAML file '{file_path}' is empty or invalid.")

        packet_data = yaml_data.get("abf_packet", {})
        
        print(f"DEBUG: packet_data type: {type(packet_data)}")
        print(f"DEBUG: packet_data value: {packet_data}")

        # Convert YAML list of hex integers into a single bytes object
        data_bytes = b''
        yaml_data_list = packet_data.get("data", [])
        for val in yaml_data_list:
            if val > 0xFFFF: # Assume 4 bytes for values > 65535
                data_bytes += val.to_bytes(4, byteorder='little')
            else: # Assume 2 bytes for smaller values
                data_bytes += val.to_bytes(2, byteorder='little')

        # Create the packet
        function_code = packet_data.get("function", 0)
        reserved_value = packet_data.get("reserved", 0)
        packet = ABF_Packet(function_code, reserved_value, data_bytes)
        
        # Fill in 'packet_length' and 'crc32' if they are null
        if packet_data.get("packet_length") is not None:
            packet.header.packet_length = packet_data["packet_length"]
        if packet_data.get("crc32") is not None:
            packet.crc32 = packet_data["crc32"]
        
        return packet

    @staticmethod
    def get_packet(ser) -> Dict[str, any]:
        rec_packet = bytearray()
        current_state = ABF_Packet.STATE_IDLE
        received_bytes = 0
        packet_length_from_header = 0
        total_packet_size_expected = 0
        print("\nReceive Packet...")
        HEADER_SIZE_BYTES = ctypes.sizeof(ABF_Packet_Header)
        CRC_SIZE_BYTES = 4
        MIN_PACKET_LENGTH_VALUE = 1 + 1 + CRC_SIZE_BYTES
        timeout_start = time.time()
        while time.time() - timeout_start < 5:
            byte = ser.read(1)
            if not byte:
                continue
            if len(rec_packet) == 0 and byte[0] == 0x55:
                rec_packet.extend(byte)
                print(byte.hex().upper() + " ", end="")
            elif len(rec_packet) == 1 and byte[0] == 0xAA:
                rec_packet.extend(byte)
                print(byte.hex().upper() + " ", end="")
                break
            else:
                rec_packet = bytearray()
        else:
            print("Timeout waiting for sync bytes.")
            return {"state": ABF_Packet.STATE_SYNC_ERR, "bytes_received": 0, "packet_length": 0, "rec_packet": bytearray()}
        header_remaining_bytes = HEADER_SIZE_BYTES - len(rec_packet)
        rest_of_header = ser.read(header_remaining_bytes)
        rec_packet.extend(rest_of_header)
        if len(rec_packet) < HEADER_SIZE_BYTES:
            print("Timeout reading header.")
            return {"state": ABF_Packet.STATE_FRAME_ERR, "bytes_received": len(rec_packet), "packet_length": 0, "rec_packet": rec_packet}
        header = ABF_Packet_Header.from_buffer_copy(rec_packet)
        packet_length_from_header = header.packet_length
        total_packet_size_expected = 2 + 2 + packet_length_from_header
        if total_packet_size_expected > ABF_Packet.MAX_TOTAL_SIZE:
            print(f"Length Error: Packet length ({packet_length_from_header}) too large.")
            return {"state": ABF_Packet.STATE_LENGTH_ERR, "bytes_received": len(rec_packet), "packet_length": packet_length_from_header, "rec_packet": rec_packet}
        remaining_bytes_to_read = total_packet_size_expected - len(rec_packet)
        if remaining_bytes_to_read > 0:
            packet_payload = ser.read(remaining_bytes_to_read)
            rec_packet.extend(packet_payload)
        if len(rec_packet) != total_packet_size_expected:
            print("Frame Error: Incomplete packet received.")
            return {"state": ABF_Packet.STATE_FRAME_ERR, "bytes_received": len(rec_packet), "packet_length": packet_length_from_header, "rec_packet": rec_packet}
        try:
            ABF_Packet.from_bytes(rec_packet)
            print("Packet CRC valid")
            return {"state": ABF_Packet.STATE_VALID, "bytes_received": len(rec_packet), "packet_length": packet_length_from_header, "rec_packet": rec_packet}
        except ValueError as e:
            print(f"Packet CRC error: {e}")
            return {"state": ABF_Packet.STATE_CRC_ERR, "bytes_received": len(rec_packet), "packet_length": packet_length_from_header, "rec_packet": rec_packet}