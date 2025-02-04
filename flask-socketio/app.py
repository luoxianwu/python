import eventlet
eventlet.monkey_patch()  # Ensure compatibility with eventlet for async operations

import time
import sys
import signal
import serial  # PySerial for COM port
from flask import Flask, render_template
from flask_socketio import SocketIO

# Flask-SocketIO Setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Serial Port Configuration
SERIAL_PORT = "COM30"  # Change this to your actual COM port (e.g., "/dev/ttyUSB0" on Linux)
BAUD_RATE = 9600

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"✅ Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
except Exception as e:
    print(f"❌ Failed to open serial port: {e}")
    ser = None

@app.route("/")
def index():
    return render_template("index.html")  # Serves index.html from templates/

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

@socketio.on("connect")
def handle_connect():
    print("✅ Client connected")

@socketio.on("disconnect")
def handle_disconnect():
    print("❌ Client disconnected")

@socketio.on("send_to_serial")
def handle_send_to_serial(data):
    """Handles messages from the frontend and writes them to the COM port."""
    message = data.get("message", "").strip()
    if ser and ser.is_open:
        try:
            ser.write((message + "\n").encode("utf-8"))
            print(f"📤 Sent to COM: {message}")
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
    socketio.run(app, host="0.0.0.0", port=5000)
