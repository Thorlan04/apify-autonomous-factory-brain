# B2B Domain SPF DKIM DMARC MX Security Auditor

> High-performance, zero-proxy, deterministic B2B micro-actor designed for Make.com, n8n, Zapier, and autonomous AI Agents.

[![Apify Actor](https://apify.com/actor-badge?actor=email-security-spf-dkim-dmarc-checker)](https://apify.com/)
[![Protocol](https://img.shields.io/badge/Protocol-DNS%20over%20HTTPS%20(DoH)-blue.svg)](#)
[![Zero Proxy Required](https://img.shields.io/badge/Proxy-Zero%20Proxy%20Required-success.svg)](#)

---

## ⚡ What is B2B Domain SPF DKIM DMARC MX Security Auditor?

**B2B Domain SPF DKIM DMARC MX Security Auditor** is an enterprise-grade automated tool engineered to analyse en profondeur les enregistrements dns d'un domaine d'entreprise pour vérifier la délivrabilité email, l'alignement dmarc et spf..

Unlike fragile web scrapers that break upon layout changes or require expensive residential proxies, this Actor leverages standard, open protocols (DNS over HTTPS (DoH)) to deliver **100% deterministic, high-speed results** at the lowest possible computing cost.

### 🎯 Ideal For:
- **Automation Builders**: Seamlessly plug into **Make.com**, **n8n**, **Zapier**, and custom webhooks.
- **AI Agent Engineers**: Feed fresh, verified structured data directly to LLMs (Claude, OpenAI, Gemini) and RAG pipelines.
- **B2B Professionals**: Équipes RevOps, agences Cold Email, RSSI.

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
| `domain` | `str` | `google.com` | Input argument for `domain` |

---

## 📤 Sample Output

```json
[
  {
    "scrapedAt": "2026-10-18T08:00:00Z",
    "status": "SUCCESS",
    "protocol": "DNS over HTTPS (DoH)",
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
2. Select **Run Actor** and choose `email-security-spf-dkim-dmarc-checker`.
3. Map the output dataset to your downstream CRM, Slack, Notion, or PostgreSQL database.

### Python / cURL
```bash
curl "https://api.apify.com/v2/acts/email-security-spf-dkim-dmarc-checker/runs?token=$APIFY_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"domain": "google.com"}'
```

---

## 💼 Pricing & Support

- **Rental Model**: $15/month with unlimited runs under platform fair-use.
- **SLA & Maintenance**: Monitored and verified automatically.
- **Custom Integrations**: Open an issue or contact support via Apify Console.
