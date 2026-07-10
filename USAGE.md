# 🛠️ Distributed Stealth Scraper: Operational Guide

Operational instructions, configuration flags, and testing guidelines for executing the Stealth Scraper node.

---

## ⚙️ 1. Configuration Real Estate (`stealth_engine.py`)

Primary parameter fields are maintained directly in the structural config map:

* `proxy_list`: An array list mapping connection strings. The value `"direct"` forces the loop back down to native local ISP routing pools for laboratory validation runs.
* `max_light_workers`: Maximum concurrent thread tasks allocated to the async request loops.
* `max_heavy_workers`: Rigid hardware throttle boundary (Semaphore) capping the volume of simultaneous persistent Chromium profiles to safeguard host memory.
* `challenge_keywords`: Signature strings used to trigger immediate engine escalation events.

---

## 🚀 2. Local Verification Suite

Ensure you have your async network layers and runtime prerequisites established:

```bash
pip install curl_cffi playwright pydantic playwright-stealth
playwright install chromium
```

### Run the Validation Layer:

```bash
python3 stealth_engine.py
```

### Expected Flow Telemetry:

The engine checks target endpoints, generates automated loop passes, and triggers an initial context-warming sequence.

Verified access structures pass parameters down to the local runtime index, returning payload length statistics straight to stdout.
