
import time
import argparse
import serial  # Import serial for the standalone function
from ccsds_pkg import *


def parse_arguments():
    parser = argparse.ArgumentParser(description="CCSDS Packet Sender/Receiver")
    parser.add_argument("com_port", help="COM port to use (e.g., COM12)")
    parser.add_argument("file", help="Specify CCSDS packet file")
    return parser.parse_args()

if __name__ == "__main__":

    args = parse_arguments()
    print(args)
    print(type(args))

    packet = CCSDS_Packet.from_file(args.file)
    print(packet)

    # Serialize to bytes
    packet_bytes = packet.to_bytes()
    print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")  

    with serial.Serial(port=args.com_port, baudrate=115200, timeout=0.05) as ser: #if did not receive char in 100ms, then break out
        bytes_written = ser.write(packet_bytes)  # Send a test string
        #response = ser.read(1024)  # Read response

        print(f"Send {bytes_written} bytes")

        response = bytearray()
        while True:
            byte = ser.read(1)  # Read 1 byte at a time
            if not byte:  # Timeout occurred (no data received within 1us)
                break
            response.extend(byte)
        hex_output = " ".join(f"{byte:02X}" for byte in response)

        print(f"Received Packet ({len(response)}):")
        print(hex_output)

        ret_ccsds = CCSDS_Packet.from_bytes(response)
        ret_ccsds.header.packet_type = 1
 
        print(ret_ccsds)
        # Serialize to bytes
        packet_bytes = ret_ccsds.to_bytes()
        print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")  


r"""
PS C:\Users\x-luo\c_cpp\space\python> python3 ccsds.py COM12 y.sds
Namespace(com_port='COM12', file='y.sds')
<class 'argparse.Namespace'>
Complete packet bytes:
1F FF C0 64 00 14 00 00 00 00 00 00 01 05 12 34 48 65 6C 6C 6F 21
Complete packet bytes:
1F FF C0 64 00 14 00 00 00 00 00 00 01 05 12 34 48 65 6C 6C 6F 21
CCSDS_Packet_Header(16) bytes:
  Version Number:      0
  Packet Type:         1
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         20
  Timing Info:         0
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0xD894B66C

Serialized Packet (Hex): 1F FF C0 64 00 14 00 00 00 00 00 00 01 05 12 34 48 65 6C 6C 6F 21 D8 94 B6 6C
Send 26 bytes
Received Packet (26):
1F FF C0 64 00 14 00 00 00 00 00 00 01 05 12 34 48 65 6C 6C 6F 21 D8 94 B6 6C
16, 6
1F FF C0 64 00 14 00 00 00 00 00 00 01 05 12 34 48 65 6C 6C 6F 21
CCSDS_Packet_Header(16) bytes:
  Version Number:      0
  Packet Type:         1
  Second Header Flag:  1
  Application ID:      0x07FF
  Group Flag:          3
  Sequence Number:     100
  Data Length:         20
  Timing Info:         0
  Segment Number:      1
  Function Code:       05
  Address Code:        0x1234
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0xD894B66C

Serialized Packet (Hex): 1F FF C0 64 00 14 00 00 00 00 00 00 01 05 12 34 48 65 6C 6C 6F 21 D8 94 B6 6C
"""