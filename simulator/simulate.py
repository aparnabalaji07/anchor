import argparse
import hashlib
import os
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
DATABASE_URL = os.environ["TIGERDATA_URL"]

NUM_HOUSEHOLDS = 100
READING_INTERVAL = timedelta(minutes=10)
WINDOW = timedelta(hours=24)
CENTER_LAT, CENTER_LNG = 33.1507, -96.8236  # Frisco, TX

STREETS = [
    "Elm St", "Oak Ave", "Pine Rd", "Maple Dr", "Cedar Ln", "Rose Garden Blvd",
    "Lebanon Rd", "Preston Rd", "Main St", "Eldorado Pkwy", "Coit Rd", "Teel Pkwy",
]

# (name, chance, min outage hours, max outage hours)
SCENARIOS = [
    ("no_outage", 0.25, 0, 0),
    ("short", 0.35, 1, 3),
    ("medium", 0.25, 6, 10),
    ("long", 0.15, 14, 20),
]


def pick_scenario():
    roll = random.random()
    total = 0
    for name, chance, lo, hi in SCENARIOS:
        total += chance
        if roll <= total:
            return name, lo, hi
    return SCENARIOS[-1][0], SCENARIOS[-1][2], SCENARIOS[-1][3]


def make_household(i):
    return {
        "device_id": f"sim-{i:03d}",
        "address": f"{random.randint(100, 9999)} {random.choice(STREETS)}, Frisco, TX",
        "zip": random.choice(["75033", "75034", "75035", "75036"]),
        "lat": CENTER_LAT + random.uniform(-0.04, 0.04),
        "lng": CENTER_LNG + random.uniform(-0.04, 0.04),
        "lives_alone": random.random() < 0.2,
        "medical_device": random.random() < 0.08,
        "mobility_limits": random.random() < 0.1,
    }


def make_readings(device_id, start):
    """Build one household's timeline with a hash chain like the real box."""
    scenario, lo, hi = pick_scenario()
    outage_start = outage_end = None
    if scenario != "no_outage":
        hours = random.uniform(lo, hi)
        outage_start = start + timedelta(hours=random.uniform(0, 3))
        outage_end = outage_start + timedelta(hours=hours)

    rows = []
    prev_hash = "0" * 64
    t = start
    counter = 1
    while t < start + WINDOW:
        power_on = not (outage_start and outage_start <= t < outage_end)

        # Add sensor fields here later, for example: "room_temp": ...
        #payload = {"device_id": device_id, "time": t.isoformat(),
         #          "power_on": power_on, "counter": counter}

        digest = hashlib.sha256(
            f"{device_id}|{t.strftime('%Y-%m-%dT%H:%M:%SZ')}|{counter}|{int(power_on)}|{prev_hash}".encode()
        ).hexdigest()

        rows.append((t, device_id, power_on, counter, digest, prev_hash))
        prev_hash = digest
        t += READING_INTERVAL
        counter += 1
    return scenario, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete old simulated data first")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    start = (datetime.now(UTC) - WINDOW).replace(second=0, microsecond=0)
    counts = {name: 0 for name, *_ in SCENARIOS}

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        if args.reset:
            cur.execute("DELETE FROM readings WHERE device_id LIKE 'sim-%'")
            cur.execute("DELETE FROM call_requests WHERE household_id IN "
                        "(SELECT id FROM households WHERE simulated)")
            cur.execute("DELETE FROM contact_status WHERE household_id IN "
                        "(SELECT id FROM households WHERE simulated)")
            cur.execute("DELETE FROM claim_drafts WHERE household_id IN "
                        "(SELECT id FROM households WHERE simulated)")
            cur.execute("DELETE FROM households WHERE simulated")
            print("Deleted old simulated data.")

        for i in range(1, NUM_HOUSEHOLDS + 1):
            h = make_household(i)
            cur.execute(
                """INSERT INTO households
                    (device_id, address, zip, lat, lng, lives_alone,
                    medical_device, mobility_limits, simulated)
                    VALUES (%(device_id)s, %(address)s, %(zip)s, %(lat)s, %(lng)s,
                            %(lives_alone)s, %(medical_device)s, %(mobility_limits)s, TRUE)
                    RETURNING id""",
                h,
            )
            household_id = cur.fetchone()[0]

            scenario, rows = make_readings(h["device_id"], start)
            counts[scenario] += 1

            with cur.copy(
                "COPY readings (time, device_id, power_on, counter, hash, prev_hash) FROM STDIN"
            ) as copy:
                for row in rows:
                    copy.write_row(row)

            cur.execute(
                "INSERT INTO contact_status (household_id) VALUES (%s)", (household_id,)
            )
            # Some customers in longer outages press the call-me button
            if scenario in ("medium", "long") and random.random() < 0.3:
                cur.execute(
                    "INSERT INTO call_requests (household_id) VALUES (%s)", (household_id,)
                )

    print(f"Created {NUM_HOUSEHOLDS} simulated households.")
    for name, n in counts.items():
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()