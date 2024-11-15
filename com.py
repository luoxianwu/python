import serial
import time

# Configure the serial port
port = 'COM5'
baudrate = 9600
timeout = 1

try:
    # Open the serial port
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
    
    # Write to the port
    write_message = "Hello, COM5!"
    ser.write(write_message.encode('utf-8'))
    print(f"Wrote message: {write_message}")
    
    # Wait a moment to ensure data is transmitted
    time.sleep(0.1)
    
    # Read from the port
    if ser.in_waiting > 0:
        read_message = ser.read(ser.in_waiting).decode('utf-8')
        print(f"Read message: {read_message}")
    else:
        print("No data available to read.")
    
    # Close the serial port
    ser.close()

except serial.SerialException as e:
    print(f"Error opening serial port {port}: {e}")
except Exception as e:
    print(f"An error occurred: {e}")