# hackutd

After a big power outage, the customers who were hit the hardest are often the ones who never call their insurance agent.

We built a sensor box that records what happened in the home during the outage, with no camera or microphone. Our dashboard tells State Farm agents who to call first and drafts the claim for them to review.

## Structure

- firmware/ ESP32 sensor box code
- backend/ FastAPI server
- frontend/ React agent dashboard
- db/ TigerData schema
- simulator/ Fake household data and attack scripts
- docs/ Diagrams and pitch notes

## Setup

Copy .env.example to .env and fill in the values.
