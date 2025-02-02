import paho.mqtt.client as mqtt
import time

# MQTT Broker Settings
BROKER = "broker.hivemq.com"  # Public broker
PORT = 1883
PUBLISH_TOPIC = "swan/telemetry"  # Publish telemetry data here
SUBSCRIBE_TOPIC = "swan/telecommand"  # Listen for telecommands

counter = 0  # Initialize counter

# Create MQTT client (New API)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Callback when connected to the broker
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ Connected to MQTT Broker!")
        print(f"📡 Subscribing to: {SUBSCRIBE_TOPIC}")
        client.subscribe(SUBSCRIBE_TOPIC)
    else:
        print(f"⚠️ Connection failed with code {reason_code}")

# Callback when a message is received
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"📩 Received command: {message} on topic {msg.topic}")

# Assign callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to MQTT broker
client.connect(BROKER, PORT, 60)
client.loop_start()  # Start MQTT loop in the background

# Publish telemetry message every second
while True:
    counter += 1
    telemetry_message = f"Telemetry Data - Counter: {counter}"
    client.publish(PUBLISH_TOPIC, telemetry_message)
    print(f"📤 Published: {telemetry_message} to {PUBLISH_TOPIC}")
    time.sleep(1)  # Wait for 1 second before sending the next message
