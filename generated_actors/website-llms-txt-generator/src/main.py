import os
import sys
import json
import time
import re
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_INPUT = {
    "startUrl": "https://fastapi.tiangolo.com",
    "maxDepth": 1,
    "maxPages": 10
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 ApifyWebsiteToLlmsTxt/1.0"
)

def load_input() -> dict:
    env_input = os.environ.get("APIFY_INPUT_VALUE")
    if env_input:
        try:
            parsed = json.loads(env_input)
            if isinstance(parsed, dict):
                return {**DEFAULT_INPUT, **parsed}
        except Exception:
            pass

    input_path = os.path.join(".", "storage", "key_value_stores", "default", "INPUT.json")
    if os.path.exists(input_path):
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                parsed = json.load(f)
                if isinstance(parsed, dict):
                    return {**DEFAULT_INPUT, **parsed}
        except Exception:
            pass

    return DEFAULT_INPUT.copy()

def html_to_markdown(soup_node) -> str:
    if soup_node is None:
        return ""

    for tag in soup_node.find_all(["script", "style", "noscript", "svg", "canvas", "iframe"]):
        tag.decompose()

    def process_node(node) -> str:
        if isinstance(node, NavigableString):
            text = str(node)
            return re.sub(r"[ \t]+", " ", text)
        if not isinstance(node, Tag):
            return ""

        tag_name = node.name.lower()

        if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag_name[1])
            inner = "".join(process_node(child) for child in node.children).strip()
            return f"\n\n{'#' * level} {inner}\n\n" if inner else ""

        if tag_name == "p":
            inner = "".join(process_node(child) for child in node.children).strip()
            return f"\n\n{inner}\n\n" if inner else ""

        if tag_name == "br":
            return "\n"

        if tag_name == "hr":
            return "\n\n---\n\n"

        if tag_name in ["strong", "b"]:
            inner = "".join(process_node(child) for child in node.children).strip()
            return f"**{inner}**" if inner else ""

        if tag_name in ["em", "i"]:
            inner = "".join(process_node(child) for child in node.children).strip()
            return f"*{inner}*" if inner else ""

        if tag_name == "code":
            if node.parent and node.parent.name.lower() == "pre":
                return node.get_text()
            inner = node.get_text().strip()
            return f"`{inner}`" if inner else ""

        if tag_name == "pre":
            code = node.get_text()
            return f"\n\n```\n{code.strip()}\n```\n\n"

        if tag_name == "blockquote":
            inner = "".join(process_node(child) for child in node.children).strip()
            lines = inner.split("\n")
            quoted = "\n".join(f"> {line}" for line in lines)
            return f"\n\n{quoted}\n\n"

        if tag_name in ["ul", "ol"]:
            items = []
            is_ol = tag_name == "ol"
            idx = 1
            for child in node.children:
                if isinstance(child, Tag) and child.name.lower() == "li":
                    item_text = "".join(process_node(c) for c in child.children).strip()
                    if item_text:
                        prefix = f"{idx}. " if is_ol else "- "
                        items.append(f"{prefix}{item_text}")
                        idx += 1
            return "\n\n" + "\n".join(items) + "\n\n"

        if tag_name == "a":
            inner = "".join(process_node(child) for child in node.children).strip()
            href = node.get("href", "").strip()
            if href and inner:
                return f"[{inner}]({href})"
            return inner

        if tag_name in ["div", "section", "article", "main"]:
            inner = "".join(process_node(child) for child in node.children)
            return f"\n{inner}\n"

        return "".join(process_node(child) for child in node.children)

    raw_md = process_node(soup_node)
    cleaned = re.sub(r"\n{3,}", "\n\n", raw_md)
    return cleaned.strip()

def normalize_url(url: str) -> str:
    clean_url, _ = urldefrag(url)
    clean_url = clean_url.rstrip("/")
    return clean_url

def is_same_domain(base_netloc: str, target_url: str) -> bool:
    try:
        parsed = urlparse(target_url)
        return parsed.netloc.lower() == base_netloc.lower()
    except Exception:
        return False

def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def save_dataset_items(items: list):
    output_dir = os.path.join(".", "storage", "datasets", "default")
    os.makedirs(output_dir, exist_ok=True)

    for index, item in enumerate(items, start=1):
        filename = f"{index:09d}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

    consolidated_path = os.path.join(output_dir, "results.json")
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    apify_token = os.environ.get("APIFY_TOKEN")
    apify_dataset_id = os.environ.get("APIFY_DEFAULT_DATASET_ID")
    if apify_token and apify_dataset_id:
        url = f"https://api.apify.com/v2/datasets/{apify_dataset_id}/items"
        headers = {
            "Authorization": f"Bearer {apify_token}",
            "Content-Type": "application/json"
        }
        try:
            requests.post(url, json=items, headers=headers, timeout=30)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to upload to Apify Dataset API: {str(e)}\n")

    sys.stdout.write(json.dumps({"APIFY_DATASET_COUNT": len(items)}) + "\n")
    sys.stdout.flush()

