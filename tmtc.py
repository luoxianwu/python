
import time
import argparse
import serial  # Import serial for the standalone function
from ccsds_pkg import *
from tm import *
import struct


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

    # PC is not real time, need adjust timeout value in practice
    with serial.Serial(port=args.com_port, baudrate=115200, timeout=2) as ser: #if did not receive char in 100ms, then break out
        bytes_written = ser.write(packet_bytes)  # Send a test string
        #response = ser.read(1024)  # Read response

        print(f"Send {bytes_written} bytes")

        #expect response
        validation, response = CCSDS_Packet.get_packet( ser )

      
        hex_output = " ".join(f"{byte:02X}" for byte in response)

        print(f"Received Packet ({len(response)}):")
        print(hex_output)

        ret_ccsds = CCSDS_Packet.from_bytes(response[2:]) # discard sync word
         
        print(ret_ccsds)
        # Serialize to bytes
        packet_bytes = ret_ccsds.to_bytes()
        print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}") 

        Telemetery.parse(ret_ccsds)


r"""
PS C:\Users\x-luo\python> python tmtc.py COM20 .\tm-adc.sds
Namespace(com_port='COM20', file='.\\tm-adc.sds')
<class 'argparse.Namespace'>
09 23 C0 64 00 13 00 00 00 00 00 00 01 10 00 01 48 65 6C 6C 6F 21
BB2FAE08
09 23 C0 64 00 13 00 00 00 00 00 00 01 10 00 01 48 65 6C 6C 6F 21
BB2FAE08
SYNC:           0x55AA
CCSDS_Packet_Header(16) bytes:
  Version Number:      0
  Packet Type:         0
  Second Header Flag:  1
  Application ID:      0x0123
  Group Flag:          3
  Sequence Number:     100
  Data Length:         19
  Timing Info:         0
  Segment Number:      1
  Function Code:       10
  Address Code:        0x0001
Data (Hex):     48 65 6C 6C 6F 21
CRC32:          0xBB2FAE08

Serialized Packet (Hex): 55 AA 09 23 C0 64 00 13 00 00 00 00 00 00 01 10 00 01 48 65 6C 6C 6F 21 BB 2F AE 08
Send 28 bytes
Received Packet (38):
55 AA 09 23 C0 01 00 1D 00 00 00 00 00 00 00 00 00 00 05 60 03 F0 03 EE 03 7F 04 0F 03 E3 0A 16 07 F8 4E A5 E4 73
16, 16
09 23 C0 01 00 1D 00 00 00 00 00 00 00 00 00 00 05 60 03 F0 03 EE 03 7F 04 0F 03 E3 0A 16 07 F8
Valid CRC : 0x4EA5E473
SYNC:           0x55AA
CCSDS_Packet_Header(16) bytes:
  Version Number:      0
  Packet Type:         0
  Second Header Flag:  1
  Application ID:      0x0123
  Group Flag:          3
  Sequence Number:     1
  Data Length:         29
  Timing Info:         0
  Segment Number:      0
  Function Code:       00
  Address Code:        0x0000
Data (Hex):     05 60 03 F0 03 EE 03 7F 04 0F 03 E3 0A 16 07 F8
CRC32:          0x4EA5E473

Serialized Packet (Hex): 55 AA 09 23 C0 01 00 1D 00 00 00 00 00 00 00 00 00 00 05 60 03 F0 03 EE 03 7F 04 0F 03 E3 0A 16 07 F8 4E A5 E4 73
Channel_0: 0x0560          28V voltage: 1.109V
Channel_1: 0x03F0          28V current: 0.812A
Channel_2: 0x03EE          5V voltage: 0.811V
Channel_3: 0x037F          5V current: 0.721A
Channel_4: 0x040F          -5V voltage: -0.837V
Channel_5: 0x03E3          -5V current: 0.802A
Channel_6: 0x0A16          board temperature: 2582.0°C
Channel_7: 0x07F8          board VCC: 3.288V
"""