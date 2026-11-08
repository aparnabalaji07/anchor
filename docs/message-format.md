# Box → Backend Message Format (draft v2)

The box stores everything on its SD card during an outage. When power and Wi-Fi come back, it uploads in this order:

1. Sensor readings (POST /ingest)
2. Photos, one per request (POST /photos), only if the customer said yes

Every request is signed with the box's secret key.

---

## 1. Sensor readings: POST /ingest

Headers:

```
Content-Type: application/json
X-Device-Id: box-001
X-Signature: <HMAC-SHA256 of the raw request body, lowercase hex>
```

Body:

```json
{
  "device_id": "box-001",
  "photo_consent": true,
  "call_requested": false,
  "readings": [
    {
      "time": "2026-11-08T02:10:00Z",
      "counter": 42,
      "power_on": false,
      "sensors": {
        "light": 12,
        "room_temp": 51.2
      },
      "prev_hash": "a3f1...",
      "hash": "9bc2..."
    }
  ]
}
```

Fields:

- device_id: unique per box, set in firmware
- photo_consent: true if the customer said yes to claim photos, false if they said no. The box still sends readings either way.
- call_requested: optional. true if the customer asked their agent to call them.
- readings: one per sample, oldest first, max 500 per request
- time: UTC, ISO 8601
- counter: goes up by 1 every reading, never repeats or resets
- power_on: optional. false when the box is on battery. If missing, the backend uses the light sensor.
- sensors.light: raw light sensor value (0 to 4095 on the ESP32 ADC)
- sensors.room_temp: degrees Fahrenheit

Hash chain:
hash = SHA-256 of the string `device_id|time|counter|power_on|prev_hash`

- power_on is written as 1 or 0 (use 1 if the box does not track it)
- the first reading uses 64 zeros as prev_hash

---

## 2. Photos: POST /photos

One JPEG per request. The body is the raw image bytes, not JSON.

Headers:

```
Content-Type: image/jpeg
X-Device-Id: box-001
X-Taken-At: 2026-11-08T02:15:00Z
X-Signature: <HMAC-SHA256 of (X-Taken-At + "\n" + JPEG bytes), lowercase hex>
```

Notes:

- The signature covers the time and the image together, so neither can be changed after the photo is taken
- On the ESP32 this is one HMAC with two updates: the time string plus a newline, then the JPEG buffer
- Max size 2 MB per photo
- Sending the same photo twice returns 409 (already received). The box can treat that as success.

---

## Responses

- 200: saved
- 401: unknown device, bad signature, or replayed counter (logged on the server)
- 409: duplicate photo, already saved
- 422: malformed body

---
