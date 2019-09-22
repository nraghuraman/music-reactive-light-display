"""
Small sections of this code were adapted from https://learn.adafruit.com/sound-reactive-neopixel-peace-pendant/circuitpython-code

The code for signal processing was adapted from norwegiancreations.com/2016/03/arduino-tutorial-simple-high-pass-band-pass-and-band-stop-filtering/
"""
import array

import board
import neopixel
from analogio import AnalogIn

import audioio
import time

# Pins for NeoPixel strips
BASS_LED_PIN = board.D42
MID_LED_PIN = board.D43
TREBLE_LED_PIN = board.D44

N_PIXELS = 30  # Number of pixels per strip

DC_OFFSET = 502  # DC offset in mic signal - if unsure, leave 0

MIC_PIN = AnalogIn(board.A9)

bassPixels = neopixel.NeoPixel(BASS_LED_PIN, N_PIXELS, brightness=1.5, auto_write=True)
midPixels = neopixel.NeoPixel(MID_LED_PIN, N_PIXELS, brightness=1.5, auto_write=True)
treblePixels = neopixel.NeoPixel(TREBLE_LED_PIN, N_PIXELS, brightness=1.5, auto_write=True)

"""
FILTERING CODE
"""

# LOW_FREQ_ALPHA is a coefficient used for low pass filtering to extract the lowest frequencies from a 
# mic signal. HIGH_FREQ_ALPHA is used for low pass filtering to extract all but the highest frequencies.
# AVERAGE_ALPHA is used for low-pass filtering to extract all frequencies except extraneous noise.
LOW_FREQ_ALPHA = 0.008
HIGH_FREQ_ALPHA = 0.015
AVERAGE_ALPHA = 0.05

lowFreqLowPass = 0
highFreqLowPass = 0
average = 0

highPass = 0
bandPass = 0

SAMPLING_FREQUENCY = 7000 # Frequency with which to sample the microphone signal (in Hz)

count = 0

COUNT_TO_CHANGE_COLOR = 50

while True:
    count += 1
    n = int((MIC_PIN.value / 65536) * 1000)  # 10-bit ADC format
    n = n - DC_OFFSET # Center on zero

    # Implementation of three separate low pass filters. See above for the purpose of the filters,
    # and visit norwegiancreations.com/2016/03/arduino-tutorial-simple-high-pass-band-pass-and-band-stop-filtering/
    # for explanations on low pass filters
    lowFreqLowPass = (LOW_FREQ_ALPHA * n) + ((1 - LOW_FREQ_ALPHA) * lowFreqLowPass);
    highFreqLowPass = (HIGH_FREQ_ALPHA * n) + ((1 - HIGH_FREQ_ALPHA) * highFreqLowPass);
    average = (AVERAGE_ALPHA * n) + ((1 - AVERAGE_ALPHA) * average);

    # A high pass filter to extract all highest frequencies (except extraneous noise), implemented by subtracting
    # the low pass filter for higher frequencies from the low pass filter for all frequencies except extraneous noise
    highPass = average - highFreqLowPass;

    # A band pass filter for extracting all midrange frequencies from the microphone signal
    bandPass = highFreqLowPass - lowFreqLowPass;

    INTENSITY_SCALE = 40

    if count % COUNT_TO_CHANGE_COLOR == 0:
        bassBrightness = min(1, abs(lowFreqLowPass) / INTENSITY_SCALE)
        trebleBrightness = min(1, abs(highPass) / INTENSITY_SCALE)
        midBrightness = min(1, abs(bandPass) / INTENSITY_SCALE)

        # Fills in neopixel strips according to intensity of bass, mid, and treble tones in music
        bassPixels.fill((int(255 * bassBrightness), int(255 * bassBrightness), int(255 * bassBrightness))) # white
        midPixels.fill((int(35 * midBrightness), int(222 * midBrightness), int(255 * midBrightness))) # blue
        treblePixels.fill((int(255 * trebleBrightness), int(0 * trebleBrightness), int(200 * trebleBrightness))) # purple

        bassPixels.show()
        midPixels.show()
        treblePixels.show()
  
    time.sleep(1 / SAMPLING_FREQUENCY)
