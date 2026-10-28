import json
import os
import re
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, Comment

# Header HTTP standard et professionnel
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


def load_input() -> dict:
    """Charge la configuration depuis l'environnement local ou Apify."""
    default_input = {
        "startUrl": "https://fastapi.tiangolo.com",
        "maxDepth": 1,
        "maxPages": 10,
    }

    # 1. Fichier local Apify
    local_input_path = Path("./storage/key_value_stores/default/INPUT.json")
    if local_input_path.exists():
        try:
            with open(local_input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default_input, **data}
        except Exception:
            pass

    # 2. Variable d'environnement Apify
    env_input = os.getenv("APIFY_INPUT_VALUE")
    if env_input:
        try:
            data = json.loads(env_input)
            return {**default_input, **data}
        except Exception:
            pass

    # 3. Fallback par défaut
    return default_input


def clean_html_to_markdown(html_content: str, url: str) -> tuple[str, str, str]:
    """Extrait le titre et convertit le contenu HTML principal en Markdown propre."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Suppression des éléments parasites
    for element in soup(
        ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "form"]
    ):
        element.decompose()

    # Suppression des commentaires HTML
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Extraction du titre
    title = "Untitled Page"
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.h1:
        title = soup.h1.get_text(strip=True)

    # Conversion des blocs de code
    for pre in soup.find_all("pre"):
        code_text = pre.get_text()
        pre.replace_with(f"\n\n```\n{code_text.strip()}\n```\n\n")

    # Conversion des hyperliens
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        href = urljoin(url, a["href"])
        if link_text:
            a.replace_with(f" [{link_text}]({href}) ")

    # Conversion des titres (h1-h6)
    for i in range(1, 7):
        for h in soup.find_all(f"h{i}"):
            h_text = h.get_text(strip=True)
            h.replace_with(f"\n\n{'#' * i} {h_text}\n\n")

    # Conversion des éléments de liste
    for li in soup.find_all("li"):
        li_text = li.get_text(strip=True)
        li.replace_with(f"\n- {li_text}")

    # Récupération du texte nettoyé
    text = soup.get_text(separator="\n")

    # Formatage des espaces et lignes vides consécutives
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = []
    previous_empty = False

    for line in lines:
        if line:
            clean_lines.append(line)
            previous_empty = False
        elif not previous_empty:
            clean_lines.append("")
            previous_empty = True

    markdown_body = "\n".join(clean_lines).strip()
    summary = clean_lines[0] if clean_lines else "No summary available."
    if len(summary) > 200:
        summary = summary[:197] + "..."

    return title, markdown_body, summary


def save_dataset(records: list[dict]) -> None:
    """Sauvegarde les enregistrements localement et sur le dataset Apify si configuré."""
    # 1. Sauvegarde locale
    dataset_dir = Path("./storage/datasets/default")
    dataset_dir.mkdir(parents=True, exist_ok=True)

    for index, record in enumerate(records, start=1):
        filename = f"{index:09d}.json"
        file_path = dataset_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

    # Sauvegarde consolidée pour accès direct
    results_path = dataset_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # 2. Export direct vers l'API Apify si les clés d'environnement sont présentes
    apify_token = os.getenv("APIFY_TOKEN")
    dataset_id = os.getenv("APIFY_DEFAULT_DATASET_ID")

    if apify_token and dataset_id:
        url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_token}"
        try:
            requests.post(url, json=records, timeout=30)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to push to Apify API: {e}\n")

    # 3. Log structuré obligatoire sur sys.stdout
    log_payload = {
        "APIFY_DATASET_COUNT": len(records),
        "status": "COMPLETED",
        "local_storage_path": str(dataset_dir.resolve()),
    }
    print(json.dumps(log_payload), flush=True)


def extract_internal_links(soup: BeautifulSoup, current_url: str, base_domain: str) -> set[str]:
    """Extrait tous les liens internes appartenant au même domaine."""
    links = set()
    for a in soup.find_all("a", href=True):
        raw_href = a["href"].split("#")[0].strip()
        if not raw_href:
            continue
        full_url = urljoin(current_url, raw_href)
        parsed = urlparse(full_url)
        if parsed.netloc == base_domain and parsed.scheme in ["http", "https"]:
            links.add(full_url)
    return links


def main():
    config = load_input()
    start_url = config.get("startUrl", "https://fastapi.tiangolo.com")
    max_depth = int(config.get("maxDepth", 1))
    max_pages = int(config.get("maxPages", 10))

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    queue = deque([(start_url, 0)])
    visited = set([start_url])
    records = []
    llms_txt_entries = []

    try:
        while queue and len(records) < max_pages:
            current_url, depth = queue.popleft()

            try:
                response = requests.get(current_url, headers=HEADERS, timeout=15)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    continue

                html = response.text
                soup = BeautifulSoup(html, "html.parser")
                title, markdown_content, summary = clean_html_to_markdown(html, current_url)

                record = {
                    "url": current_url,
                    "title": title,
                    "depth": depth,
                    "summary": summary,
                    "markdown": markdown_content,
                    "char_count": len(markdown_content),
                    "status_code": response.status_code,
                    "error": None,
                }
                records.append(record)
                llms_txt_entries.append(f"- [{title}]({current_url}): {summary}")

                # Crawl des liens suivants si profondeur autorisée
                if depth < max_depth:
                    internal_links = extract_internal_links(soup, current_url, base_domain)
                    for link in internal_links:
                        if link not in visited:
                            visited.add(link)
                            queue.append((link, depth + 1))

            except Exception as req_err:
                # Capture d'erreur robuste par page sans interrompre l'Actor
                error_record = {
                    "url": current_url,
                    "title": "Error Processing Page",
                    "depth": depth,
                    "summary": f"Failed to retrieve or process page: {str(req_err)}",
                    "markdown": f"# Error\n\nCould not scrape `{current_url}`.\nDetails: {str(req_err)}",
                    "char_count": 0,
                    "status_code": getattr(getattr(req_err, "response", None), "status_code", 500),
                    "error": str(req_err),
                }
                records.append(error_record)

    except Exception as fatal_err:
        # Fallback de secours absolu pour garantir au moins 1 enregistrement
        if not records:
            records.append(
                {
                    "url": start_url,
                    "title": "Fatal Execution Error",
                    "depth": 0,
                    "summary": f"Actor execution failed: {str(fatal_err)}",
                    "markdown": f"# Fatal Error\n\n{str(fatal_err)}",
                    "char_count": 0,
                    "status_code": 500,
                    "error": str(fatal_err),
                }
            )

    # Génération du fichier llms.txt consolidé dans le premier enregistrement si disponible
    if records:
        domain_name = base_domain or "Website"
        llms_txt_header = f"# {domain_name}\n\n> Auto-generated llms.txt for LLM/RAG ingestion.\n\n## Documentation Pages\n\n"
        llms_txt_content = llms_txt_header + "\n".join(llms_txt_entries)

        # Ajout d'une entrée spéciale avec la structure llms.txt globale
        records.append(
            {
                "url": start_url,
                "title": f"llms.txt Summary for {domain_name}",
                "depth": 0,
                "summary": f"Aggregated llms.txt file containing {len(llms_txt_entries)} indexed pages.",
                "markdown": llms_txt_content,
                "char_count": len(llms_txt_content),
                "is_llms_txt_file": True,
                "status_code": 200,
                "error": None,
            }
        )

    save_dataset(records)


if __name__ == "__main__":
    main()