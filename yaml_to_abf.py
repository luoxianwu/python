import yaml
import re
import binascii
from abf_pkt2 import ABF_Packet

def from_yaml_file(file_path: str) -> ABF_Packet:
    print(f"DEBUG: Now parsing YAML file: {file_path}")
    
    with open(file_path, "r") as f:
        file_content = f.read()

    yaml_data = yaml.safe_load(file_content)

    if yaml_data is None:
        raise ValueError(f"YAML file '{file_path}' is empty or invalid.")

    packet_data = yaml_data.get("abf_packet", {})
    
    print(f"DEBUG: packet_data type: {type(packet_data)}")
    print(f"DEBUG: packet_data value: {packet_data}")

    # --- CORRECTED REGULAR EXPRESSION LOGIC ---
    # 1. Capture the entire text block between 'data:' and 'crc32:'
    #    The 're.DOTALL' flag allows '.' to match newlines.
    data_block_pattern = re.compile(r'data:(.*?)\scrc32:', re.DOTALL)
    data_match = data_block_pattern.search(file_content)

    raw_data_strings = []
    if data_match:
        # 2. Extract the text content of the data block
        data_list_text = data_match.group(1)
        
        # 3. Find all hex values within that block, ignoring newlines and comments
        hex_pattern = re.compile(r'0x[0-9a-fA-F]+')
        raw_data_strings = hex_pattern.findall(data_list_text)

    # --- END OF CORRECTED REGULAR EXPRESSION LOGIC ---

    # ... (rest of the function is unchanged)
    data_bytes = b''
    for hex_str in raw_data_strings:
        val = int(hex_str, 16)
        num_bytes = (len(hex_str) - 2 + 1) // 2
        data_bytes += val.to_bytes(num_bytes, byteorder='little')
    
    print(f"DEBUG: raw_data_strings: {raw_data_strings}")
    print(f"DEBUG: The final data_bytes object is: {data_bytes.hex()}")

    function_code = packet_data.get("function", 0)
    reserved_value = packet_data.get("reserved", 0)
    packet = ABF_Packet(function_code, reserved_value, data_bytes)
    
    if packet_data.get("packet_length") is not None:
        packet.header.packet_length = packet_data["packet_length"]
    if packet_data.get("crc32") is not None:
        packet.crc32 = packet_data["crc32"]
    
    return packet