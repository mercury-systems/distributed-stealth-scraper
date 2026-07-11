# Distributed Asynchronous Stealth Scraping Node (v1.1)

An enterprise-grade, multi-tier web automation framework engineered to handle high-throughput data extraction across hardened anti-bot boundaries (Cloudflare Turnstile, Akamai, DataDome).

## 🛠️ Architectural Features

* **Multi-Engine Escalation Matrix:** Minimizes infrastructure overhead by utilizing high-performance, asynchronous `curl_cffi` network requests by default. Automatically escalates single tasks to resource-heavy browser instances only upon verifying a WAF challenge block.
* **Fingerprint & Context Isolation:** Manages distinct, localized persistent Chromium profiles mapped dynamically to unique directory hashes per proxy allocation, preventing global profile tracking.
* **Context Evasion Ingestion:** Automatically hooks evasion routines straight into the Chromium namespace using fine-grained `apply_stealth_async` API overrides at the context layer.
* **Persistent State Tracking:** Employs a local relational SQLite cookie vault to serialize and cache authenticated active session parameters, maintaining pool integrity across worker lifecycles.

## ⚡ Technical Specification
* **Core Transport:** Python Asyncio, `curl_cffi` (Native JA3/JA4 TLS fingerprint spoofing)
* **Orchestration:** Playwright (Chromium Headless Engine), `playwright-stealth`
* **Persistence Layer:** SQLite, JSON Serialization
