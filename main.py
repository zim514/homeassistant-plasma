# HomeAssistant Plasma
# (c) 2024 Snapcase
# Inspired by https://github.com/eminentspoon/picoplasma_homeassistant
# Uses effect examples from Pimoroni: https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/plasma_stick\
# MQTT from: https://github.com/micropython/micropython-lib/tree/master/micropython/umqtt.simple
# For Pimoroni Plasma Stick 2040W https://shop.pimoroni.com/products/plasma-stick-2040-w?variant=40359072301139
# Suppports home assistant MQTT discovery. Edit Config.py with your WiFi information and an MQTT broker connected to Home Assistant.  https://www.home-assistant.io/integrations/mqtt/

import sys

import uasyncio as asyncio
import ujson as json
from machine import Pin
from micropython import const
from umqtt.simple import MQTTClient

from strip_controller import StripController

try:
    import config_local as CONFIG
except ImportError:
    import CONFIG

from network_manager import NetworkManager

STATE_TOPIC = f'{CONFIG.MQTT_DISCOVERY_PREFIX}/light/{CONFIG.MQTT_CLIENTID}'
COMMAND_TOPIC = f'{CONFIG.MQTT_DISCOVERY_PREFIX}/light/{CONFIG.MQTT_CLIENTID}/set'
AVAILABILITY_TOPIC = f"{CONFIG.MQTT_DISCOVERY_PREFIX}/light/{CONFIG.MQTT_CLIENTID}/available"

RECONNECT_DELAY = const(10)


