import struct

# ANSI color codes for terminal output
RED = "\033[91m"
RESET = "\033[0m"

# Conversion constants
ADC_MAX = 4095      # 12-bit ADC
VREF = 3.3          # Reference voltage
TEMP_SCALE = 128.0  # Temperature scaling factor

class Telemetry:
    HEALTH_STRUCT_FORMAT = "<BBbBIBBHHH"  # Little-endian, 16 bytes

    HEALTH_FIELD_INFO = [
        ("sw_ver_main", "Software Version Major: {}", None),
        ("sw_ver_minor", "Software Version Minor: {}", None),
        ("board_temp", "Board Temperature: {:.1f} °C", lambda temp: temp),
        ("board_vcc", "Board VCC: {:.1f} V", lambda vcc: vcc / 255 * VREF * 2),
        ("up_time", "Up Time: {} ms", None), 
        ("reset_count", "Reset Count: {}", None),
        ("latest_error_code", "Latest Error Code: {}", lambda err: f"0x{err:02X}"),
        ("cumulative_error_count", "Cumulative Error Count: {}", None),
        ("tele_cmd_count", "Telemetry Command Count: {}", None),
        ("telemetry_count", "Telemetry Count: {}", None),
    ]

    ADC_CHANNELS = {
        0: ("board temperature", 15.0, 30.0, "{:.1f}°C", lambda value: value / TEMP_SCALE),
        1: ("board VCC", 3.00, 3.80, "{:.1f}V", lambda value: value / ADC_MAX * VREF * 2),
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

        if print_output:
            print("Health Data:")
            
            # --- MODIFIED: Align the health data output ---
            # Find the length of the longest key string for alignment by splitting on '{'
            max_key_len = max(len(info[1].split('{')[0]) for info in self.HEALTH_FIELD_INFO)
            
            for i, (name, print_fmt, process_func) in enumerate(self.HEALTH_FIELD_INFO):
                raw_value = unpacked_health[i]
                processed_value = process_func(raw_value) if process_func else raw_value
                result["health"][name] = processed_value
                
                # Split the format string to get the key and the format specifier
                key, fmt_spec = print_fmt.split("{", 1)
                
                # Re-add the opening brace to the format specifier
                full_fmt = "{" + fmt_spec
                
                # Print the aligned key and the formatted value
                print(f"{key:<{max_key_len}}{full_fmt.format(processed_value)}")
            # --- END OF MODIFICATION ---

        if print_output:
            print("\nADC Channel Values:")

        for i, raw_value in enumerate(unpacked_adc):
            if i % 8 == 0:
                print(f"{f'ADC{i}:':<8}", end="")
            
            print(f" 0x{raw_value:04X}", end="")
            
            if (i + 1) % 8 == 0:
                print()
        if (i + 1) % 8 != 0:
            print()
            
            if i in self.ADC_CHANNELS:
                name, low, high, fmt, conversion_func = self.ADC_CHANNELS[i]
                converted_value = conversion_func(raw_value)
                formatted_value = self.format_with_threshold(converted_value, low, high, f"{name}: {fmt.format(converted_value)}")
                is_out_of_range = converted_value < low or converted_value > high
            else:
                converted_value = raw_value / ADC_MAX * VREF
                formatted_value = f"Unknown Channel_{i}: {converted_value:.3f}V"
                is_out_of_range = False
            
            result["adc"].append({
                "channel": i,
                "raw_value": raw_value,
                "converted_value": converted_value,
                "formatted": formatted_value,
                "is_out_of_range": is_out_of_range
            })

        return result

    @staticmethod
    def format_with_threshold(value, low, high, format_str):
        """Format value with color if out of range."""
        if value < low or value > high:
            return f"{RED}{format_str}{RESET}"
        return format_str


# Test with provided raw data
if __name__ == "__main__":
    raw_data = bytes.fromhex("0B161A7F7856341233AA320000000100270AFA077B04E2031804B6031C04BF04")
    telemetry = Telemetry()
    result = telemetry.parse(raw_data)
    print("\nParsed Result:")
    # print(result)