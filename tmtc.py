
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

    # Check if the file path ends with '.bin'
    if args.file.endswith(".bin"):
      # Process CCSDS binary file 
      with open(args.file, 'rb') as f:  # Open in binary read mode ('rb')
        binary_data = f.read()
      packet = CCSDS_Packet.from_bytes(binary_data)
    elif args.file.endswith(".sds"): 
      packet = CCSDS_Packet.from_file(args.file)
    else :
       print("invalid file extension!")

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

        with open("abc.bin", 'wb') as output_file: 
            output_file.write(response[2:])

        if validation:
          
            ret_ccsds = CCSDS_Packet.from_bytes(response[2:]) # discard sync word
            
            print(ret_ccsds)
            # Serialize to bytes
            packet_bytes = ret_ccsds.to_bytes()
            print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}") 

            Telemetery.parse(ret_ccsds)
        else:
            if len(response) == 0:
                print("No response")
            


r"""
PS C:\Users\x-luo\python> python tmtc.py COM18 .\tm-adc.sds
Namespace(com_port='COM18', file='.\\tm-adc.sds')
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

Receive Packet...
55 AA 09 23 C0 01 00 1D 00 00 00 00 00 00 00 00 00 00 06 01 03 E0 03 8C 03 9B 03 AB 03 AC 0A 66 08 05 34 2A 5C 8C
received 38 bytes.
packet CRC valid
16, 16
09 23 C0 01 00 1D 00 00 00 00 00 00 00 00 00 00 06 01 03 E0 03 8C 03 9B 03 AB 03 AC 0A 66 08 05
Valid CRC : 0x342A5C8C
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
Data (Hex):     06 01 03 E0 03 8C 03 9B 03 AB 03 AC 0A 66 08 05
CRC32:          0x342A5C8C

Serialized Packet (Hex): 55 AA 09 23 C0 01 00 1D 00 00 00 00 00 00 00 00 00 00 06 01 03 E0 03 8C 03 9B 03 AB 03 AC 0A 66 08 05 34 2A 5C 8C
Channel_0: 0x0601          28V voltage:  10.509V
Channel_1: 0x03E0          28V current:  6.783A
Channel_2: 0x038C          5V voltage:   1.109V
Channel_3: 0x039B          5V current:   1.127A
Channel_4: 0x03AB          -5V voltage:  -1.147V
Channel_5: 0x03AC          -5V current:  1.148A
Channel_6: 0x0A66          board temperature:    20.80°C
Channel_7: 0x0805          board VCC:    3.309V
PS C:\Users\x-luo\python>
"""