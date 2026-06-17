"""
Run this script ONCE to generate the 4 beep WAV files.
Works on any computer (Windows, Mac, Linux, or the Pi itself).
Requires only Python standard library — no pip needed.

Output files (save these to ~/mentorship/ on the Pi):
  beep_start.wav    - short beep when event starts
  beep_warn.wav     - 1-minute warning
  beep_rotate.wav   - rotate now! (end of session)
  beep_end.wav      - long final bell (end of event)
"""

import wave
import struct
import math
import os

SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit

def generate_wav(filename, frequency, duration_ms, volume=0.8):
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    attack = int(SAMPLE_RATE * 0.01)
    release = int(SAMPLE_RATE * 0.08)

    with wave.open(filename, 'w') as f:
        f.setnchannels(CHANNELS)
        f.setsampwidth(SAMPLE_WIDTH)
        f.setframerate(SAMPLE_RATE)

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Envelope
            env = 1.0
            if i < attack:
                env = i / attack
            elif i > n_samples - release:
                env = (n_samples - i) / release
            val = int(volume * env * 32767 * math.sin(2 * math.pi * frequency * t))
            val = max(-32768, min(32767, val))
            f.writeframes(struct.pack('<h', val))

    print(f"Created: {filename}")

output_dir = os.path.dirname(os.path.abspath(__file__))

generate_wav(os.path.join(output_dir, "beep_start.wav"),   frequency=880,  duration_ms=250)
generate_wav(os.path.join(output_dir, "beep_warn.wav"),    frequency=1100, duration_ms=180)
generate_wav(os.path.join(output_dir, "beep_rotate.wav"),  frequency=660,  duration_ms=900)
generate_wav(os.path.join(output_dir, "beep_end.wav"),     frequency=440,  duration_ms=3000, volume=0.95)

print("\nDone! Copy all 4 .wav files to ~/mentorship/ on your Pi.")
