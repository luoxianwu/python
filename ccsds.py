
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


