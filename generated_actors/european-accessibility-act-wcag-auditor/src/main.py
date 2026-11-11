import os
import re
import sys
import json
import math
from pathlib import Path
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def load_input() -> dict:
    """Loads input from Apify local storage, environment variable, or defaults."""
    default_input = {
        "targetUrl": "https://news.ycombinator.com",
        "checkAria": True,
        "checkContrast": True
    }

    input_file = Path("./storage/key_value_stores/default/INPUT.json")
    if input_file.exists():
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**default_input, **data}
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to parse input file: {e}\n")

    env_input = os.getenv("APIFY_INPUT_VALUE")
    if env_input:
        try:
            data = json.loads(env_input)
            if isinstance(data, dict):
                return {**default_input, **data}
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to parse APIFY_INPUT_VALUE: {e}\n")

    return default_input

def parse_color(color_str: str):
    """Parses hex or rgb color strings into (r, g, b) tuple in range [0, 255]."""
    color_str = color_str.strip().lower()
    
    # Hex format #fff or #ffffff
    hex_match = re.match(r'^#([0-9a-f]{3}|[0-9a-f]{6})$', color_str)
    if hex_match:
        val = hex_match.group(1)
        if len(val) == 3:
            return tuple(int(c * 2, 16) for c in val)
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
    
    # RGB format rgb(r, g, b)
    rgb_match = re.match(r'^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$', color_str)
    if rgb_match:
        return tuple(min(255, max(0, int(c))) for c in rgb_match.groups())

    return None

