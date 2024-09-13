# HomeAssistant Plasma


* Inspired by https://github.com/eminentspoon/picoplasma_homeassistant
* For Pimoroni Plasma Stick 2040W https://shop.pimoroni.com/products/plasma-stick-2040-w?variant=40359072301139
* Uses effect and WiFi examples from Pimoroni: https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/plasma_stick\
* MQTT from: https://github.com/micropython/micropython-lib/tree/master/micropython/umqtt.simple



# Overview
Micropython script to integrate [Pimoroni Plasma Stick 2040W](https://shop.pimoroni.com/products/plasma-stick-2040-w?variant=40359072301139) to [Home Assistant](https://www.home-assistant.io) via MQTT. Supports Home Assistant auto discovery and provides an [MQTT Light](https://www.home-assistant.io/integrations/light.mqtt/) entity.  
Supports colour, brightness and several effects. 



# Setup
1. [Setup MQTT](https://www.home-assistant.io/integrations/mqtt/) in Home Assistant
2. [Install Pimoroni Micropython](https://github.com/pimoroni/pimoroni-pico/blob/main/setting-up-micropython.md) to your [Plasma Stick](https://shop.pimoroni.com/products/plasma-stick-2040-w?variant=40359072301139), ensure you have at least [version 1.23](https://github.com/pimoroni/pimoroni-pico/releases/)
3. Modify CONFIG.py with your settings. You can also copy and rename to config_local.py to avoid overwriting your settings if updating the whole package
4. If correctly configured and connected, your device should now be visible as a light in Home Assistant, where it can be used and controlled like any other light.

# CONFIG.py


| **Setting**           | **Default**     |                                                                                                                   |
|-----------------------|-----------------|-------------------------------------------------------------------------------------------------------------------|
| NUM_LEDS              | 50              | Integer, Number of leads on the light strip                                                                       |
| WIFI_SSID             | "WIFI"          | WiFi Access Point Name                                                                                            |
| WIFI_PSK              | "PASSWORD"      | WiFi Password                                                                                                     |
| WIFI_COUNTRY          | "CA"            | Change to your local two-letter ISO 3166-1 country code                                                           |
| MQTT_SERVER           | "192.168.1.10"  | Address of MQTT broker                                                                                            |
| MQTT_PORT             | 1883            | Integer, 1833 is the default MQTT port                                                                            |
| MQTT_CLIENTID         | "plasma_1"      | Unique ID for this device, with no spaces                                                                         |
| MQTT_NAME             | "Plasma 1"      | Friendly name, as displayed in Home Assistant UIs                                                                 |
| MQTT_DISCOVERY_PREFIX | "homeassistant" | Default for home assistant, [configure in HA](https://www.home-assistant.io/integrations/mqtt/#discovery-options) |





# Status Effects and troubleshooting

At initial start up, the light strip colour will show the connection status and errors.
However, if the light strip successfully connected, it will keep the previous light state and quietly reconnect in the background. This is to avoid the strip suddenly going on in the middle of the night for a simple connection problem.  


| **Strip Colour** | **Meaning**                                                    |
|------------------|----------------------------------------------------------------|
| Alternating Blue | Connecting to Wi-Fi                                            |
| Green, then off  | Successfully connected to Wifi and MQTT. Ready!                |
| Red              | Error connecting to Wi-Fi.                                     |
| Orange           | Error establishing initial connection to MQTT broker, retrying |

The LED on the Pico W indicates a connection in progress.

| **Pico W LED** | **Meaning**                              |
|----------------|------------------------------------------|
| On             | Attempting Wi-Fi or MQTT connection      |
| Rapid blinking | Successfully connected and ready for use |
| Off            | Connected to Wifi and MQTT               |





