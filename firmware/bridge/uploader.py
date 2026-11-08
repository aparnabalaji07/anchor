"""
Sends the box's readings (POST /ingest) and claim photos (POST /photos) to the ANCHOR backend.

- Samples a reading every SAMPLE_SECONDS (not every serial line)
- Builds the hash chain and signs each batch with HMAC, like docs/message-format.md
- Keeps unsent readings and retries, so it keeps working if Wi-Fi drops
- Saves the counter and last hash to a file so restarts are not seen as replays
- Photos that fail to upload are remembered in the same file and retried

Settings come from environment variables (or a .env file next to this script):
  ANCHOR_API_URL        e.g. http://155.138.221.23:8000
  ANCHOR_DEVICE_ID      e.g. box-001
  ANCHOR_DEVICE_SECRET  the same secret as box-001 in the server's DEVICE_SECRET_KEYS
"""

import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Load a simple .env file if one exists (KEY=value lines)
env_file = HERE / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

API_URL = os.getenv("ANCHOR_API_URL", "http://155.138.221.23:8000").rstrip("/")
DEVICE_ID = os.getenv("ANCHOR_DEVICE_ID", "box-001")
SECRET = os.getenv("ANCHOR_DEVICE_SECRET", "").encode()
SAMPLE_SECONDS = int(os.getenv("ANCHOR_SAMPLE_SECONDS", "10"))
UPLOAD_SECONDS = int(os.getenv("ANCHOR_UPLOAD_SECONDS", "30"))
STATE_FILE = HERE / ".anchor_state.json"

_lock = threading.Lock()
_photo_send_lock = threading.Lock()  # only one thread sends photos at a time
_pending = []
_flags = {"photo_consent": False, "call_requested": False}
_last_sample = 0.0


def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"counter": 0, "prev_hash": "0" * 64, "pending": []}


_state = _load_state()
_pending.extend(_state.get("pending", []))
_state.setdefault("pending_photos", [])  # [{"path": ..., "taken_at": ...}]


def _save_state():
    _state["pending"] = _pending
    STATE_FILE.write_text(json.dumps(_state))


def set_flags(photo_consent=None, call_requested=None):
    """Call this after the customer answers the voice prompts."""
    with _lock:
        if photo_consent is not None:
            _flags["photo_consent"] = bool(photo_consent)
        if call_requested is not None:
            _flags["call_requested"] = bool(call_requested)


def record(temp_f, light_raw, blackout):
    """Call this every time a sensor line is parsed. It only keeps one reading per SAMPLE_SECONDS."""
    global _last_sample
    now = time.time()
    if now - _last_sample < SAMPLE_SECONDS:
        return
    _last_sample = now

    with _lock:
        _state["counter"] += 1
        counter = _state["counter"]
        t = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        power_on = not blackout
        prev_hash = _state["prev_hash"]
        digest = hashlib.sha256(
            f"{DEVICE_ID}|{t}|{counter}|{int(power_on)}|{prev_hash}".encode()
        ).hexdigest()
        _pending.append({
            "time": t,
            "counter": counter,
            "power_on": power_on,
            "sensors": {"room_temp": float(temp_f), "light": int(light_raw)},
            "prev_hash": prev_hash,
            "hash": digest,
        })
        _state["prev_hash"] = digest
        _save_state()


def _upload_once():
    with _lock:
        if not _pending:
            return
        batch = _pending[:500]
        body = json.dumps({
            "device_id": DEVICE_ID,
            "photo_consent": _flags["photo_consent"],
            "call_requested": _flags["call_requested"],
            "readings": batch,
        }).encode()

    # Sign the exact bytes we send
    signature = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"{API_URL}/ingest", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "X-Device-Id": DEVICE_ID, "X-Signature": signature},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[anchor] uploaded {len(batch)} readings ({resp.status})")
            sent = True
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="ignore")
        if err.code == 401 and "replayed_counter" in detail:
            print("[anchor] server already had these readings, dropping them")
            sent = True
        else:
            print(f"[anchor] upload rejected ({err.code}): {detail}")
            sent = False
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        print(f"[anchor] offline, will retry: {err}")
        sent = False

    if sent:
        with _lock:
            del _pending[:len(batch)]
            _save_state()


def _send_photo(path, taken_at):
    """Returns True when the photo is done (saved, duplicate or unsendable), False to retry."""
    try:
        jpeg = Path(path).read_bytes()
    except OSError:
        print(f"[anchor] photo file is missing, skipping it: {path}")
        return True

    # Sign the time and the image together, like docs/message-format.md section 2
    signature = hmac.new(SECRET, taken_at.encode() + b"\n" + jpeg, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"{API_URL}/photos", data=jpeg, method="POST",
        headers={"Content-Type": "image/jpeg", "X-Device-Id": DEVICE_ID,
                 "X-Taken-At": taken_at, "X-Signature": signature},
    )
    name = Path(path).name
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"[anchor] photo uploaded: {name} ({resp.status})")
            return True
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="ignore")
        if err.code == 409:
            print(f"[anchor] server already has photo {name}")
            return True
        if err.code >= 500:
            print(f"[anchor] server error on photo {name} ({err.code}), will retry")
            return False
        print(f"[anchor] photo {name} rejected ({err.code}): {detail}. Not retrying; file kept at {path}")
        return True
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        print(f"[anchor] offline, photo {name} will retry: {err}")
        return False


def _send_pending_photos():
    if not _photo_send_lock.acquire(blocking=False):
        return  # another thread is already sending
    try:
        with _lock:
            queue = list(_state["pending_photos"])
        for item in queue:
            if not _send_photo(item["path"], item["taken_at"]):
                break  # still offline, try the rest next round
            with _lock:
                _state["pending_photos"].remove(item)
                _save_state()
    finally:
        _photo_send_lock.release()


def upload_photo(path, taken_at_iso):
    """Queue a saved photo and try to send it right away without blocking the camera loop."""
    with _lock:
        _state["pending_photos"].append({"path": str(path), "taken_at": taken_at_iso})
        _save_state()
    print(f"[anchor] uploading photo {Path(path).name}...")
    threading.Thread(target=_send_pending_photos, daemon=True).start()


def _loop():
    while True:
        _upload_once()
        _send_pending_photos()
        time.sleep(UPLOAD_SECONDS)


def start():
    """Start uploading in the background. Call once when the bridge starts."""
    if not SECRET:
        print("[anchor] WARNING: ANCHOR_DEVICE_SECRET is not set, uploads will be rejected")
    print(f"[anchor] uploading as {DEVICE_ID} to {API_URL} every {UPLOAD_SECONDS}s")
    if _state["pending_photos"]:
        print(f"[anchor] {len(_state['pending_photos'])} photo(s) from last time will be uploaded")
    threading.Thread(target=_loop, daemon=True).start()
