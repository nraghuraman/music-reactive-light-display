# An implementation of a web server using an ESP 32 and a microphone signal in order to send data to clients
# regarding colors of lights for bass, mid, and treble tones.
#
# This code is still a work in progress, and utilizes much of the code from mic_filtering.py. Please view
# that code for a more thorough explanation of filtering.
#
# Much of this code was adapted from Adafruit's esp32spi_wsgiserver.py
import os
import board
import busio
import neopixel
import array
import audioio
import time, gc

from digitalio import DigitalInOut
from analogio import AnalogIn

mic_pin = AnalogIn(board.A9)

from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_wifimanager as wifimanager
import adafruit_esp32spi.adafruit_esp32spi_wsgiserver as server

# This example depends on the 'static' folder in the examples folder
# being copied to the root of the circuitpython filesystem.
# This is where our static assets like html, js, and css live.

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

try:
    import json as json_module
except ImportError:
    import ujson as json_module

print("ESP32 SPI simple web server test!")

# SAM32 board ESP32 Setup
dtr = DigitalInOut(board.DTR)
esp32_cs = DigitalInOut(board.TMS) #GPIO14
esp32_ready = DigitalInOut(board.TCK) #GPIO13
esp32_reset = DigitalInOut(board.RTS)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset, gpio0_pin=dtr, debug=False)

## If you want to create a WIFI hotspot to connect to with secrets:
secrets = {"ssid": "My ESP32 AP!", "password": "supersecret"}
wifi = wifimanager.ESPSPI_WiFiManager(esp, secrets)
wifi.create_ap()

class SimpleWSGIApplication:
    """
    An example of a simple WSGI Application that supports
    basic route handling and static asset file serving for common file types
    """

    INDEX = "/index.html"
    CHUNK_SIZE = 8912 # max number of bytes to read at once when reading files

    def __init__(self, static_dir=None, debug=False):
        self._debug = debug
        self._listeners = {}
        self._start_response = None
        self._static = static_dir
        if self._static:
            self._static_files = ["/" + file for file in os.listdir(self._static)]

    def __call__(self, environ, start_response):
        """
        Called whenever the server gets a request.
        The environ dict has details about the request per wsgi specification.
        Call start_response with the response status string and headers as a list of tuples.
        Return a single item list with the item being your response data string.
        """
        if self._debug:
            self._log_environ(environ)

        self._start_response = start_response
        status = ""
        headers = []
        resp_data = []

        key = self._get_listener_key(environ["REQUEST_METHOD"].lower(), environ["PATH_INFO"])
        if key in self._listeners:
            status, headers, resp_data = self._listeners[key](environ)

        self._start_response(status, headers)
        return resp_data

    def on(self, method, path, request_handler):
        """
        Register a Request Handler for a particular HTTP method and path.
        request_handler will be called whenever a matching HTTP request is received.

        request_handler should accept the following args:
            (Dict environ)
        request_handler should return a tuple in the shape of:
            (status, header_list, data_iterable)

        :param str method: the method of the HTTP request
        :param str path: the path of the HTTP request
        :param func request_handler: the function to call
        """
        self._listeners[self._get_listener_key(method, path)] = request_handler

    def serve_file(self, file_path, directory=None):
        status = "200 OK"
        headers = [("Content-Type", self._get_content_type(file_path))]

        full_path = file_path if not directory else directory + file_path
        def resp_iter():
            with open(full_path, 'rb') as file:
                while True:
                    chunk = file.read(self.CHUNK_SIZE)
                    if chunk:
                        yield chunk
                    else:
                        break

        return (status, headers, resp_iter())

    def toHexadecimal(self, rgbTuple):
        return rgbTuple[0] << 16 | rgbTuple[1] << 8 | rgbTuple[2]

    def serve_rgb_value(self, tone_range):
        status = "200 OK"
        headers = [("Content-Type", "text/plain")]

        def resp():
            return str(self.toHexadecimal(colors_dict[tone_range]))

        return (status, headers, resp())

    def _log_environ(self, environ): # pylint: disable=no-self-use
        print("environ map:")
        for name, value in environ.items():
            print(name, value)

    def _get_listener_key(self, method, path): # pylint: disable=no-self-use
        return "{0}|{1}".format(method.lower(), path)

    def _get_content_type(self, file): # pylint: disable=no-self-use
        ext = file.split('.')[-1]
        if ext in ("html", "htm"):
            return "text/html"
        if ext == "js":
            return "application/javascript"
        if ext == "css":
            return "text/css"
        if ext in ("jpg", "jpeg"):
            return "image/jpeg"
        if ext == "png":
            return "image/png"
        return "text/plain"

colors_dict = {}

# Our HTTP Request handlers
def bass(environ):
    #print("Getting bass")
    return web_app.serve_rgb_value("bass")

def mids(environ):
    #print("Getting mids")
    return web_app.serve_rgb_value("mids")

def treble(environ):
    #print("Getting treble")
    return web_app.serve_rgb_value("treble")

web_app = SimpleWSGIApplication()

web_app.on("GET", "/bass", bass)
web_app.on("GET", "/mids", mids)
web_app.on("GET", "/treble", treble)

# Here we setup our server, passing in our web_app as the application
server.set_interface(esp)
wsgiServer = server.WSGIServer(80, application=web_app)

print("open this IP in your browser: ", esp.pretty_ip(esp.ip_address))

dc_offset = 502  # DC offset in mic signal - if unusure, leave 0

lowAverageAlpha = 0.008
highAverageAlpha = 0.015
averageAlpha = 0.05

lowPass = 0
highAverage = 0
veryHighAverage = 0
average = 0

highPass = 0
bandPass = 0

SAMPLING_FREQUENCY = 7000 #4 KHz

# Start the server
wsgiServer.start()

count = 0
while True:
    # Our main loop where we have the server poll for incoming requests
    try:
        #if updateCount % 100 == 0:
        wsgiServer.update_poll()

        # The code for filtering was adapted from
        # norwegiancreations.com/2016/03/arduino-tutorial-simple-high-pass-band-pass-and-band-stop-filtering/

        count += 1
        n = int((mic_pin.value / 65536) * 1000)  # 10-bit ADC format
        n = n - dc_offset # Center on zero

        lowPass = (lowAverageAlpha * n) + ((1 - lowAverageAlpha) * lowPass);
        highAverage = (highAverageAlpha * n) + ((1 - highAverageAlpha) * highAverage);
        average = (averageAlpha * n) + ((1 - averageAlpha) * average);

        highPass = average - highAverage;
        bandPass = highAverage - lowPass;

        if count % 50 == 0:
            bassBrightness = min(1, abs(lowPass) / 40)
            trebleBrightness = min(1, abs(highPass) / 40)
            midBrightness = min(1, abs(bandPass) / 40)

            colors_dict['bass'] = (int(255 * bassBrightness), int(255 * bassBrightness), int(255 * bassBrightness)) #white
            colors_dict['mids'] = (int(35 * midBrightness), int(222 * midBrightness), int(255 * midBrightness)) #blue
            colors_dict['treble'] = (int(255 * trebleBrightness), int(0 * trebleBrightness), int(200 * trebleBrightness)) #purple
    except (ValueError, RuntimeError) as e:
        print("Failed to update server, restarting ESP32\n", e)
        wifi.reset()
        continue
    gc.collect()
    time.sleep(1/SAMPLING_FREQUENCY)