import os
import sys
import json
import re
from urllib.parse import urlparse
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/dns-json"
}

DOH_ENDPOINTS = [
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query"
]

COMMON_DKIM_SELECTORS = [
    "google", "k1", "selector1", "s1", "default", "mail", "k2", "s2048", "dmarc",
    "ms", "zoho", "mandrill", "sendgrid", "mailchimp", "hubspot", "amazonses"
]


def clean_domain(raw_input: str) -> str:
    """Extract clean domain string from user input."""
    raw = str(raw_input).strip().lower()
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        raw = parsed.netloc or parsed.path
    raw = raw.split("/")[0].split(":")[0]
    return raw.strip(".")


def doh_query(domain: str, record_type: str) -> list:
    """Perform DoH (DNS over HTTPS) query returning record data strings."""
    for endpoint in DOH_ENDPOINTS:
        try:
            params = {"name": domain, "type": record_type}
            resp = requests.get(endpoint, params=params, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if "Answer" in data:
                    results = []
                    for ans in data["Answer"]:
                        data_val = ans.get("data", "").strip('"')
                        # Clean TXT records concatenated strings
                        if data_val.startswith('"') and data_val.endswith('"'):
                            data_val = data_val[1:-1]
                        data_val = data_val.replace('" "', '')
                        results.append(data_val)
                    return results
                return []
        except Exception:
            continue
    return []


def analyze_mx(domain: str) -> dict:
    """Analyze MX records for the domain."""
    records = doh_query(domain, "MX")
    parsed_mx = []
    for rec in records:
        parts = rec.split()
        if len(parts) >= 2 and parts[0].isdigit():
            parsed_mx.append({"priority": int(parts[0]), "server": parts[1].rstrip(".")})
        else:
            parsed_mx.append({"priority": 0, "server": rec.rstrip(".")})

    parsed_mx.sort(key=lambda x: x["priority"])
    return {
        "found": len(parsed_mx) > 0,
        "count": len(parsed_mx),
        "records": parsed_mx
    }


def analyze_spf(domain: str) -> dict:
    """Analyze SPF record for syntax, policy strictness, and estimated DNS lookups."""
    records = doh_query(domain, "TXT")
    spf_records = [r for r in records if r.startswith("v=spf1") or "v=spf1" in r]

    if not spf_records:
        return {
            "found": False,
            "raw": None,
            "strictness": "missing",
            "lookup_count": 0,
            "issues": ["No SPF record found. Emails sent from this domain are at risk of being marked as spam."]
        }

    raw_spf = spf_records[0]
    issues = []

    if len(spf_records) > 1:
        issues.append("Multiple SPF records found. This violates RFC standards and causes SPF validation failure.")

    # Check strictness / qualifier
    strictness = "unknown"
    if "-all" in raw_spf:
        strictness = "HardFail (-all)"
    elif "~all" in raw_spf:
        strictness = "SoftFail (~all)"
    elif "?all" in raw_spf:
        strictness = "Neutral (?all)"
    elif "+all" in raw_spf:
        strictness = "Pass (+all - DANGEROUS)"
        issues.append("SPF record contains '+all' which allows anyone to send emails on behalf of this domain.")
    else:
        issues.append("SPF record is missing an 'all' mechanism at the end.")

    # Estimate DNS Lookups (include, a, mx, ptr, exists, redirect)
    tokens = raw_spf.split()
    lookup_mechanisms = [t for t in tokens if any(t.startswith(prefix) for prefix in ["include:", "a", "mx", "ptr", "exists:", "redirect="])]
    lookup_count = len(lookup_mechanisms)

    if lookup_count > 10:
        issues.append(f"SPF record exceeds 10 DNS lookup limit (Estimated lookups: {lookup_count}). SPF will break.")

    return {
        "found": True,
        "raw": raw_spf,
        "strictness": strictness,
        "lookup_count_estimate": lookup_count,
        "issues": issues
    }


def analyze_dmarc(domain: str) -> dict:
    """Analyze DMARC record at _dmarc.<domain>."""
    dmarc_domain = f"_dmarc.{domain}"
    records = doh_query(dmarc_domain, "TXT")
    dmarc_records = [r for r in records if r.startswith("v=DMARC1")]

    if not dmarc_records:
        return {
            "found": False,
            "raw": None,
            "policy": "none",
            "rua": None,
            "ruf": None,
            "pct": None,
            "issues": ["No DMARC record found at _dmarc." + domain + ". Domain is vulnerable to spoofing."]
        }

    raw_dmarc = dmarc_records[0]
    issues = []

    # Extract key DMARC tags
    tags = {}
    for part in raw_dmarc.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            tags[k.strip().lower()] = v.strip()

    policy = tags.get("p", "none").lower()
    rua = tags.get("rua", None)
    ruf = tags.get("ruf", None)
    pct = tags.get("pct", "100")

    if policy == "none":
        issues.append("DMARC policy is set to 'p=none' (Monitoring mode only). Spoofed emails are not blocked.")
    elif policy not in ["quarantine", "reject"]:
        issues.append(f"Invalid or unrecognized DMARC policy: {policy}")

    if not rua:
        issues.append("No aggregate report URI (rua) defined. You won't receive visibility on delivery reports.")

    return {
        "found": True,
        "raw": raw_dmarc,
        "policy": policy,
        "subdomain_policy": tags.get("sp", policy),
        "rua": rua,
        "ruf": ruf,
        "pct": pct,
        "aspf": tags.get("aspf", "r"),
        "adkim": tags.get("adkim", "r"),
        "issues": issues
    }


def analyze_dkim(domain: str) -> dict:
    """Scan common selector subdomains to discover active DKIM public keys."""
    discovered_keys = []
    for selector in COMMON_DKIM_SELECTORS:
        dkim_domain = f"{selector}._domainkey.{domain}"
        records = doh_query(dkim_domain, "TXT")
        for r in records:
            if "v=DKIM1" in r or "k=rsa" in r or "p=" in r:
                discovered_keys.append({
                    "selector": selector,
                    "record": r
                })

    return {
        "found": len(discovered_keys) > 0,
        "discovered_selectors_count": len(discovered_keys),
        "selectors": discovered_keys,
        "note": "Scanned 15 common DKIM selectors. Customized selectors might require targeted lookup."
    }


def compute_security_score(mx: dict, spf: dict, dmarc: dict, dkim: dict) -> tuple:
    """Compute overall email security score (0 - 100) and list recommendations."""
    score = 0
    recommendations = []

    # MX evaluation (15 pts)
    if mx["found"]:
        score += 15
    else:
        recommendations.append("Add MX records if this domain is intended to receive email.")

    # SPF evaluation (35 pts)
    if spf["found"]:
        score += 15
        if spf["strictness"] == "HardFail (-all)":
            score += 20
        elif spf["strictness"] == "SoftFail (~all)":
            score += 15
        elif spf["strictness"] == "Neutral (?all)":
            score += 5

        for issue in spf.get("issues", []):
            recommendations.append(f"SPF: {issue}")
    else:
        recommendations.append("Create a strong SPF record ending with '~all' or '-all'.")

    # DMARC evaluation (35 pts)
    if dmarc["found"]:
        score += 10
        if dmarc["policy"] == "reject":
            score += 25
        elif dmarc["policy"] == "quarantine":
            score += 20
        elif dmarc["policy"] == "none":
            score += 10

        for issue in dmarc.get("issues", []):
            recommendations.append(f"DMARC: {issue}")
    else:
        recommendations.append("Implement a DMARC policy record at '_dmarc." + dmarc.get("domain", "") + "' starting with 'p=none' then progressing to 'p=reject'.")

    # DKIM evaluation (15 pts)
    if dkim["found"]:
        score += 15
    else:
        recommendations.append("Ensure DKIM signatures are properly configured and key records published in DNS.")

    return min(100, max(0, score)), recommendations


def main():
    # 1. Input Resolution
    input_data = {}
    local_input_path = "./storage/key_value_stores/default/INPUT.json"

    if os.path.exists(local_input_path):
        try:
            with open(local_input_path, "r", encoding="utf-8") as f:
                input_data = json.load(f)
        except Exception:
            pass

    if not input_data and os.getenv("APIFY_INPUT_VALUE"):
        try:
            input_data = json.loads(os.getenv("APIFY_INPUT_VALUE"))
        except Exception:
            pass

    raw_domain = input_data.get("domain", "google.com") if isinstance(input_data, dict) else "google.com"
    target_domain = clean_domain(raw_domain)

    # 2. Perform Audit
    try:
        mx_res = analyze_mx(target_domain)
        spf_res = analyze_spf(target_domain)
        dmarc_res = analyze_dmarc(target_domain)
        dkim_res = analyze_dkim(target_domain)

        score, recommendations = compute_security_score(mx_res, spf_res, dmarc_res, dkim_res)

        audit_result = {
            "domain": target_domain,
            "security_score": score,
            "mx_records": mx_res,
            "spf_record": spf_res,
            "dmarc_record": dmarc_res,
            "dkim_audit": dkim_res,
            "recommendations": recommendations,
            "status": "SUCCESS"
        }
    except Exception as err:
        audit_result = {
            "domain": target_domain,
            "security_score": 0,
            "status": "ERROR",
            "error_message": str(err),
            "recommendations": ["Re-run the audit; DNS queries failed."]
        }

    # 3. Output & Dataset Storage
    dataset_dir = "./storage/datasets/default"
    os.makedirs(dataset_dir, exist_ok=True)
    local_file_path = os.path.join(dataset_dir, "000000001.json")

    with open(local_file_path, "w", encoding="utf-8") as f:
        json.dump(audit_result, f, indent=2, ensure_ascii=False)

    # Apify Cloud Dataset Sync if tokens present
    apify_token = os.getenv("APIFY_TOKEN")
    apify_dataset_id = os.getenv("APIFY_DEFAULT_DATASET_ID")

    if apify_token and apify_dataset_id:
        try:
            api_url = f"https://api.apify.com/v2/datasets/{apify_dataset_id}/items?token={apify_token}"
            requests.post(api_url, json=[audit_result], headers={"Content-Type": "application/json"}, timeout=10)
        except Exception:
            pass

    # Standard JSON log execution output
    output_log = {
        "APIFY_DATASET_COUNT": 1,
        "status": audit_result["status"],
        "domain": target_domain,
        "security_score": audit_result["security_score"]
    }
    print(json.dumps(output_log), flush=True)


if __name__ == "__main__":
    main()