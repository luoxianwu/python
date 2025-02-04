import eventlet
eventlet.monkey_patch()  # Ensure compatibility with eventlet for async operations

import time
import sys
import signal
import serial  # PySerial for COM port
import serial.tools.list_ports  # Import for listing available COM ports
from flask import Flask, render_template
from flask_socketio import SocketIO

# Flask-SocketIO Setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Serial Port Configuration (Initially None, selected dynamically)
SERIAL_PORT = None
BAUD_RATE = 9600
ser = None  # Serial connection variable

def list_available_ports():
    """Returns a list of available COM ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]  # Extract COM port names

@app.route("/")
def index():
    return render_template("index.html")  # Serves index.html from templates/

@socketio.on("get_com_ports")
def handle_get_com_ports():
    """Handles request to list available COM ports."""
    print("get_com_ports");
    ports = list_available_ports()
    print(f"🔍 Available COM Ports: {ports}")
    socketio.emit("com_ports", ports)  # Send available COM ports to the frontend

@socketio.on("select_com_port")
def handle_select_com_port(data):
    """Handles user selection of a COM port and opens the connection."""
    global SERIAL_PORT, ser
    selected_port = data.get("port")
    print(f"selected_port:{selected_port}")
    if selected_port:
        SERIAL_PORT = selected_port
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"✅ Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
            socketio.emit("serial_status", {"status": "connected", "port": SERIAL_PORT})
        except Exception as e:
            print(f"❌ Failed to open serial port {SERIAL_PORT}: {e}")
            socketio.emit("serial_status", {"status": "error", "message": str(e)})

def read_serial():
    """Background thread to read from the COM port and emit data to clients."""
    while True:
        if ser and ser.is_open:
            try:
                data = ser.readline().decode("utf-8").strip()
                if data:
                    print(f"📡 Received from COM: {data}")
                    socketio.emit("serial_data", {"data": data})  # Emit to frontend
            except Exception as e:
                print(f"❌ Serial Read Error: {e}")
        eventlet.sleep(0.1)  # Avoid CPU overload

@socketio.on("send_to_serial")
def handle_send_to_serial(data):
    """Handles messages from the frontend and writes them to the COM port."""
    global ser
    message = data.get("message", "").strip()
    
    if ser and ser.is_open:
        try:
            ser.write((message + "\n").encode("utf-8"))
            print(f"📤 Sent to {SERIAL_PORT}: {message}")
        except Exception as e:
            print(f"❌ Serial Write Error: {e}")

# Graceful Shutdown Handler
def handle_exit(signum, frame):
    print("\n🛑 Shutting down gracefully...")
    if ser and ser.is_open:
        ser.close()
        print("🔌 Serial port closed.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, handle_exit)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # Handle termination signals

# Start background task properly
if __name__ == "__main__":
    print("🚀 Flask WebSocket Server Starting...")
    socketio.start_background_task(read_serial)  # Start COM port reader thread
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
