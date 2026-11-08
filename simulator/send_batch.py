"""
Sends a signed batch to /ingest, like a real box would.

python simulator/send_batch.py              # valid batch, should return 200
python simulator/send_batch.py --replay     # resend the last batch, should be 401
python simulator/send_batch.py --forge      # wrong key, should be 401
python simulator/send_batch.py --unknown    # unregistered device, should be 401
"""

import argparse
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
LAST_BATCH_FILE = ROOT / "simulator" / ".last_batch.json"
API_URL = os.getenv("API_URL", "http://localhost:8000")
DEVICE_ID = "box-001"


def device_key(device_id):
    for pair in os.getenv("DEVICE_SECRET_KEYS", "").split(","):
        if pair.startswith(device_id + ":"):
            return pair.split(":", 1)[1].encode()
    raise SystemExit(f"No key for {device_id} in DEVICE_SECRET_KEYS")


def build_batch(device_id, start_counter):
    readings, prev_hash = [], "0" * 64
    now = datetime.now(UTC).replace(microsecond=0)
    for i in range(3):
        t = (now + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        counter = start_counter + i
        power_on = i == 0
        digest = hashlib.sha256(
            f"{device_id}|{t}|{counter}|{int(power_on)}|{prev_hash}".encode()
        ).hexdigest()
        readings.append({"time": t, "counter": counter, "power_on": power_on,
                         "sensors": {"room_temp": 66.0 - i},
                         "prev_hash": prev_hash, "hash": digest})
        prev_hash = digest
    return {"device_id": device_id, "call_requested": False, "readings": readings}


def send(device_id, body: bytes, key: bytes):
    signature = hmac.new(key, body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"{API_URL}/ingest", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "X-Device-Id": device_id, "X-Signature": signature},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(resp.status, resp.read().decode())
    except urllib.error.HTTPError as err:
        print(err.code, err.read().decode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--replay", action="store_true")
    p.add_argument("--forge", action="store_true")
    p.add_argument("--unknown", action="store_true")
    args = p.parse_args()

    if args.replay:
        body = LAST_BATCH_FILE.read_bytes()
        send(DEVICE_ID, body, device_key(DEVICE_ID))
        return

    if args.unknown:
        body = json.dumps(build_batch("box-999", 1)).encode()
        send("box-999", body, b"made-up-key")
        return

    # Use a counter based on the clock so every valid run is new
    start = int(datetime.now(UTC).timestamp())
    body = json.dumps(build_batch(DEVICE_ID, start)).encode()

    if args.forge:
        send(DEVICE_ID, body, b"attacker-guessed-key")
        return

    LAST_BATCH_FILE.write_bytes(body)
    send(DEVICE_ID, body, device_key(DEVICE_ID))


if __name__ == "__main__":
    main()