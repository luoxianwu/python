import struct

RED = "\033[91m"
RESET = "\033[0m"

def format_with_threshold(value, low, high, format_str, is_temperature=False, is_vcc=False, is_28V=False, is_5v=False, is_5v_current=False, is_neg5v=False, is_neg5v_current=False, is_28v_current=False):
    if is_temperature:
        converted_value = value / 128.0
    elif is_vcc:
        converted_value = value / 4095 * 3.3 * 2
    elif is_28V or is_28v_current:
        converted_value = value / 4095 * 28.0
    elif is_5v or is_5v_current:
        converted_value = value / 4095 * 5.0
    elif is_neg5v or is_neg5v_current:
        converted_value = (value / 4095 * 5.0)  # Negative voltage conversion
    else:
        converted_value = value / 4095 * 3.3
    formatted = format_str.format(converted_value)
    if converted_value < low or converted_value > high:
        return f"{RED}{formatted}{RESET}"
    return formatted

annotations = [
    lambda v: format_with_threshold(v, 1.000, 3.000, "28V voltage:\t {:.3f}V", is_28V=True),
    lambda v: format_with_threshold(v, 0.5, 1.5, "28V current:\t {:.3f}A", is_28v_current=True),  # Use is_28v_current flag
    lambda v: format_with_threshold(v, 4.75, 5.25, "5V voltage:\t {:.3f}V", is_5v=True),
    lambda v: format_with_threshold(v, 0.5, 1.5, "5V current:\t {:.3f}A", is_5v_current=True),
    lambda v: format_with_threshold(v, -5.25, -4.75, "-5V voltage:\t -{:.3f}V", is_neg5v=True),
    lambda v: format_with_threshold(v, 0.5, 1.5, "-5V current:\t {:.3f}A", is_neg5v_current=True),
    lambda v: format_with_threshold(v, 0, 20, "board temperature:\t {:.2f}°C", is_temperature=True),
    lambda v: format_with_threshold(v, 3.00, 3.80, "board VCC:\t {:.3f}V", is_vcc=True)
]

def get_annotation(index, value):
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