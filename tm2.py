import struct

# ANSI color codes for terminal output
RED = "\033[91m"
RESET = "\033[0m"

# Conversion constants
ADC_MAX = 4095    # 12-bit ADC
VREF = 3.3        # Reference voltage
TEMP_SCALE = 128.0  # Temperature scaling factor
ADC_TOTAL_CH = 8  # Total number of ADC channels


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
    # Define struct format for TLM_1 (HEALTH_State + ADC channels)
    STRUCT_FORMAT = "<BBIBbHBB8H"  # Little-endian, 28 bytes

    # Health field names and print formats (for output, not parsing)
    HEALTH_FIELD_INFO = [
        ("sw_ver_main", "Software Version Major: {}"),
        ("sw_ver_minor", "Software Version Minor: {}"),
        ("up_time", "Up Time: {} s"),
        ("reset_count", "Reset Count: {}"),
        ("board_temp", "Board Temperature: {} °C"),
        ("cumulative_error_count", "Cumulative Error Count: {}"),
        ("latest_error_code", "Latest Error Code: 0x{:02X}"),
        ("tele_cmd_count", "Telemetry Command Count: {}"),
    ]

    # ADC channel definitions: (name, low, high, format_str, conversion_flags)
    ADC_CHANNELS = {
        0: ("28V voltage", 25.0, 30.0, "{:.3f}V", {"is_28V": True}),
        1: ("28V current", 0.5, 1.5, "{:.3f}A", {"is_28v_current": True}),
        2: ("5V voltage", 4.75, 5.25, "{:.3f}V", {"is_5v": True}),
        3: ("5V current", 0.5, 1.5, "{:.3f}A", {"is_5v_current": True}),
        4: ("-5V voltage", -5.25, -4.75, "{:.3f}V", {"is_neg5v": True}),
        5: ("-5V current", 0.5, 1.5, "{:.3f}A", {"is_neg5v_current": True}),
        6: ("board temperature", 15.0, 30.0, "{:.2f}°C", {"is_temperature": True}),
        7: ("board VCC", 3.00, 3.80, "{:.3f}V", {"is_vcc": True}),
    }

    def __init__(self):
        # Calculate sizes
        self.health_size = 12  # HEALTH_State: BBIBbHBB = 1+1+4+1+1+2+1+1 = 12 bytes
        self.tlm_1_size = self.health_size + ADC_TOTAL_CH * 2  # 12 + 8*2 = 28 bytes
        print(f"HEALTH data length: {self.health_size} bytes")
        print(f"TLM_1 data length: {self.tlm_1_size} bytes")

    def parse(self, data, print_output=True):
        """Parse TLM_1 telemetry data using single struct format."""
        print(f"Input data length: {len(data)} bytes")
        print(f"Expected TLM_1 size: {self.tlm_1_size} bytes")

        if len(data) < self.tlm_1_size:
            raise ValueError(f"Data too short: got {len(data)} bytes, need {self.tlm_1_size} bytes")

        # Parse entire TLM_1 structure
        try:
            unpacked = struct.unpack(self.STRUCT_FORMAT, data[:self.tlm_1_size])
        except struct.error as e:
            raise ValueError(f"Error parsing TLM_1 data: {e}")

        # Map unpacked values to HEALTH_State
        health_fields = [
            "sw_ver_main", "sw_ver_minor", "up_time", "reset_count",
            "board_temp", "cumulative_error_count", "latest_error_code", "tele_cmd_count"
        ]
        result = {"health": {}, "adc": []}
        for i, name in enumerate(health_fields):
            result["health"][name] = unpacked[i]

        # Parse ADC channels
        adc_values = unpacked[8:8 + ADC_TOTAL_CH]  # Last 8 values from unpack
        for i, value in enumerate(adc_values):
            if i in self.ADC_CHANNELS:
                name, low, high, fmt, kwargs = self.ADC_CHANNELS[i]
                formatted_value = format_with_threshold(value, low, high, f"{name}: {fmt}", **kwargs)
            else:
                formatted_value = f"Unknown Channel_{i}: {value / ADC_MAX * VREF:.3f}V"

            result["adc"].append({
                "channel": i,
                "raw_value": value,
                "formatted": formatted_value
            })

        # Print formatted output
        if print_output:
            for name, print_fmt in self.HEALTH_FIELD_INFO:
                value = result["health"][name]
                if "0x{:02X}" in print_fmt:
                    print(print_fmt.format(value))
                else:
                    print(print_fmt.format(value))
            for adc_entry in result["adc"]:
                print(f"Channel_{adc_entry['channel']}: 0x{adc_entry['raw_value']:04X}          {adc_entry['formatted']}")

        return result


