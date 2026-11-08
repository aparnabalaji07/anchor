# Box → Backend Message Format (draft)

## Endpoint

POST /ingest
Content-Type: application/json
X-Device-Id: box-001
X-Signature: <HMAC-SHA256 of the raw request body, hex>

## Body

```json
{
  "device_id": "box-001",
  "call_requested": false,
  "readings": [
    {
      "time": "2026-11-08T02:10:00Z",
      "counter": 42,
      "power_on": false,
      "sensors": {
        "room_temp": 51.2
      },
      "prev_hash": "a3f1...",
      "hash": "9bc2..."
    }
  ]
}
```

## Fields

- device_id: unique per box, set in firmware
- call_requested: true if the customer pressed the call-me button since the last upload
- readings: one entry per sample, oldest first. The box stores these on SD while offline and sends them in batches when power and Wi-Fi return.
- time: UTC, ISO 8601, from the real-time clock
- counter: goes up by 1 every reading and never repeats or resets (used to block replays)
- power_on: false when the box is running on battery
- sensors: whatever sensors the box has. Keys are optional. Agreed names so far: room_temp (°F), pipe_temp (°F), fridge_temp (°F), leak (true/false)
- prev_hash / hash: tamper-evident chain (see below)

## Hash chain

hash = SHA-256 of this exact string:
`device_id|time|counter|power_on|prev_hash`

- power_on is written as `1` or `0`
- the first reading uses 64 zeros as prev_hash

## Signature

- Each box has a secret key, shared with the backend only
- X-Signature = HMAC-SHA256(secret_key, raw body bytes), as lowercase hex
- The backend rejects: unknown device_id, a bad signature, or any counter that was already received
