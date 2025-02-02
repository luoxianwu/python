import paho.mqtt.client as mqtt
from flask import Flask, render_template
from flask_socketio import SocketIO
import eventlet

# Flask Setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# MQTT Broker Settings
BROKER = "broker.hivemq.com"
PORT = 1883
SUBSCRIBE_TOPIC = "swan/telemetry"  # Receive telemetry
PUBLISH_TOPIC = "swan/telecommand"  # Send commands

# MQTT Client Setup
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

subscribed = False  # Global variable to track subscription

def on_connect(client, userdata, flags, reason_code, properties):
    global subscribed
    if reason_code == 0:
        if not subscribed:
            print(f"✅ Connected to MQTT Broker! Subscribing to: {SUBSCRIBE_TOPIC}")
            client.subscribe(SUBSCRIBE_TOPIC)
            subscribed = True  # Ensure it only subscribes once
    else:
        print(f"⚠️ Connection failed with code {reason_code}")

'''
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"📩 Telemetry Data: {message}")

    # Ensure message is sent to all clients
    #socketio.emit('mqtt_message', {'topic': msg.topic, 'message': message}, broadcast=True)
    #socketio.emit('mqtt_message', {'topic': msg.topic, 'message': message}, namespace='/')
    #socketio.emit('mqtt_message', {'topic': msg.topic, 'message': message}, namespace='/', broadcast=True)
    socketio.emit('mqtt_message', {'topic': msg.topic, 'message': message}, namespace='/', to='broadcast')
'''
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"📩 Telemetry Data: {message}")  # Ensure MQTT message is received

    try:
        # Emit the message to web clients
        socketio.emit('mqtt_message', {'topic': msg.topic, 'message': message}, namespace='/')
        print(f"📡 Sent to Web UI: {message}")  # Debug: Confirm message is emitted
    except Exception as e:
        print(f"❌ SocketIO Emit Error: {e}")  # Catch any errors




mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("publish_message")
def handle_publish(json):
    command = json["message"]
    print(f"📤 Sending Command: {command} to {PUBLISH_TOPIC}")
    mqtt_client.publish(PUBLISH_TOPIC, command)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
