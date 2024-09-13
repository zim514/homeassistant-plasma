# HomeAssistant Plasma - strip_controller.py
# (c) 2024 Snapcase
# Inspired by https://github.com/eminentspoon/picoplasma_homeassistant
# Uses effect examples from Pimoroni: https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/plasma_stick
# For Pimoroni Plasma Stick 2040W https://shop.pimoroni.com/products/plasma-stick-2040-w?variant=40359072301139
# Suppports home assistant MQTT discovery. Edit Config.py with your WiFi information and an MQTT broker connected to Home Assistant.  https://www.home-assistant.io/integrations/mqtt/


from random import randrange, uniform

import asyncio
import plasma
from plasma import plasma_stick

try:
    import config_local as CONFIG
except ImportError:
    import CONFIG


class StripController:
    def __init__(self):

        self.default_brightness = 128
        self.brightness = 0
        self.hue = 0
        self.saturation = 0

        self.state = False
        self.effect = "None"
        self.effect_task = None
        self.num_leds = CONFIG.NUM_LEDS

        # Create a list of [r, g, b] values that will hold current LED colours, for display
        # Create a list of [r, g, b] values that will hold target LED colours, to move towards

        self.current_leds = [[0, 0, 0] for _ in range(self.num_leds)]
        self.target_leds = [[0, 0, 0] for _ in range(self.num_leds)]

        self.led_strip = plasma.WS2812(CONFIG.NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_RGB)
        self.led_strip.start()

        self.effects = Effects(self.led_strip, CONFIG.NUM_LEDS, self.current_leds, self.target_leds)
        self.update_task = asyncio.create_task(self.update_led_strip_task())

    async def update_led_strip_task(self):
        while True:
            await self.effects.move_to_target(self.effects.current_leds, self.effects.target_leds, self.effects.num_leds)
            await StripController._display_current(self.effects.num_leds, self.effects.led_strip, self.effects.current_leds)
            await asyncio.sleep_ms(50)

    @staticmethod
    async def _display_current(num_leds, led_strip, current_leds):
        # paint our current LED colours to the strip_controller
        for i in range(num_leds):
            led_strip.set_rgb(i, current_leds[i][0], current_leds[i][1], current_leds[i][2])

    async def set_state(self, brightness=None, hue=None, saturation=None, state=None, effect=None):
        print(f"set_state: State: {state}, brightness: {brightness}, hue: {hue}, saturation: {saturation}, Effect: {effect}")

        if hue is not None:
            self.hue = hue
            if self.effect not in self.effects.colour_effects:
                print(f'Forcing static effect in hue. self.effect: {self.effect}')
                self.effect = "None"  # Force to 'Static' mode when color change received

        if saturation is not None:
            self.saturation = saturation
            if self.effect not in self.effects.colour_effects:
                print(f'Forcing static effect in saturation. self.effect: {self.effect}')
                self.effect = "None"  # Force to 'Static' mode when color change received

        if effect is not None:
            self.effect = effect

        if state is not None:
            self.state = state

        if state is True and (self.brightness == 0 or self.brightness is None):  # Force default brightness if there is none
            self.brightness = self.default_brightness

        if brightness is not None:
            self.brightness = brightness
        print(f"set_state: New State: {state}, brightness: {brightness}, hue: {hue}, saturation: {saturation}, Effect: {effect}")
        self._update_strip()

    def set_rgb(self, r, g, b):
        h, s, v = self.effects.rgb_to_hsv(r, g, b)
        self.set_state(hue=h, saturation=s, brightness=v, state=True)

    async def _apply_effect(self, effect, state, brightness, hue=None, saturation=None):
        print(f"Apply_effect: {effect}, state: {state}, hue: {hue}, saturation: {saturation}, brightness: {brightness}")
        if effect in self.effects.effects.keys():
            if effect in self.effects.colour_effects:
                await self.effects.effects[effect](self.effects, hue, saturation, brightness, state)

            else:
                await self.effects.effects[effect](self.effects, state, brightness)
        else:
            print("Unknown effect, default to Static/None")
            self.effects.effect = "None"
            await self.effects.effects["None"](self.effects, hue, saturation, brightness, state)

    def _update_strip(self):
        if self.effect_task:
            try:
                self.effect_task.cancel()
                print("Previous effect task cancelled.")
            except asyncio.CancelledError as e:
                print(f"Previous effect task NOT cancelled: {e}")

        print(f"Starting {self.effect} effect task")
        self.effect_task = asyncio.create_task(self._apply_effect(self.effect, self.state, self.brightness, self.hue, self.saturation))


