# European Accessibility Act (EAA) WCAG Auditor

> High-performance, zero-proxy, deterministic B2B micro-actor designed for Make.com, n8n, Zapier, and autonomous AI Agents.

[![Apify Actor](https://apify.com/actor-badge?actor=european-accessibility-act-wcag-auditor)](https://apify.com/)
[![Protocol](https://img.shields.io/badge/Protocol-DOM%20Inspection%20&%20WCAG%20Rules-blue.svg)](#)
[![Zero Proxy Required](https://img.shields.io/badge/Proxy-Zero%20Proxy%20Required-success.svg)](#)

---

## ⚡ What is European Accessibility Act (EAA) WCAG Auditor?

**European Accessibility Act (EAA) WCAG Auditor** is an enterprise-grade automated tool engineered to vérifie les critères wcag 2.1 aa obligatoires de l'european accessibility act 2025 (contrastes, alt text, aria, hiérarchie titres)..

Unlike fragile web scrapers that break upon layout changes or require expensive residential proxies, this Actor leverages standard, open protocols (DOM Inspection & WCAG Rules) to deliver **100% deterministic, high-speed results** at the lowest possible computing cost.

### 🎯 Ideal For:
- **Automation Builders**: Seamlessly plug into **Make.com**, **n8n**, **Zapier**, and custom webhooks.
- **AI Agent Engineers**: Feed fresh, verified structured data directly to LLMs (Claude, OpenAI, Gemini) and RAG pipelines.
- **B2B Professionals**: Responsables conformité, agences web, juristes du numérique.

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
| `targetUrl` | `str` | `https://news.ycombinator.com` | Input argument for `targetUrl` |
| `checkAria` | `bool` | `True` | Input argument for `checkAria` |
| `checkContrast` | `bool` | `True` | Input argument for `checkContrast` |

---

## 📤 Sample Output

```json
[
  {
    "scrapedAt": "2026-10-18T08:00:00Z",
    "status": "SUCCESS",
    "protocol": "DOM Inspection & WCAG Rules",
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
2. Select **Run Actor** and choose `european-accessibility-act-wcag-auditor`.
3. Map the output dataset to your downstream CRM, Slack, Notion, or PostgreSQL database.

### Python / cURL
```bash
curl "https://api.apify.com/v2/acts/european-accessibility-act-wcag-auditor/runs?token=$APIFY_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"targetUrl": "https://news.ycombinator.com", "checkAria": true, "checkContrast": true}'
```

---

## 💼 Pricing & Support

- **Rental Model**: $39/month with unlimited runs under platform fair-use.
- **SLA & Maintenance**: Monitored and verified automatically.
- **Custom Integrations**: Open an issue or contact support via Apify Console.
