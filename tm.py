import struct

RED = "\033[91m"
RESET = "\033[0m"

def format_with_threshold(value, low, high, format_str, is_temperature=False, is_vcc=False):
    if is_temperature:
        converted_value = value / 128.0  # received data is temperature * 128
    elif is_vcc:
        converted_value = value / 4095 * 3.3 * 2  # Special conversion for board VCC
    else:
        converted_value = value / 4095 * 3.3  # Default conversion
    formatted = format_str.format(converted_value)
    if converted_value < low or converted_value > high:
        return f"{RED}{formatted}{RESET}"
    return formatted

annotations = [
    lambda v: format_with_threshold(v, 1.000, 3.000, "28V voltage:\t {:.3f}V"),
    lambda v: format_with_threshold(v, 1.000, 3.000, "28V current:\t {:.3f}A"),
    lambda v: format_with_threshold(v, 1.000, 3.000, "5V voltage:\t {:.3f}V"),
    lambda v: format_with_threshold(v, 1.000, 3.000, "5V current:\t {:.3f}A"),
    lambda v: format_with_threshold(v, 1.000, 3.000, "-5V voltage:\t -{:.3f}V"),
    lambda v: format_with_threshold(v, 1.000, 3.000, "-5V current:\t {:.3f}A"),
    lambda v: format_with_threshold(v, 0, 20, "board temperature:\t {:.2f}°C", is_temperature=True),
    lambda v: format_with_threshold(v, 3.00, 3.80, "board VCC:\t {:.3f}V", is_vcc=True)
]

def get_annotation(index, value):   
    # Ensure the annotation list loops if there are more chunks
    return annotations[index % len(annotations)](value)

class Telemetery:
    @staticmethod
    def parse( ccsds_pkt):
        user_data = ccsds_pkt.data
        #user data parse
        # ADC
        chunk_size = 2
        # Calculate the number of 16-bit integers in the data
        num_chunks = len(user_data) // chunk_size
        # Parse the data as big-endian 16-bit integers
        adc_values = struct.unpack(f'>{num_chunks}H', user_data)
        # Print each chunk with index and value in hexadecimal format
        for index, value in enumerate(adc_values):
            annotation = get_annotation(index, value)  # Get annotation for this chunk
            print(f"Channel_{index}: 0x{value:04X}          {annotation}") 