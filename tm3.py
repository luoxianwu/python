import struct

# ANSI color codes for terminal output
RED = "\033[91m"
RESET = "\033[0m"

# Conversion constants
ADC_MAX = 4095       # 12-bit ADC
VREF = 3.3         # Reference voltage
TEMP_SCALE = 128.0  # Temperature scaling factor


class Telemetry:
    HEALTH_STRUCT_FORMAT = "<BBbBIBBHHH"  # Little-endian, 16 bytes

    # Health field names, print formats, and optional processing functions
    HEALTH_FIELD_INFO = [
        ("sw_ver_main", "Software Version Major: {}", None),
        ("sw_ver_minor", "Software Version Minor: {}", None),
        ("board_temp", "Board Temperature: {:.1f} °C", lambda temp: temp),  # Modified to 1 decimal place
        ("board_vcc", "Board VCC: {:.1f} V", lambda vcc: vcc / 255 * VREF * 2),  # Modified to 1 decimal place
        ("up_time", "Up Time: {} s", None),
        ("reset_count", "Reset Count: {}", None),
        ("latest_error_code", "Latest Error Code: 0x{}", lambda err: f"0x{err:02X}"),
        ("cumulative_error_count", "Cumulative Error Count: {}", None),
        ("tele_cmd_count", "Telemetry Command Count: {}", None),
        ("telemetry_count", "Telemetry Count: {}", None),
    ]

    # ADC channel definitions (as before)
    ADC_CHANNELS = {
        0: ("board temperature", 15.0, 30.0, "{:.1f}°C", lambda value: value / TEMP_SCALE), # Modified to 1 decimal place
        1: ("board VCC", 3.00, 3.80, "{:.1f}V", lambda value: value / ADC_MAX * VREF * 2),   # Modified to 1 decimal place
        2: ("28V voltage", 25.0, 30.0, "{:.3f}V", lambda value: value / ADC_MAX * 28.0),
        3: ("28V current", 0.5, 1.5, "{:.3f}A", lambda value: value / ADC_MAX * 28.0),
        4: ("5V voltage", 4.75, 5.25, "{:.3f}V", lambda value: value / ADC_MAX * 5.0),
        5: ("5V current", 0.5, 1.5, "{:.3f}A", lambda value: value / ADC_MAX * 5.0),
        6: ("-5V voltage", -5.25, -4.75, "{:.3f}V", lambda value: -(value / ADC_MAX * 5.0)),
        7: ("-5V current", 0.5, 1.5, "{:.3f}A", lambda value: -(value / ADC_MAX * 5.0)),
    }

    def __init__(self):
        pass

    def parse(self, data, print_output=True):
        self.health_size = struct.calcsize(self.HEALTH_STRUCT_FORMAT)
        adc_size = len(data) - self.health_size
        adc_channels = int(adc_size / 2)
        adc_format = f"<{adc_channels}H"

        if len(data) < self.health_size:
            raise ValueError(f"Data too short: got {len(data)} bytes, need at least {self.health_size} for health.")

        try:
            health_data = data[:self.health_size]
            adc_data = data[self.health_size:]

            unpacked_health = struct.unpack(self.HEALTH_STRUCT_FORMAT, health_data)
            unpacked_adc = struct.unpack(adc_format, adc_data)

        except struct.error as e:
            raise ValueError(f"Error parsing data: {e}")

        result = {"health": {}, "adc": []}

        # Map and process health data
        for i, (name, print_fmt, process_func) in enumerate(self.HEALTH_FIELD_INFO):
            raw_value = unpacked_health[i]
            processed_value = process_func(raw_value) if process_func else raw_value
            result["health"][name] = processed_value
            if print_output:
                print(print_fmt.format(processed_value))

        # Parse ADC channels
        for i, raw_value in enumerate(unpacked_adc):
            if i in self.ADC_CHANNELS:
                name, low, high, fmt, conversion_func = self.ADC_CHANNELS[i]
                converted_value = conversion_func(raw_value)
                formatted_value = self.format_with_threshold(converted_value, low, high, f"{name}: {fmt}")
                result["adc"].append({
                    "channel": i,
                    "raw_value": raw_value,
                    "converted_value": converted_value,
                    "formatted": formatted_value
                })
                if print_output:
                    if i in [0, 1]:  # print channels 0 and 1 without unit.
                        print(f"Channel_{i}: 0x{raw_value:04X}    {name} raw data")
                    else:
                        print(f"Channel_{i}: 0x{raw_value:04X}    {formatted_value}")
            else:
                converted_value = raw_value / ADC_MAX * VREF  # Default conversion
                formatted_value = f"Unknown Channel_{i}: {converted_value:.3f}V"
                result["adc"].append({
                    "channel": i,
                    "raw_value": raw_value,
                    "converted_value": converted_value,
                    "formatted": formatted_value
                })
                if print_output:
                    print(f"Unknown Channel_{i}: 0x{raw_value:04X}    {formatted_value}")

        return result

    @staticmethod
    def format_with_threshold(value, low, high, format_str):
        """Format value with color if out of range."""
        formatted = format_str.format(value)
        if value < low or value > high:
            return f"{RED}{formatted}{RESET}"
        return formatted


# Test with provided raw data
if __name__ == "__main__":
    raw_data = bytes.fromhex("0100220d7856341233443200AABB5605F103E4036403E303DD03190AFB07")
    telemetry = Telemetry()
    result = telemetry.parse(raw_data)
    print("\nParsed Result:")
    print(result)

    import json

    print("Parsed Result (JSON):")
    print(json.dumps(result, indent=4))