def get_relative_luminance(rgb) -> float:
    """Calculates relative luminance for WCAG contrast ratio."""
    def adjust(c):
        c_norm = c / 255.0
        return c_norm / 12.92 if c_norm <= 0.04045 else ((c_norm + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def calculate_contrast_ratio(color1, color2) -> float:
    """Calculates WCAG 2.1 contrast ratio between two colors."""
    lum1 = get_relative_luminance(color1)
    lum2 = get_relative_luminance(color2)
    l1 = max(lum1, lum2)
    l2 = min(lum1, lum2)
    return round((l1 + 0.05) / (l2 + 0.05), 2)

def audit_document(soup: BeautifulSoup, check_aria: bool, check_contrast: bool) -> dict:
    """Executes WCAG 2.1 AA audits on the parsed HTML document."""
    violations = []
    passes = []
    
    # 1. Document Title (WCAG 2.4.2 Page Titled)
    title_tag = soup.find('title')
    if title_tag and title_tag.get_text(strip=True):
        passes.append({"rule": "WCAG 2.4.2 Page Titled", "message": "Document has a non-empty <title> element."})
    else:
        violations.append({"rule": "WCAG 2.4.2 Page Titled", "impact": "serious", "message": "Document lacks a valid or non-empty <title> tag."})

    # 2. Language Attribute (WCAG 3.1.1 Language of Page)
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        passes.append({"rule": "WCAG 3.1.1 Language of Page", "message": f"Document has 'lang' attribute set to '{html_tag['lang']}'."})
    else:
        violations.append({"rule": "WCAG 3.1.1 Language of Page", "impact": "critical", "message": "<html> element missing 'lang' attribute."})

    # 3. Image Alt Text (WCAG 1.1.1 Non-text Content)
    images = soup.find_all('img')
    missing_alt_count = 0
    for img in images:
        if not img.has_attr('alt'):
            missing_alt_count += 1

    if missing_alt_count == 0:
        passes.append({"rule": "WCAG 1.1.1 Non-text Content", "message": f"All {len(images)} image(s) have 'alt' attributes."})
    else:
        violations.append({"rule": "WCAG 1.1.1 Non-text Content", "impact": "critical", "message": f"Found {missing_alt_count} image(s) missing an 'alt' attribute."})

    # 4. Heading Structure (WCAG 1.3.1 Info and Relationships)
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    h1_count = len(soup.find_all('h1'))
    
    if h1_count == 1:
        passes.append({"rule": "WCAG 1.3.1 Info and Relationships", "message": "Document contains exactly one <h1> heading."})
    elif h1_count == 0:
        violations.append({"rule": "WCAG 1.3.1 Info and Relationships", "impact": "moderate", "message": "Document has no <h1> heading."})
    else:
        violations.append({"rule": "WCAG 1.3.1 Info and Relationships", "impact": "moderate", "message": f"Document contains multiple ({h1_count}) <h1> headings."})

    last_level = 0
    skipped_levels = 0
    for h in headings:
        level = int(h.name[1])
        if last_level > 0 and level > last_level + 1:
            skipped_levels += 1
        last_level = level

    if skipped_levels > 0:
        violations.append({"rule": "WCAG 1.3.1 Heading Hierarchy", "impact": "moderate", "message": f"Detected {skipped_levels} skipped heading level(s) (e.g. h1 to h3)."})
    else:
        passes.append({"rule": "WCAG 1.3.1 Heading Hierarchy", "message": "Heading levels follow a sequential logical structure."})

    # 5. Form Controls and Labels (WCAG 1.3.1 / 4.1.2)
    inputs = soup.find_all(['input', 'select', 'textarea'])
    unlabeled_inputs = 0
    for inp in inputs:
        inp_type = inp.get('type', '').lower()
        if inp_type in ['hidden', 'submit', 'button', 'image', 'reset']:
            continue
        
        inp_id = inp.get('id')
        has_label = False
        if inp_id and soup.find('label', attrs={'for': inp_id}):
            has_label = True
        elif inp.find_parent('label'):
            has_label = True
        elif inp.get('aria-label') or inp.get('aria-labelledby') or inp.get('title'):
            has_label = True

        if not has_label:
            unlabeled_inputs += 1

    if unlabeled_inputs == 0:
        passes.append({"rule": "WCAG 4.1.2 Name, Role, Value", "message": "All form controls have associated accessible labels."})
    else:
        violations.append({"rule": "WCAG 4.1.2 Name, Role, Value", "impact": "critical", "message": f"Found {unlabeled_inputs} form control(s) missing accessible labels."})

    # 6. ARIA Audits (Optional checkAria)
    if check_aria:
        all_elements = soup.find_all(True)
        aria_errors = 0
        all_ids = set(el.get('id') for el in all_elements if el.get('id'))

        for el in all_elements:
            if el.has_attr('aria-labelledby'):
                target_ids = el['aria-labelledby'].split()
                for target_id in target_ids:
                    if target_id not in all_ids:
                        aria_errors += 1
            if el.has_attr('aria-hidden') and el['aria-hidden'].lower() == 'true':
                if el.name in ['a', 'button', 'input', 'select', 'textarea'] and el.get('tabindex') != '-1':
                    aria_errors += 1

        if aria_errors == 0:
            passes.append({"rule": "WCAG 4.1.2 ARIA Attributes", "message": "ARIA attributes and element references are valid."})
        else:
            violations.append({"rule": "WCAG 4.1.2 ARIA Attributes", "impact": "serious", "message": f"Found {aria_errors} invalid ARIA attribute reference(s) or hidden focusable element(s)."})

    # 7. Contrast Checks (Optional checkContrast - Inline style inspection)
    if check_contrast:
        elements_with_style = soup.find_all(style=True)
        contrast_violations = 0
        evaluated_count = 0

        for el in elements_with_style:
            style_str = el['style']
            color_match = re.search(r'(?:^|;\s*)color\s*:\s*([^;]+)', style_str, re.IGNORECASE)
            bg_match = re.search(r'(?:^|;\s*)background-color\s*:\s*([^;]+)', style_str, re.IGNORECASE)

            if color_match and bg_match:
                fg_color = parse_color(color_match.group(1))
                bg_color = parse_color(bg_match.group(1))

                if fg_color and bg_color:
                    evaluated_count += 1
                    ratio = calculate_contrast_ratio(fg_color, bg_color)
                    if ratio < 4.5:
                        contrast_violations += 1

        if contrast_violations > 0:
            violations.append({"rule": "WCAG 1.4.3 Contrast (Minimum)", "impact": "serious", "message": f"Found {contrast_violations} inline styled element(s) with contrast ratio below 4.5:1."})
        else:
            passes.append({"rule": "WCAG 1.4.3 Contrast (Minimum)", "message": f"Evaluated inline color pairs ({evaluated_count} verified) meet minimum contrast thresholds."})

    total_rules = len(passes) + len(violations)
    score = round((len(passes) / total_rules * 100), 2) if total_rules > 0 else 100.0

    return {
        "score_percentage": score,
        "total_checks": total_rules,
        "passed_checks": len(passes),
        "failed_checks": len(violations),
        "violations": violations,
        "passes": passes
    }

def save_results(results: list):
    """Saves output results locally and sends to Apify API dataset if credentials exist."""
    dataset_dir = Path("./storage/datasets/default")
    dataset_dir.mkdir(parents=True, exist_ok=True)

    for idx, item in enumerate(results, start=1):
        file_path = dataset_dir / f"{idx:09d}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

    with open(dataset_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    token = os.getenv("APIFY_TOKEN")
    dataset_id = os.getenv("APIFY_DEFAULT_DATASET_ID")

    if token and dataset_id:
        endpoint = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={token}"
        try:
            response = requests.post(
                endpoint,
                json=results,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to push dataset to Apify API: {e}\n")

    print(json.dumps({"APIFY_DATASET_COUNT": len(results)}))

def main():
    config = load_input()
    target_url = config.get("targetUrl", "https://news.ycombinator.com")
    check_aria = config.get("checkAria", True)
    check_contrast = config.get("checkContrast", True)

    headers = {"User-Agent": USER_AGENT}
    dataset_record = {
        "targetUrl": target_url,
        "status": "success",
        "error": None,
        "compliance_standard": "European Accessibility Act (EAA) / WCAG 2.1 AA",
        "audit_results": {}
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=20)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        audit_outcomes = audit_document(soup, check_aria, check_contrast)
        dataset_record["audit_results"] = audit_outcomes

    except Exception as e:
        dataset_record["status"] = "failed"
        dataset_record["error"] = str(e)
        dataset_record["audit_results"] = {
            "score_percentage": 0.0,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "violations": [{"rule": "HTTP / Network Request", "impact": "critical", "message": f"Unable to reach target URL: {str(e)}"}],
            "passes": []
        }

    save_results([dataset_record])

if __name__ == "__main__":
    main()