class Effects:
    """
    animation_step_size
    Purpose: Controls the maximum step size for changes in LED color values.
    Description: This parameter determines the maximum amount by which an LED color value can change in one step. Higher values result in larger steps, causing the animation to transition more quickly between colors. Lower values result in smaller steps, making the transitions smoother and slower.

    animation_step_delay (ms)
    Purpose: Controls the delay between each step of the animation.
    Description: This parameter sets the delay in milliseconds between each step of the animation. Higher values result in a slower overall animation speed because there is more time between each color change step. Lower values make the animation faster by reducing the delay between steps.

    """

    def __init__(self, led_strip, num_leds, current_leds, target_leds):
        self.effects = {"None": Effects.static_effect,
                        "Storm": Effects.storm_effect,
                        "Rain": Effects.rain_effect,
                        "Clouds": Effects.clouds_effect,
                        "Snow": Effects.snow_effect,
                        "Sun": Effects.sun_effect,
                        "Sky": Effects.sky_effect,
                        # "Fire": Effects.fire_effect,
                        # "Rainbow": Effects.rainbow_effect,
                        "Chaser": Effects.chaser_effect,
                        "Sparkles": Effects.sparkles_effect}
        self.colour_effects = ["None", "Sparkles", "Chaser"]  # Effects that support setting a colour in HS mode

        self.led_strip = led_strip
        self.num_leds = num_leds
        self.current_leds = current_leds
        self.target_leds = target_leds

        self.default_animation_speed = self.animation_step_size = 1
        self.animation_step_delay = 10

    async def move_to_target(self, current_leds, target_leds, num_leds):
        for i in range(num_leds):
            for c in range(3):
                current = current_leds[i][c]
                target = target_leds[i][c]
                delta = target - current
                step = max(-self.animation_step_size, min(self.animation_step_size, delta))
                current_leds[i][c] += step

                if abs(current - target) < abs(step):
                    current_leds[i][c] = target

        # Introduce a delay between each step to control the animation speed
        await asyncio.sleep_ms(self.animation_step_delay)

    async def status_effect(self, r, g, b):
        self.animation_step_size = 5
        self.animation_step_delay = 20

        # print(f"Status Effect: {r}, {g}, {b}")
        for i in range(self.num_leds):
            self.target_leds[i] = [r, g, b]

    async def static_effect(self, hue, saturation, brightness, state):
        self.animation_step_size = 5
        self.animation_step_delay = 5

        h = round(hue / 360, 2)
        s = round(saturation / 100, 2)
        v = round((brightness / 255), 2) if state else 0

        r, g, b = self.hsv_to_rgb(h, s, v)

        print(f"Static Effect: {r}, {g}, {b}. hsv: {h}, {s}, {v}")
        for i in range(self.num_leds):
            self.target_leds[i] = [r, g, b]

    async def sparkles_effect(self, hue, saturation, brightness, state):
        self.animation_step_size = 3
        self.animation_step_delay = 1
        frame_speed = 200
        sparkle_frequency = 0.005
        brightness = min(max(brightness, 30), 255)  # Min & Max brightness for this effect, to stay within working strip range

        print(f"Sparkles Brightness: {brightness}, hue: {hue}, saturation: {saturation}, brightness: {brightness}")

        if state:
            if hue == 0 and saturation == 0:
                hue = 50
                saturation = 80

            h = hue / 360
            s = saturation / 100
            v = brightness / 255 if state else 0

            sparkle_rgb = self.hsv_to_rgb(h, s, v)
            background_rgb = self.hsv_to_rgb(h, s, v * 0.3)

            print(f"Sparkles Background RGB: {background_rgb}, sparkle_rgb: {sparkle_rgb}")
            self.target_leds = [background_rgb[:] for _ in range(self.num_leds)]

            while state:
                for i in range(self.num_leds):
                    if sparkle_frequency > uniform(0, 1):
                        self.target_leds[i] = sparkle_rgb[:]
                    if self.current_leds[i] == self.target_leds[i]:
                        self.target_leds[i] = background_rgb[:]

                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, state)

    async def chaser_effect(self, hue, saturation, brightness, state):
        self.animation_step_size = 2  # how quickly the light fades to black
        self.animation_step_delay = 1  # how slow the overall animation is
        frame_speed = 150  # how fast the light moves
        brightness = min(max(brightness, 30), 255)  # Min & Max brightness for this effect, to stay within working strip range

        print(f"Chaser Brightness: {brightness}, hue: {hue}, saturation: {saturation}, brightness: {brightness}")

        if state:
            if hue == 0 and saturation == 0:
                hue = 50
                saturation = 80

            h = hue / 360
            s = saturation / 100
            v = brightness / 255 if state else 0

            chaser_rgb = self.scale_brightness(self.hsv_to_rgb(h, s, v), brightness)

            background_rgb = [0, 0, 0]

            print(f"Chaser RGB: {chaser_rgb}")
            self.target_leds = [background_rgb[:] for _ in range(self.num_leds)]
            current_led = 0

            while state:
                for i in range(self.num_leds):
                    if i == current_led:
                        self.current_leds[i] = chaser_rgb[:]
                    if self.current_leds[i] == self.target_leds[i]:
                        self.target_leds[i] = background_rgb[:]

                if current_led <= self.num_leds:
                    current_led = (current_led + 1)
                else:
                    current_led = 0

                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, state)

    async def storm_effect(self, state, brightness):
        self.animation_step_size = 5
        self.animation_step_delay = 1
        frame_speed = 300  # time between colour updates
        brightness = min(max(brightness, 10), 255)
        lightning_chance = 0.02
        raindrop_chance = 0.05
        background = self.scale_brightness([1, 30, 120], brightness)
        lightning = self.scale_brightness([255, 255, 255], brightness)

        print(f"Storm Effect. State: {state}, brightness: {brightness}, lightning: {lightning}, background: {background}")

        while state:

            for i in range(self.num_leds):
                if raindrop_chance > uniform(0, 1):
                    self.current_leds[i] = self.scale_brightness([randrange(0, 50), randrange(50, 100), randrange(100, 255)], brightness)
                else:
                    self.target_leds[i] = background[:]

            if lightning_chance > uniform(0, 1):
                for x in range(self.num_leds):
                    self.current_leds[x] = lightning[:]

                # await asyncio.sleep_ms(500)

            await asyncio.sleep_ms(frame_speed)

        await self.static_effect(0, 0, 0, False)

    async def rain_effect(self, state, brightness):
        # splodgy blues

        self.animation_step_size = 1
        self.animation_step_delay = 1
        frame_speed = 200  # time between colour updates
        brightness = min(max(brightness, 10), 255)  # Min & Max brightness for this effect, to stay within range

        raindrop_chance = 0.01  # moderate rain

        background = self.scale_brightness([0, 15, 60], brightness)

        print(f"Rain Effect: State: {state}, brightness: {brightness}, raindrop_chance: {raindrop_chance}")
        if state:
            while state:
                for i in range(self.num_leds):
                    if raindrop_chance > uniform(0, 1):
                        self.current_leds[i] = self.scale_brightness([randrange(0, 50), randrange(20, 100), randrange(50, 255)], brightness)
                    else:
                        self.target_leds[i] = background[:]
                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, False)

    async def clouds_effect(self, state, brightness):

        cloud_colour = [165, 168, 138]  # partly cloudy
        brightness = min(max(brightness, 10), 230)  # Min & Max brightness for this effect, to stay within working strip range

        self.animation_step_size = 5
        self.animation_step_delay = 1
        frame_speed = 800  # how many ms between colour updates

        highlight = self.scale_brightness([x + 40 for x in cloud_colour], brightness)
        lowlight = self.scale_brightness([x - 40 for x in cloud_colour], brightness)
        normal = self.scale_brightness(cloud_colour, brightness)

        print(f"Clouds Effect: State: {state}, brightness: {brightness}, cloud_colour: {cloud_colour}, self.animation_step_size: {self.animation_step_size}, animation_step_delay: {self.animation_step_delay}")
        print(f"highlight: {highlight}, lowlight: {lowlight}, normal: {normal}")

        if state:
            for i in range(self.num_leds):
                self.target_leds[i] = self.scale_brightness(cloud_colour, brightness)  # paint with initial cloud colour

            while state:
                # add highlights and lowlights
                for i in range(self.num_leds):
                    if uniform(0, 1) < 0.02:  # highlight
                        self.target_leds[i] = highlight[:]
                    elif uniform(0, 1) < 0.02:  # lowlight
                        self.target_leds[i] = lowlight[:]
                    else:  # normal
                        self.target_leds[i] = normal[:]

                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, False)

    async def snow_effect(self, state, brightness):
        # splodgy whites
        self.animation_step_size = 5
        self.animation_step_delay = 1
        frame_speed = 200  # time between colour updates
        brightness = min(max(brightness, 10), 255)  # Min & Max brightness for this effect, to stay within range

        snowflake_chance = 0.003  # moderate snow

        snowflake = self.scale_brightness([227, 227, 227], brightness)
        backdrop = self.scale_brightness([54, 54, 54], brightness)

        print(f"Snow Effect: State: {state}, brightness: {brightness}, snowflake_chance: {snowflake_chance}")
        if state:

            while state:
                for i in range(self.num_leds):
                    if snowflake_chance > uniform(0, 1):
                        # paint a snowflake (use current rather than target, for an abrupt change to the drop colour)
                        self.current_leds[i] = snowflake[:]
                    else:
                        # paint backdrop
                        self.target_leds[i] = backdrop[:]
                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, False)

    async def sun_effect(self, state, brightness):
        # shimmering yellow
        self.animation_step_size = 2
        self.animation_step_delay = 1
        frame_speed = 425

        brightness = min(max(brightness, 40), 255)  # Min & Max brightness for this effect, to stay within yellow range

        print(f"Sun Effect: State: {state}, brightness: {brightness}, animation_step_size: {self.animation_step_size}, animation_step_delay: {self.animation_step_delay}, frame_speed: {frame_speed}")
        if state:
            while True:
                for i in range(self.num_leds):
                    self.target_leds[i] = self.scale_brightness([randrange(220, 255), randrange(220, 255), randrange(50, 90)], brightness)
                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, False)

    async def sky_effect(self, state, brightness):
        # sky blues
        self.animation_step_size = 2
        self.animation_step_delay = 1
        frame_speed = 700

        brightness = min(max(brightness, 10), 230)  # Min & Max brightness for this effect, to stay within range

        print(f"Sky Effect: State: {state}, brightness: {brightness}")
        if state:
            while state:
                for i in range(self.num_leds):
                    self.target_leds[i] = self.scale_brightness([randrange(0, 40), randrange(130, 190), randrange(170, 220)], brightness)

                await asyncio.sleep_ms(frame_speed)
        else:
            await self.static_effect(0, 0, 0, False)

    @micropython.native
    @staticmethod
    def scale_brightness(rgb, brightness):
        factor = brightness / 255
        return [int(color * factor) for color in rgb]

    @micropython.native
    @staticmethod
    def rgb_to_hsv_integer(r, g, b):
        # Scale the RGB values to be in the range of 0 to 255
        r, g, b = r * 1000 // 255, g * 1000 // 255, b * 1000 // 255
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        delta = max_c - min_c

        # Note: We're using scaled values to maintain precision
        h = 0
        if delta == 0:
            h = 0
        else:
            if max_c == r:
                h = ((60000 * (g - b) // delta) + 360000) % 360000
            elif max_c == g:
                h = ((60000 * (b - r) // delta) + 120000) % 360000
            else:  # max_c == b
                h = ((60000 * (r - g) // delta) + 240000) % 360000

        # Calculate saturation
        s = 0 if max_c == 0 else (100000 * delta // max_c)

        # Calculate value
        v = max_c * 100 // 1000

        # Scale back to desired range and return
        return h // 1000, s // 1000, v

    @micropython.native
    @staticmethod
    def hsv_to_rgb(hue, saturation, value):
        # Scale the inputs to use integers instead of floats
        hue = int(hue * 6 * 256)  # Scaling hue to range 0-1536
        saturation = int(saturation * 256)  # Scaling saturation to range 0-256
        value = int(value * 255)  # Scaling value to range 0-255

        if saturation == 0:
            return [value, value, value]

        sector = hue // 256
        fractional = hue % 256

        p = (value * (256 - saturation)) // 256
        q = (value * (256 - (saturation * fractional) // 256)) // 256
        t = (value * (256 - (saturation * (256 - fractional)) // 256)) // 256

        if sector == 0:
            return [value, t, p]
        elif sector == 1:
            return [q, value, p]
        elif sector == 2:
            return [p, value, t]
        elif sector == 3:
            return [p, q, value]
        elif sector == 4:
            return [t, p, value]
        else:
            return [value, p, q]
