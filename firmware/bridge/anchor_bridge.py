"""
ANCHOR box bridge: runs on the laptop the Arduino is plugged into.

- Reads light, temperature and joystick values from the Arduino over USB serial
- Plays the two voice prompts and asks for consent
- Takes a photo when the joystick is pressed (only if the customer agreed)
- Sends readings and photos to the ANCHOR backend through uploader.py (signed, retried if offline)

Settings come from firmware/bridge/.env (see .env.example).
"""

import math
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2
import serial
import uploader  # also loads .env

HERE = Path(__file__).resolve().parent

SERIAL_PORT = os.getenv("ANCHOR_SERIAL_PORT", "/dev/cu.usbmodem1201")
BAUD_RATE = 9600
CAMERA_INDEX = int(os.getenv("ANCHOR_CAMERA_INDEX", "0"))
PHOTO_DIR = Path(os.getenv("ANCHOR_PHOTO_DIR", str(HERE / "photos")))
CLAIM_AUDIO = os.getenv("ANCHOR_CLAIM_AUDIO", str(HERE / "audio" / "claim_prompt.m4a"))
CONSENT_AUDIO = os.getenv("ANCHOR_CONSENT_AUDIO", str(HERE / "audio" / "consent_prompt.m4a"))
TEMP_SENSOR = os.getenv("ANCHOR_TEMP_SENSOR", "grove")  # grove, tmp36 or fahrenheit
BLACKOUT_LIGHT = int(os.getenv("ANCHOR_BLACKOUT_LIGHT", "80"))
JOYSTICK_PRESS = 1000
MAX_PHOTO_BYTES = 2 * 1024 * 1024  # the backend rejects anything bigger

# Format from the emailed sketch: "Light:512,Temperature:480,X:510,Y:505"
LINE_RE = re.compile(r"Light:(\d+),?\s*Temperature:(\d+),?\s*X:(\d+),?\s*Y:(\d+)")
# Format the Arduino is running now: "Temperature Raw: 62 | Light Raw: 288"
SIMPLE_RE = re.compile(r"Temperature Raw:\s*(\d+)\s*\|\s*Light Raw:\s*(\d+)")


def to_fahrenheit(raw):
    """Convert the Arduino's 0-1023 reading to degrees F."""
    if TEMP_SENSOR == "fahrenheit":
        return float(raw)
    if TEMP_SENSOR == "lm35":
        celsius = raw * 5000 / 1024 / 10
        return round(celsius * 9 / 5 + 32, 1)   
    if TEMP_SENSOR == "tmp36":
        millivolts = raw * 5000 / 1024
        celsius = (millivolts - 500) / 10
    else:  # Grove temperature sensor (thermistor, B = 4275)
        if raw <= 0 or raw >= 1023:
            return None
        resistance = 100000 * (1023.0 / raw - 1.0)
        celsius = 1 / (math.log(resistance / 100000) / 4275 + 1 / 298.15) - 273.15
    return round(celsius * 9 / 5 + 32, 1)


def parse(line):
    """Returns (light, temp_raw, x, y) or None."""
    m = LINE_RE.search(line)
    if m:
        return tuple(int(v) for v in m.groups())
    m = SIMPLE_RE.search(line)
    if m:
        temp_raw, light = int(m.group(1)), int(m.group(2))
        return (light, temp_raw, 0, 0)  # no joystick values in this format
    return None


def shrink_if_too_big(path, frame):
    """Re-encode at lower JPEG quality until the file fits under MAX_PHOTO_BYTES."""
    if path.stat().st_size <= MAX_PHOTO_BYTES:
        return
    for quality in (85, 75, 65, 55, 45, 35):
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok and len(buf) <= MAX_PHOTO_BYTES:
            path.write_bytes(buf.tobytes())
            print(f">>> photo re-saved at quality {quality} to fit under 2 MB")
            return
    print(">>> photo is still over 2 MB, the server will reject it")


def play_audio(filepath):
    if os.path.exists(filepath):
        os.system(f"afplay '{filepath}'")
    else:
        print(f"(audio not found at {filepath}, skipping)")


def handle_line(line, frame=None, photos_allowed=False):
    values = parse(line)
    pressed = "CAPTURE" in line
    if values:
        light, temp_raw, x, _y = values
        temp_f = to_fahrenheit(temp_raw)
        blackout = light <= BLACKOUT_LIGHT
        if temp_f is not None:
            uploader.record(temp_f, light, blackout)
        pressed = pressed or x > JOYSTICK_PRESS
    if pressed:
        if photos_allowed and frame is not None:
            PHOTO_DIR.mkdir(parents=True, exist_ok=True)
            taken = datetime.now(UTC)
            path = PHOTO_DIR / f"incident_{int(taken.timestamp())}.jpg"
            if cv2.imwrite(str(path), frame):
                print(f">>> photo saved: {path}")
                shrink_if_too_big(path, frame)
                uploader.upload_photo(path, taken.strftime("%Y-%m-%dT%H:%M:%SZ"))
            else:
                print(f">>> could not save photo to {path}")
        elif not photos_allowed:
            print(">>> joystick pressed, but photos were declined. no photo taken.")
        time.sleep(1.5)  # matches the Arduino's debounce


def main():
    print("connecting to arduino...")
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(3)
    uploader.start()

    print("\n--- anchor incident flow starting ---")
    play_audio(CLAIM_AUDIO)
    print("We have detected a potential issue in your home. Would you like to report "
          "this issue to State Farm and begin preparing an insurance claim?")
    wants_claim = input("yes/no: ").strip().lower() in ("yes", "y")

    wants_photos = False
    if wants_claim:
        play_audio(CONSENT_AUDIO)
        print("Would you consent to us taking a photograph of the affected area "
              "to include with your claim report?")
        wants_photos = input("yes/no: ").strip().lower() in ("yes", "y")
    else:
        print("No claim started. Still recording the outage so your agent can check on you.")

    uploader.set_flags(call_requested=wants_claim, photo_consent=wants_photos)

    cam = None
    if wants_photos:
        cam = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)
        if not cam.isOpened():
            print("camera not found, continuing without photos")
            cam, wants_photos = None, False
        else:
            print("camera on. press the joystick to take a photo, q to quit.")

    try:
        while True:
            frame = None
            if cam is not None:
                ok, frame = cam.read()
                if ok:
                    cv2.imshow("Anchor", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                else:
                    frame = None
            try:
                if arduino.in_waiting > 0:
                    line = arduino.readline().decode("utf-8", errors="ignore").strip()
                    handle_line(line, frame, wants_photos)
                elif cam is None:
                    time.sleep(0.05)
            except serial.SerialException as err:
                print(f"usb hiccup: {err}")
                time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        if cam is not None:
            cam.release()
        cv2.destroyAllWindows()
        print("bridge stopped. unsent readings are saved and will upload next time.")


if __name__ == "__main__":
    main()
