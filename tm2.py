import struct

# ANSI color codes for terminal output
RED = "\033[91m"
RESET = "\033[0m"

# Conversion constants
ADC_MAX = 4095  # 12-bit ADC
VREF = 3.3      # Reference voltage
TEMP_SCALE = 128.0  # Temperature scaling factor

def format_with_threshold(value, low, high, format_str, is_temperature=False, is_vcc=False, 
                         is_28V=False, is_5v=False, is_5v_current=False, is_neg5v=False, 
                         is_neg5v_current=False, is_28v_current=False):
    """Convert raw ADC value to physical units and format with color if out of range."""
    if is_temperature:
        converted_value = value / TEMP_SCALE
    elif is_vcc:
        converted_value = value / ADC_MAX * VREF * 2
    elif is_28V or is_28v_current:
        converted_value = value / ADC_MAX * 28.0
    elif is_5v or is_5v_current:
        converted_value = value / ADC_MAX * 5.0
    elif is_neg5v or is_neg5v_current:
        converted_value = -(value / ADC_MAX * 5.0)
    else:
        converted_value = value / ADC_MAX * VREF
    
    formatted = format_str.format(converted_value)
    if converted_value < low or converted_value > high:
        return f"{RED}{formatted}{RESET}"
    return formatted

class Telemetry:
    # Header structure: (name, size in bytes, format string for struct.unpack, print format)
    # Combining sw_major and sw_minor into one logical field for display
    HEADER_FIELDS = [
        ("sw_version", 2, "BB", "SW Version: {}.{}"),  # 2 bytes, parsed as two unsigned bytes
        ("counter", 2, "<H", "Counter: 0x{:04X} ({})"),
        ("ccsds_error", 1, "B", "CCSDS Error: 0x{:02X}"),
        ("ccsds_sequence", 1, "B", "CCSDS Sequence: {}"),
    ]

    # Channel definitions: (name, low, high, format_str, conversion_flags)
    ADC_CHANNELS = {
        0: ("28V voltage", 25.0, 30.0, "{:.3f}V", {"is_28V": True}),
        1: ("28V current", 0.5, 1.5, "{:.3f}A", {"is_28v_current": True}),
        2: ("5V voltage", 4.75, 5.25, "{:.3f}V", {"is_5v": True}),
        3: ("5V current", 0.5, 1.5, "{:.3f}A", {"is_5v_current": True}),
        4: ("-5V voltage", -5.25, -4.75, "{:.3f}V", {"is_neg5v": True}),
        5: ("-5V current", 0.5, 1.5, "{:.3f}A", {"is_neg5v_current": True}),
        6: ("board temperature", 15.0, 30.0, "{:.2f}°C", {"is_temperature": True}),
        7: ("board VCC", 3.00, 3.80, "{:.3f}V", {"is_vcc": True}),
        8: ("28V voltage", 25.0, 30.0, "{:.3f}V", {"is_28V": True}),
    }

    def __init__(self):
        # Calculate total header size dynamically
        self.header_size = sum(field[1] for field in self.HEADER_FIELDS)

    def parse(self, ccsds_pkt, print_output=True):
        """Parse a CCSDS packet and return telemetry data."""
        if not hasattr(ccsds_pkt, 'data'):
            raise ValueError("Invalid CCSDS packet: missing 'data' attribute")
        user_data = ccsds_pkt.data
        if len(user_data) < self.header_size:
            raise ValueError("Data too short to parse header")

        # Parse header dynamically
        result = {}
        offset = 0
        for name, size, fmt, _ in self.HEADER_FIELDS:
            if name == "sw_version":
                # Special case: unpack two bytes for version
                major, minor = struct.unpack(fmt, user_data[offset:offset + size])
                result["sw_major"] = major
                result["sw_minor"] = minor
                result["sw_version"] = (major, minor)  # Store as tuple for printing
            else:
                value = struct.unpack(fmt, user_data[offset:offset + size])[0]
                result[name] = value
            offset += size

        # Parse ADC data
        adc_data = user_data[offset:]
        chunk_size = 2
        adc_count = len(adc_data) // chunk_size
        result["adc"] = []

        if adc_count > 0:
            try:
                adc_values = struct.unpack(f'<{adc_count}H', adc_data)
                for i, value in enumerate(adc_values):
                    if i in self.ADC_CHANNELS:
                        name, low, high, fmt, kwargs = self.ADC_CHANNELS[i]
                        formatted_value = format_with_threshold(value, low, high, 
                                                              f"{name}:  {fmt}", **kwargs)
                    else:
                        formatted_value = f"Unknown Channel_{i}:  {value / ADC_MAX * VREF:.3f}V"
                    
                    result["adc"].append({
                        "channel": i,
                        "raw_value": value,
                        "formatted": formatted_value
                    })
            except struct.error as e:
                raise ValueError(f"Error parsing ADC values: {e}")

        # Optional printing with exact formatting
        if print_output:
            for name, _, _, print_fmt in self.HEADER_FIELDS:
                if name == "sw_version":
                    major, minor = result["sw_version"]
                    print(print_fmt.format(major, minor))
                elif name == "counter":
                    value = result[name]
                    print(print_fmt.format(value, value))
                else:
                    print(print_fmt.format(result[name]))
            for adc_entry in result["adc"]:
                print(f"Channel_{adc_entry['channel']}: 0x{adc_entry['raw_value']:04X}          {adc_entry['formatted']}")

        return result

# Test with correct raw data
if __name__ == "__main__":
    class MockPacket:
        def __init__(self, data):
            self.data = data

    # Raw data matching expected output
    raw_data = bytes.fromhex("01 00 C1 08 00 00 00 00 6A 05 F9 03 F2 03 8E 03 F3 03 D7 03 A5 0B F9 07")
    pkt = MockPacket(raw_data)
    telemetry = Telemetry()
    result = telemetry.parse(pkt)