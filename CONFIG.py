# Defaults. Copy and rename to config_local.py to avoid overwriting your settings if reinstalling the whole package


NUM_LEDS = 50  # Number of LEDs on the light strip

WIFI_SSID = "WIFI"
WIFI_PSK = "PASSWORD"
WIFI_COUNTRY = "CA"

MQTT_SERVER = "192.168.1.10"  # Address to MQTT broker
MQTT_PORT = 1883  # 1833 is the default port
MQTT_CLIENTID = "plasma_1"  # Unique ID for this device, with no spaces
MQTT_NAME = "Plasma 1"  # Friendly name, as displayed in Home Assistant UIs

MQTT_DISCOVERY_PREFIX = "homeassistant"  # default for home assistant

# Add your MQTT username and password here
# You can use a Home Assistant user account!
MQTT_USER = "MQTT_USERNAME"
MQTT_PASSWORD = "MQTT_PASSWORD"
