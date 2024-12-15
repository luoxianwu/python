import struct
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
            print(f"Channel_{index}: 0x{value:04X}") 