# Website to llms.txt & Markdown RAG Converter

> High-performance, zero-proxy, deterministic B2B micro-actor designed for Make.com, n8n, Zapier, and autonomous AI Agents.

[![Apify Actor](https://apify.com/actor-badge?actor=website-llms-txt-generator)](https://apify.com/)
[![Protocol](https://img.shields.io/badge/Protocol-HTTP%20GET%20/%20Clean%20Markdown%20Parsing-blue.svg)](#)
[![Zero Proxy Required](https://img.shields.io/badge/Proxy-Zero%20Proxy%20Required-success.svg)](#)

---

## ⚡ What is Website to llms.txt & Markdown RAG Converter?

**Website to llms.txt & Markdown RAG Converter** is an enterprise-grade automated tool engineered to convertit n'importe quel site ou documentation en fichier standardisé llms.txt et llms-full.txt optimisé pour injection dans llms et rag..

Unlike fragile web scrapers that break upon layout changes or require expensive residential proxies, this Actor leverages standard, open protocols (HTTP GET / Clean Markdown Parsing) to deliver **100% deterministic, high-speed results** at the lowest possible computing cost.

### 🎯 Ideal For:
- **Automation Builders**: Seamlessly plug into **Make.com**, **n8n**, **Zapier**, and custom webhooks.
- **AI Agent Engineers**: Feed fresh, verified structured data directly to LLMs (Claude, OpenAI, Gemini) and RAG pipelines.
- **B2B Professionals**: Développeurs IA, architectes RAG, agents Cursor/Claude/Gemini.

---

## 🚀 Key Features

- **Zero-Proxy Architecture**: Works 100% reliably on standard cloud datacenter IPs without costly residential proxies.
- **Ultra-Fast Execution**: Minimal memory footprint (less than 256MB RAM) for lightning-fast runs.
- **Production-Ready JSON**: Validated structured output ready for direct database storage or API dispatch.
- **Continuous Maintenance**: Maintained and auto-updated weekly by the *Autonomous Factory Brain*.

---

## 📥 Input Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `startUrl` | `str` | `https://fastapi.tiangolo.com` | Input argument for `startUrl` |
| `maxDepth` | `int` | `1` | Input argument for `maxDepth` |
| `maxPages` | `int` | `10` | Input argument for `maxPages` |

---

## 📤 Sample Output

```json
[
  {
    "scrapedAt": "2026-10-18T08:00:00Z",
    "status": "SUCCESS",
    "protocol": "HTTP GET / Clean Markdown Parsing",
    "data": {
      "exampleKey": "exampleValue"
    }
  }
]
```

---

## 🔗 Integration Examples

### Make.com / n8n
1. Add an **Apify** node to your workflow.
2. Select **Run Actor** and choose `website-llms-txt-generator`.
3. Map the output dataset to your downstream CRM, Slack, Notion, or PostgreSQL database.

### Python / cURL
```bash
curl "https://api.apify.com/v2/acts/website-llms-txt-generator/runs?token=$APIFY_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"startUrl": "https://fastapi.tiangolo.com", "maxDepth": 1, "maxPages": 10}'
```

---

## 💼 Pricing & Support

- **Rental Model**: $29/month with unlimited runs under platform fair-use.
- **SLA & Maintenance**: Monitored and verified automatically.
- **Custom Integrations**: Open an issue or contact support via Apify Console.