# Test with provided raw data
if __name__ == "__main__":
    raw_data = bytes.fromhex("01007856341233443200AABB5605F103E4036403E303DD03190AFB07")
    telemetry = Telemetry()
    result = telemetry.parse(raw_data)
    print("\nParsed Result:")
    print(result)


    import json

    # ... your parsing logic that results in the 'parsed_result' dictionary ...

    print("Parsed Result:")
    print(json.dumps(result, indent=4))

    r"""
    PS C:\Users\x-luo\python> python tm2.py
HEALTH data length: 12 bytes
TLM_1 data length: 28 bytes
Input data length: 28 bytes
Expected TLM_1 size: 28 bytes
Software Version Major: 1
Software Version Minor: 0
Up Time: 305419896 s
Reset Count: 51
Board Temperature: 68 °C
Cumulative Error Count: 50
Latest Error Code: 0xAA
Telemetry Command Count: 187
Channel_0: 0x0556          28V voltage: 9.340V
Channel_1: 0x03F1          28V current: 6.899A
Channel_2: 0x03E4          5V voltage: 1.216V
Channel_3: 0x0364          5V current: 1.060A
Channel_4: 0x03E3          -5V voltage: -1.215V
Channel_5: 0x03DD          -5V current: -1.208A
Channel_6: 0x0A19          board temperature: 20.20°C
Channel_7: 0x07FB          board VCC: 3.293V

Parsed Result:
{'health': {'sw_ver_main': 1, 'sw_ver_minor': 0, 'up_time': 305419896, 'reset_count': 51, 'board_temp': 68, 'cumulative_error_count': 50, 'latest_error_code': 170, 'tele_cmd_count': 187}, 'adc': [{'channel': 0, 'raw_value': 1366, 'formatted': '\x1b[91m28V voltage: 9.340V\x1b[0m'}, {'channel': 1, 'raw_value': 1009, 'formatted': '\x1b[91m28V current: 6.899A\x1b[0m'}, {'channel': 2, 'raw_value': 996, 'formatted': '\x1b[91m5V voltage: 1.216V\x1b[0m'}, {'channel': 3, 'raw_value': 868, 'formatted': '5V current: 1.060A'}, {'channel': 4, 'raw_value': 995, 'formatted': '\x1b[91m-5V voltage: -1.215V\x1b[0m'}, {'channel': 5, 'raw_value': 989, 'formatted': '\x1b[91m-5V current: -1.208A\x1b[0m'}, {'channel': 6, 'raw_value': 2585, 'formatted': 'board temperature: 20.20°C'}, {'channel': 7, 'raw_value': 2043, 'formatted': 'board VCC: 3.293V'}]}
Parsed Result:
{
    "health": {
        "sw_ver_main": 1,
        "sw_ver_minor": 0,
        "up_time": 305419896,
        "reset_count": 51,
        "board_temp": 68,
        "cumulative_error_count": 50,
        "latest_error_code": 170,
        "tele_cmd_count": 187
    },
    "adc": [
        {
            "channel": 0,
            "raw_value": 1366,
            "formatted": "\u001b[91m28V voltage: 9.340V\u001b[0m"
        },
        {
            "channel": 1,
            "raw_value": 1009,
            "formatted": "\u001b[91m28V current: 6.899A\u001b[0m"
        },
        {
            "channel": 2,
            "raw_value": 996,
            "formatted": "\u001b[91m5V voltage: 1.216V\u001b[0m"
        },
        {
            "channel": 3,
            "raw_value": 868,
            "formatted": "5V current: 1.060A"
        },
        {
            "channel": 4,
            "raw_value": 995,
            "formatted": "\u001b[91m-5V voltage: -1.215V\u001b[0m"
        },
        {
            "channel": 5,
            "raw_value": 989,
            "formatted": "\u001b[91m-5V current: -1.208A\u001b[0m"
        },
        {
            "channel": 6,
            "raw_value": 2585,
            "formatted": "board temperature: 20.20\u00b0C"
        },
        {
            "channel": 7,
            "raw_value": 2043,
            "formatted": "board VCC: 3.293V"
        }
    ]
}
PS C:\Users\x-luo\python>
    """