def crawl_and_extract(start_url: str, max_depth: int, max_pages: int) -> list:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    base_parsed = urlparse(start_url)
    base_netloc = base_parsed.netloc

    queue = deque([(normalize_url(start_url), 0)])
    visited = set()
    pages_data = []

    while queue and len(pages_data) < max_pages:
        current_url, current_depth = queue.popleft()

        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            response = session.get(current_url, timeout=15, allow_redirects=True)
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            title_tag = soup.find("title")
            title = title_tag.get_text().strip() if title_tag else current_url

            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()
            elif not meta_desc:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    meta_desc = og_desc["content"].strip()

            content_container = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", attrs={"role": "main"})
                or soup.find("div", class_=re.compile(r"content|documentation|docs|body", re.I))
                or soup.body
            )

            markdown = html_to_markdown(content_container if content_container else soup)
            first_h1 = soup.find("h1")
            h1_text = first_h1.get_text().strip() if first_h1 else title

            pages_data.append({
                "url": current_url,
                "title": title,
                "h1": h1_text,
                "description": meta_desc,
                "depth": current_depth,
                "statusCode": response.status_code,
                "markdown": markdown,
                "length": len(markdown)
            })

            if current_depth < max_depth and len(pages_data) < max_pages:
                for link in soup.find_all("a", href=True):
                    href = link["href"].strip()
                    abs_url = normalize_url(urljoin(current_url, href))
                    if (
                        is_valid_http_url(abs_url)
                        and is_same_domain(base_netloc, abs_url)
                        and abs_url not in visited
                    ):
                        file_ext = os.path.splitext(urlparse(abs_url).path)[1].lower()
                        if file_ext not in [".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz", ".exe", ".css", ".js"]:
                            queue.append((abs_url, current_depth + 1))

        except requests.RequestException as e:
            if not pages_data:
                pages_data.append({
                    "url": current_url,
                    "title": "Crawl Error",
                    "h1": "Request Failed",
                    "description": f"Failed to fetch {current_url}: {str(e)}",
                    "depth": current_depth,
                    "statusCode": getattr(e.response, "status_code", 0) if hasattr(e, "response") and e.response else 500,
                    "markdown": f"Network error during retrieval: {str(e)}",
                    "length": 0
                })
            continue

    return pages_data

def generate_llms_txt(site_name: str, site_summary: str, pages: list) -> str:
    lines = [
        f"# {site_name}",
        "",
        f"> {site_summary}" if site_summary else f"> Documentation and content corpus for {site_name}.",
        "",
        "## Core Documentation",
        ""
    ]
    for page in pages:
        title = page.get("h1") or page.get("title") or page.get("url")
        desc = page.get("description")
        desc_suffix = f": {desc}" if desc else ""
        lines.append(f"- [{title}]({page['url']}){desc_suffix}")
    return "\n".join(lines).strip()

def generate_llms_full_txt(site_name: str, pages: list) -> str:
    blocks = [
        f"# Full Documentation Corpus: {site_name}",
        f"Generated on {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "================================================================================"
    ]
    for page in pages:
        blocks.append(f"\n\n# Document: {page.get('title')}\nURL: {page.get('url')}\n\n{page.get('markdown')}\n\n---")
    return "\n".join(blocks).strip()

def main():
    config = load_input()
    start_url = config.get("startUrl", DEFAULT_INPUT["startUrl"]).strip()
    if not is_valid_http_url(start_url):
        start_url = DEFAULT_INPUT["startUrl"]

    try:
        max_depth = int(config.get("maxDepth", DEFAULT_INPUT["maxDepth"]))
    except (ValueError, TypeError):
        max_depth = DEFAULT_INPUT["maxDepth"]

    try:
        max_pages = int(config.get("maxPages", DEFAULT_INPUT["maxPages"]))
    except (ValueError, TypeError):
        max_pages = DEFAULT_INPUT["maxPages"]

    pages = crawl_and_extract(start_url, max_depth, max_pages)

    if not pages:
        pages.append({
            "url": start_url,
            "title": "Execution Completed",
            "h1": "No Pages Extracted",
            "description": "Crawler encountered no valid or reachable HTML documents.",
            "depth": 0,
            "statusCode": 404,
            "markdown": "No content could be extracted from the provided startUrl.",
            "length": 0
        })

    root_page = pages[0]
    site_title = root_page.get("h1") or root_page.get("title") or urlparse(start_url).netloc
    site_desc = root_page.get("description") or f"Knowledge base parsed from {start_url}"

    llms_txt = generate_llms_txt(site_title, site_desc, pages)
    llms_full_txt = generate_llms_full_txt(site_title, pages)

    dataset_records = []

    dataset_records.append({
        "type": "llms_txt",
        "url": start_url,
        "filename": "llms.txt",
        "content": llms_txt,
        "totalPages": len(pages),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })

    dataset_records.append({
        "type": "llms_full_txt",
        "url": start_url,
        "filename": "llms-full.txt",
        "content": llms_full_txt,
        "totalPages": len(pages),
        "totalCharacters": len(llms_full_txt),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })

    for page in pages:
        dataset_records.append({
            "type": "page_markdown",
            "url": page["url"],
            "title": page["title"],
            "description": page["description"],
            "depth": page["depth"],
            "statusCode": page["statusCode"],
            "markdown": page["markdown"],
            "length": page["length"]
        })

    save_dataset_items(dataset_records)

if __name__ == "__main__":
    main()