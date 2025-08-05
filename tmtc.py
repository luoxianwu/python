import time
import argparse
import serial
import struct
import sys
import os
import importlib
import binascii
from yaml_to_abf import from_yaml_file

# Note: This line assumes your packet parsing file is named abf_pkt2.py
# If you rename it to abf_pkt.py, you should change this line as well.
from abf_pkt2 import ABF_Packet
import yaml # Import the yaml library for parsing YAML files

def parse_arguments():
    parser = argparse.ArgumentParser(description="ABF Packet Sender/Receiver")
    parser.add_argument("com_port", help="COM port to use (e.g., COM12)")
    parser.add_argument("file", help="Specify an ABF packet file (e.g., .\\swan\\tm.abf or .\\swan\\pwm.yml)")
    return parser.parse_args()

def get_parser_module_name_from_file_path(file_path):
    """
    Derives the parser module name (e.g., 'swan.tm_parse') from a given
    data file path (e.g., '.\swan\tm.abf').
    """
    normalized_path = os.path.normpath(file_path)
    module_dir = os.path.dirname(normalized_path)
    parser_module_base_name = "tm_parse"
    path_components = [part for part in module_dir.split(os.sep) if part and part != '.']
    
    if path_components:
        return ".".join(path_components) + "." + parser_module_base_name
    else:
        return parser_module_base_name

if __name__ == "__main__":
    args = parse_arguments()
    print(args)
    print(type(args))

    parser_module_name = get_parser_module_name_from_file_path(args.file)
    print(f"Attempting to import parser module: {parser_module_name}")

    try:
        # Dynamically import the module containing the Telemetry class
        dynamic_parser_module = importlib.import_module(parser_module_name)
        
        # Get only the Telemetry class from the dynamically loaded module
        Telemetry = getattr(dynamic_parser_module, "Telemetry")

        print(f"Successfully loaded ABF_Packet from abf_pkt.py")
        print(f"Successfully loaded Telemetry from {parser_module_name}")

    except ImportError as e:
        print(f"Error: Could not import the module '{parser_module_name}'.")
        print(f"Please ensure 'tm_parse.py' exists in '{os.path.dirname(os.path.normpath(args.file))}'")
        print(f"and that all parent directories contain an empty '__init__.py' file.")
        print(f"Details: {e}")
        sys.exit(1)
    except AttributeError as e:
        print(f"Error: The module '{parser_module_name}' is missing the 'Telemetry' class.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during module loading: {e}")
        sys.exit(1)

    try:
        # --- NEW LOGIC: Check file extension to choose parser ---
        print(f"Parsing '{args.file}'...")
        file_extension = os.path.splitext(args.file)[1].lower()
        if file_extension in ['.yml', '.yaml']:
            packet = from_yaml_file(args.file)
        else:
            packet = ABF_Packet.from_file(args.file)
        
        print(packet)

        packet_bytes = packet.to_bytes()
        print(f"Serialized Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes)}")

        with serial.Serial(port=args.com_port, baudrate=115200, timeout=1.5) as ser:
            bytes_written = ser.write(packet_bytes)
            print(f"Send {bytes_written} bytes")

            rec_packet_info = ABF_Packet.get_packet(ser)

            if rec_packet_info["state"] == ABF_Packet.STATE_VALID:
                print("Packet received successfully!")
                print(f"Packet data: {rec_packet_info['rec_packet'].hex()}")
                
                ret_abf = ABF_Packet.from_bytes(rec_packet_info['rec_packet']) 
                print(ret_abf)
                packet_bytes_response = ret_abf.to_bytes()
                print(f"Serialized Response Packet (Hex): {' '.join(f'{b:02X}' for b in packet_bytes_response)}") 
                
                if len(ret_abf.data) != 0: 
                    telemetry = Telemetry()
                    result = telemetry.parse(ret_abf.data)
                    print("\n--- Telemetry Data ---")
            else:
                print("Error receiving packet.")
                print(f"Final state: {rec_packet_info['state']}")
                print(f"Bytes received: {rec_packet_info['bytes_received']}")
                print(f"Packet length: {rec_packet_info['packet_length']}")
                print(f"Packet data: {rec_packet_info['rec_packet'].hex()}")
                if rec_packet_info['bytes_received'] == 0:
                    print("No response")
            
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        print(f"Please ensure '{args.com_port}' is available and not in use by another application.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during packet processing: {e}")
        sys.exit(1)