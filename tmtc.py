
import time
import argparse
import serial  # Import serial for the standalone function
from abf_pkt import *
from tm2 import *
import struct


def parse_arguments():
    parser = argparse.ArgumentParser(description="ABF Packet Sender/Receiver")
    parser.add_argument("com_port", help="COM port to use (e.g., COM12)")
    parser.add_argument("file", help="Specify a ABF packet file")
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_arguments()
    print(args)
    print(type(args))

    packet = ABF_Packet.from_file(args.file)
    print(packet)

    # Serialize to bytes
    packet_bytes = packet.to_bytes()
    print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")  

    # PC is not real time, need adjust timeout value in practice
    with serial.Serial(port=args.com_port, baudrate=115200, timeout=1.5) as ser: #if did not receive char in 100ms, then break out
        bytes_written = ser.write(packet_bytes)  # Send a test string
        #response = ser.read(1024)  # Read response

        print(f"Send {bytes_written} bytes")

        #expect response
        rec_packet_info = ABF_Packet.get_packet( ser )

        # Process the results
        if rec_packet_info["state"] == ABF_Packet.STATE_VALID:
            print("Packet received successfully!")
            print(f"Packet data: {rec_packet_info['rec_packet'].hex()}")
            # You would then decode packet_bytes according to the ABF specification
        else:
            print("Error receiving packet.")
            print(f"Final state: {rec_packet_info['state']}")
            print(f"Bytes received: {rec_packet_info['bytes_received']}")
            print(f"Packet length: {rec_packet_info['packet_length']}")
            print(f"Packet data: {rec_packet_info['rec_packet'].hex()}")

        if rec_packet_info["state"] == ABF_Packet.STATE_VALID:
          
            ret_abf = ABF_Packet.from_bytes(rec_packet_info['rec_packet']) 
            
            print(ret_abf)
            # Serialize to bytes
            packet_bytes = ret_abf.to_bytes()
            print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}") 
            ''' for import tm.py
            Telemetry.parse(ret_abf)'
            '''
            if len(ret_abf.data) != 0: 
              #for import tm2.py
              telemetry = Telemetry()
              result = telemetry.parse(ret_abf.data)
        else:
            if rec_packet_info['bytes_received'] == 0:
                print("No response")
            


r"""
PS C:\Users\x-luo\python> python tmtc.py COM18 tlm1.abf
Namespace(com_port='COM18', file='tlm1.abf')
<class 'argparse.Namespace'>
data_(hex): ""
ABF_Packet:
ABF_Packet_Header:
  Sync:                 0x55 0xAA
  Packet Length:        8
  Function:             0x02
  Count:                1
  Reserved:             0x0000
  Data (Hex):
  CRC32:         0xF65A8172
Serialized Packet (Hex): 55 AA 08 00 02 01 00 00 72 81 5A F6
Send 12 bytes

Receive Packet...
55 AA 24 00 02
Function: 0x02
01 Count: 0x01
00 00 Reserved: 0x0000
00 00 78 56 34 12 33 44 32 00 AA BB 9D 05 0B 04 BB 03 AE 03 96 03 E0 03 38 0A 03 08 Data (Hex): 00 00 78 56 34 12 33 44 32 00 AA BB 9D 05 0B 04 BB 03 AE 03 96 03 E0 03
94 30 55 06 Received 40 bytes.
Packet CRC valid
Packet received successfully!
Packet data: 55aa24000201000000007856341233443200aabb9d050b04bb03ae039603e003380a030894305506
Received CRC: 0x06553094
ABF_Packet:
ABF_Packet_Header:
  Sync:                 0x55 0xAA
  Packet Length:        36
  Function:             0x02
  Count:                1
  Reserved:             0x0000
  Data (Hex):    00 00 78 56 34 12 33 44 32 00 AA BB 9D 05 0B 04 BB 03 AE 03 96 03 E0 03 38 0A 03 08
  CRC32:         0x06553094
Serialized Packet (Hex): 55 AA 24 00 02 01 00 00 00 00 78 56 34 12 33 44 32 00 AA BB 9D 05 0B 04 BB 03 AE 03 96 03 E0 03 38 0A 03 08 94 30 55 06
HEALTH data length: 12 bytes
TLM_1 data length: 28 bytes
Input data length: 28 bytes
Expected TLM_1 size: 28 bytes
Software Version Major: 0
Software Version Minor: 0
Up Time: 305419896 s
Reset Count: 51
Board Temperature: 68 °C
Cumulative Error Count: 50
Latest Error Code: 0xAA
Telemetry Command Count: 187
Channel_0: 0x059D          28V voltage: 9.826V
Channel_1: 0x040B          28V current: 7.077A
Channel_2: 0x03BB          5V voltage: 1.166V
Channel_3: 0x03AE          5V current: 1.150A
Channel_4: 0x0396          -5V voltage: -1.121V
Channel_5: 0x03E0          -5V current: -1.211A
Channel_6: 0x0A38          board temperature: 20.44°C
Channel_7: 0x0803          board VCC: 3.306V
PS C:\Users\x-luo\python>

"""