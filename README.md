# Shopify Fast Catalog & Inventory Monitor

> High-performance, zero-proxy, deterministic B2B micro-actor designed for Make.com, n8n, Zapier, and autonomous AI Agents.

[![Apify Actor](https://apify.com/actor-badge?actor=shopify-fast-catalog-products-json)](https://apify.com/)
[![Protocol](https://img.shields.io/badge/Protocol-HTTP%20REST%20/products.json-blue.svg)](#)
[![Zero Proxy Required](https://img.shields.io/badge/Proxy-Zero%20Proxy%20Required-success.svg)](#)

---

## ⚡ What is Shopify Fast Catalog & Inventory Monitor?

**Shopify Fast Catalog & Inventory Monitor** is an enterprise-grade automated tool engineered to scrape l'intégralité du catalogue public, variantes de prix, inventaires et sku d'une boutique shopify via le endpoint natif sans headless browser..

Unlike fragile web scrapers that break upon layout changes or require expensive residential proxies, this Actor leverages standard, open protocols (HTTP REST /products.json) to deliver **100% deterministic, high-speed results** at the lowest possible computing cost.

### 🎯 Ideal For:
- **Automation Builders**: Seamlessly plug into **Make.com**, **n8n**, **Zapier**, and custom webhooks.
- **AI Agent Engineers**: Feed fresh, verified structured data directly to LLMs (Claude, OpenAI, Gemini) and RAG pipelines.
- **B2B Professionals**: E-commerçants, outils de veille tarifaire, agences Make/n8n.

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
| `storeUrl` | `str` | `https://shop.fender.com` | Input argument for `storeUrl` |
| `maxPages` | `int` | `2` | Input argument for `maxPages` |
| `limitPerPage` | `int` | `50` | Input argument for `limitPerPage` |

---

## 📤 Sample Output

```json
[
  {
    "scrapedAt": "2026-10-18T08:00:00Z",
    "status": "SUCCESS",
    "protocol": "HTTP REST /products.json",
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
2. Select **Run Actor** and choose `shopify-fast-catalog-products-json`.
3. Map the output dataset to your downstream CRM, Slack, Notion, or PostgreSQL database.

### Python / cURL
```bash
curl "https://api.apify.com/v2/acts/shopify-fast-catalog-products-json/runs?token=$APIFY_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"storeUrl": "https://shop.fender.com", "maxPages": 2, "limitPerPage": 50}'
```

---

## 💼 Pricing & Support

- **Rental Model**: $19/month with unlimited runs under platform fair-use.
- **SLA & Maintenance**: Monitored and verified automatically.
- **Custom Integrations**: Open an issue or contact support via Apify Console.
