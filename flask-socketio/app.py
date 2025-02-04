import signal
import sys

import eventlet
eventlet.monkey_patch()  # Important for async operations

import time
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route("/")
def index():
    return render_template("index.html")  # Serves index.html from templates/

def send_count():
    """Background thread to send an incrementing count to clients"""
    count = 0
    while True:
        count += 1
        print(f"Emitting update_count: {count}")  # Debugging
        socketio.emit("update_count", {"count": count})
        eventlet.sleep(0.5)  # Correct: Use eventlet.sleep() instead of socketio.sleep()

@socketio.on("connect")
def handle_connect():
    print("✅ Client connected")

@socketio.on("disconnect")
def handle_disconnect():
    print("❌ Client disconnected")

# Graceful Shutdown Handler
def handle_exit(signum, frame):
    print("\n🛑 Shutting down gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, handle_exit)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # Handle termination signals    

# Start background task properly
if __name__ == "__main__":
    print("🚀 Flask WebSocket Server Starting...")
    #following both works, second is better
    #eventlet.spawn(send_count)  # Correct way to start the background task
    socketio.start_background_task(send_count)
    socketio.run(app, host="0.0.0.0", port=5000 )