class HomeAssistantPlasmaStick:
    def __init__(self):
        self.strip_controller = StripController()
        self.network_manager = NetworkManager(CONFIG.WIFI_COUNTRY, status_handler=self.wifi_status_handler, error_handler=self.wifi_error_handler, client_timeout=15)
        self.mqtt_client = None
        self.message_queue = []  # List to act as a queue for incoming MQTT messages
        self.processing_message = False

        self.pico_led = Pin('LED', Pin.OUT)  # set up the Pico W's onboard LED
        self.pico_led.value(True)  #Turn on LED to indiciate initilization started

    async def wifi_status_handler(self, mode, status, ip):
        print('Attempting WiFi Connection')
        print(f"WiFi Status Handler: mode={mode}, status={status}, ip={ip}")
        self.pico_led.value(True)
        await self.strip_controller.effects.status_effect(0, 0, 128)
        await asyncio.sleep(2)

        if status is True:
            print(f'Wifi connect status: {status}')

            await self.strip_controller.effects.status_effect(0, 0, 255)
            await asyncio.sleep_ms(500)
            await self.strip_controller.effects.status_effect(0, 0, 0)
            self.pico_led.value(False)

        elif status is False:
            print(f'Wifi not connected: {status}')
            self.pico_led.value(True)
            await self.strip_controller.effects.status_effect(64, 0, 0)

        else:
            print(f"Waiting for connection: {status}")

            await self.strip_controller.effects.status_effect(0, 0, 64)
            await asyncio.sleep(2)

    async def wifi_error_handler(self, mode, message):
        print(f"Wifi Error: {mode}: {message}")
        self.pico_led.value(True)

        await self.strip_controller.effects.status_effect(128, 0, 0)
        await asyncio.sleep(RECONNECT_DELAY)
        while not self.network_manager.isconnected():
            print("Attempting to reconnect to Wifi..")
            await self.network_manager.client(CONFIG.WIFI_SSID, CONFIG.WIFI_PSK)
            await asyncio.sleep(RECONNECT_DELAY)

    async def mqtt_connect(self):
        self.pico_led.value(True)
        await self.strip_controller.effects.status_effect(0, 64, 0)
        while self.mqtt_client is None:
            print('MQTT: Init MQTT Client')
            mqtt_client = MQTTClient(CONFIG.MQTT_CLIENTID, CONFIG.MQTT_SERVER, CONFIG.MQTT_PORT, keepalive=60)
            mqtt_client.set_last_will(AVAILABILITY_TOPIC, "false")
            mqtt_client.set_callback(self.mqtt_callback)  # Set callback before connecting
            try:
                mqtt_client.connect()
                print('MQTT: Connected, subscribing to MQTT topics')
                mqtt_client.subscribe(f"{CONFIG.MQTT_DISCOVERY_PREFIX}/status", qos=1)
                mqtt_client.subscribe(COMMAND_TOPIC, qos=1)
                self.mqtt_client = mqtt_client
                await self.mqtt_announce()

                # Flash green to indicate connection:
                await self.strip_controller.effects.status_effect(0, 128, 0)
                await asyncio.sleep_ms(750)
                await self.strip_controller.effects.status_effect(0, 0, 0)

                for _ in range(5):
                    await asyncio.sleep_ms(100)
                    self.pico_led.value(True)
                    await asyncio.sleep_ms(100)
                    self.pico_led.value(False)



            except OSError as e:
                print(f'MQTT connection failed: {e}. Trying again in 15 seconds')
                await self.strip_controller.effects.status_effect(128, 64, 0)
                await asyncio.sleep_ms(500)
                await self.strip_controller.effects.status_effect(64, 32, 0)

                self.mqtt_client = None
                await asyncio.sleep(10)

    def mqtt_broadcast_state(self):
        print("MQTT: Update light state")
        print(f"MQTT Update: Effect: {self.strip_controller.effect}")
        if self.strip_controller.effect in self.strip_controller.effects.colour_effects:  # Effect supports colours - Static or Sparkles
            state = {
                "state": "ON" if self.strip_controller.state else "OFF",
                "effect": "EFFECT_OFF" if self.strip_controller.effect == "None" else self.strip_controller.effect,
                "brightness": round(self.strip_controller.brightness),
                "color_mode": "hs",
                "color": {
                    "h": round(self.strip_controller.hue),
                    "s": round(self.strip_controller.saturation),
                }
            }
        else:
            state = {
                "state": "ON" if self.strip_controller.state else "OFF",
                "effect": self.strip_controller.effect,
                "brightness": round(self.strip_controller.brightness),
                "color_mode": "brightness",
            }

        print("MQTT State update: {}".format(state))
        self.mqtt_client.publish(STATE_TOPIC, json.dumps(state), qos=1)

    def mqtt_callback(self, topic, msg):
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        print(f"MQTT Subscribed Message Received:  {topic}, message: {msg}")
        self.message_queue.append((topic, msg))

    async def mqtt_announce(self):
        print('Announce MQTT Config')
        payload = {
            "name": CONFIG.MQTT_NAME,
            "schema": "json",
            "qos": 1,
            "unique_id": CONFIG.MQTT_CLIENTID,
            "brightness": True,
            "brightness_scale": 255,
            "supported_color_modes": ["hs"],
            "state_topic": f"homeassistant/light/{CONFIG.MQTT_CLIENTID}",
            "command_topic": f"homeassistant/light/{CONFIG.MQTT_CLIENTID}/set",
            "retain": True,
            "effect": True,
            "effect_list": list(self.strip_controller.effects.effects.keys()),  # list of effects from Effects class
            #"availability_mode": "any",
            "availability": {
                "payload_not_available": "false",
                "payload_available": "true",
                "topic": AVAILABILITY_TOPIC
            }
        }
        print(f"MQTT Discovery Announce: Topic: {CONFIG.MQTT_DISCOVERY_PREFIX}/light/{CONFIG.MQTT_CLIENTID}/config, Payload {json.dumps(payload)}")
        self.mqtt_client.publish(f"{CONFIG.MQTT_DISCOVERY_PREFIX}/light/{CONFIG.MQTT_CLIENTID}/config", json.dumps(payload), qos=1)
        await asyncio.sleep(1)  # Home Assistant sometimes needs a moment before it's ready for the rest

        print("MQTT Setting Available to True")
        self.mqtt_client.publish(AVAILABILITY_TOPIC, "true", qos=1)

        self.mqtt_broadcast_state()

    @micropython.native
    async def process_messages(self):
        while True:
            if self.message_queue and not self.processing_message:
                self.processing_message = True
                topic, msg = self.message_queue.pop(0)
                if topic == f"{CONFIG.MQTT_DISCOVERY_PREFIX}/status" and msg == "online":
                    print("Home assistant is back online, announce auto discovery")
                    await self.mqtt_announce()
                elif topic == COMMAND_TOPIC:
                    command = json.loads(msg)
                    print(f"Set command received: {command}")
                    state = None
                    hue = None
                    saturation = None
                    brightness = None
                    effect = None
                    try:
                        state_command = command['state']
                        if state_command == "ON":
                            state = True
                        if state_command == "OFF":
                            state = False
                        print(f"State: {state}")
                    except KeyError:
                        pass
                    try:
                        color_command = command['color']
                        hue = color_command['h']
                        saturation = color_command['s']
                        print(f"Hue: {hue}, Sat: {saturation}")
                    except KeyError:
                        pass
                    try:
                        brightness = command['brightness']
                        print(f"Brightness:  = {brightness}")
                    except KeyError:
                        pass

                    try:
                        effect = command['effect']
                        print(f"Effect: {effect}")
                    except KeyError:
                        pass

                    print("Parsed command, updating led state")
                    await self.strip_controller.set_state(brightness=brightness, state=state, hue=hue, saturation=saturation, effect=effect)
                    self.mqtt_broadcast_state()
                self.processing_message = False
            await asyncio.sleep_ms(50)  # Small delay to yield control

    @micropython.native
    async def main(self):
        print(f'Starting up... homeassistant-plasmastick - {sys.version}')

        try:
            print('Start up Network_Manager')
            await self.network_manager.client(CONFIG.WIFI_SSID, CONFIG.WIFI_PSK)
        except Exception as e:
            if not self.network_manager.isconnected():
                print(f'Wifi connection failed! {e}. Will try again in {RECONNECT_DELAY} seconds.')
                await self.strip_controller.effects.status_effect(128, 0, 0)
                await asyncio.sleep(RECONNECT_DELAY)  #wait 15 seconds before trying again
                #return  # Exit if WiFi connection fails

        await self.mqtt_connect()
        print('MQTT: Ready')
        asyncio.create_task(self.process_messages())

        ping_counter = 0
        while True:
            try:
                if self.mqtt_client:
                    self.mqtt_client.check_msg()
                else:
                    await self.mqtt_connect()

                if ping_counter >= 30 and self.mqtt_client:  # Send a ping every 30 seconds
                    try:
                        self.mqtt_client.ping()
                    except OSError as e:
                        print(f'MQTT Ping failed! {e}')
                        if self.mqtt_client:
                            try:
                                self.mqtt_client.disconnect()  # ensure proper disconnection
                            except Exception:
                                pass
                        self.mqtt_client = None

                    ping_counter = 0
                ping_counter += 1
            except OSError as e:
                print(f'MQTT check_msg failed! Exception: {e}')
                if self.mqtt_client:
                    try:
                        self.mqtt_client.disconnect()  # ensure proper disconnection

                    except Exception:
                        pass
                self.mqtt_client = None
                print('MQTT Disconnected')
                #await self.mqtt_connect()  # Attempt to reconnect

            await asyncio.sleep(1)  # Check messages every second


if __name__ == '__main__':
    main = HomeAssistantPlasmaStick()
    asyncio.run(main.main())
