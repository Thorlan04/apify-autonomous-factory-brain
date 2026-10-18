"""
Module ActorCodeGenerator - Générateur de code d'Actors Apify par IA.

Utilise Gemini 2.5 Flash pour générer une architecture complète, propre et sans placeholder
pour un nouvel Actor Apify dans 'generated_actors/<actor_slug>/'.
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.brain_ideator import ActorIdea

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger("ActorCodeGenerator")


class ActorCodeGenerator:
    """Générateur de code automatisé pour Actors Apify."""

    def __init__(self, output_root: Optional[Path] = None):
        if output_root is None:
            self.output_root = Path(__file__).resolve().parent.parent / "generated_actors"
        else:
            self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _call_gemini(self, prompt: str) -> str:
        """Appelle Gemini 2.5 Flash via google-genai ou fallback REST."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY manquant. Impossible de générer le code de l'Actor.")

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Appel google-genai a échoué ({e}). Utilisation du fallback REST...")

        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        candidates = res.json().get("candidates", [])
        if not candidates:
            raise ValueError("Réponse Gemini vide reçue lors de la génération de code.")
        return candidates[0]["content"]["parts"][0]["text"]

    def generate_actor_files(self, idea: ActorIdea) -> Path:
        """
        Génère l'ensemble des fichiers de l'Actor dans un sous-dossier dédié.
        Retourne le chemin absolu du dossier de l'Actor.
        """
        actor_dir = self.output_root / idea.slug
        actor_dir.mkdir(parents=True, exist_ok=True)
        (actor_dir / ".actor").mkdir(parents=True, exist_ok=True)
        (actor_dir / "src").mkdir(parents=True, exist_ok=True)

        logger.info(f"Génération de l'Actor '{idea.name}' ({idea.slug}) dans {actor_dir}...")

        # 1. Génération de .actor/actor.json
        actor_json = {
            "actorSpecification": 1,
            "name": idea.slug,
            "title": idea.name,
            "description": idea.description,
            "version": "0.1",
            "dockerfile": "./Dockerfile",
            "restartOnError": False,
            "input": "./input_schema.json",
            "output": "./output_schema.json",
            "storages": {
                "dataset": "./dataset_schema.json"
            },
            "meta": {
                "categories": [idea.category.upper().replace("-", "_")]
            }
        }
        with open(actor_dir / ".actor" / "actor.json", "w", encoding="utf-8") as f:
            json.dump(actor_json, f, indent=2, ensure_ascii=False)

        # 2. Génération de .actor/input_schema.json
        input_schema = self._generate_input_schema(idea)
        with open(actor_dir / ".actor" / "input_schema.json", "w", encoding="utf-8") as f:
            json.dump(input_schema, f, indent=2, ensure_ascii=False)

        # 3. Génération de .actor/output_schema.json (Requis par l'Apify Store)
        output_schema = {
            "actorOutputSchemaVersion": 1,
            "title": f"Output Schema for {idea.name}",
            "description": "Defines the output produced by the Actor.",
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "title": "Scraped Results Dataset",
                    "description": "Dataset containing all items collected by the Actor.",
                    "template": "{{links.defaultDatasetId}}"
                }
            }
        }
        with open(actor_dir / ".actor" / "output_schema.json", "w", encoding="utf-8") as f:
            json.dump(output_schema, f, indent=2, ensure_ascii=False)

        # 4. Génération de .actor/dataset_schema.json
        dataset_schema = {
            "actorSpecification": 1,
            "fields": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "title": "Item ID"
                    },
                    "title": {
                        "type": "string",
                        "title": "Item Title"
                    },
                    "data": {
                        "type": "object",
                        "title": "Structured Data"
                    }
                },
                "additionalProperties": True
            },
            "views": {
                "overview": {
                    "title": "Overview",
                    "transformation": {
                        "fields": ["title", "id", "data"]
                    }
                }
            }
        }
        with open(actor_dir / ".actor" / "dataset_schema.json", "w", encoding="utf-8") as f:
            json.dump(dataset_schema, f, indent=2, ensure_ascii=False)

        # 4. Génération du Dockerfile
        dockerfile_content = """# Dockerfile standard Apify Python optimisé
FROM python:3.11-slim

# Configuration d'environnement Python
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1

WORKDIR /usr/src/app

# Installation des dépendances
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . ./

# Commande d'exécution officielle Apify
CMD ["python3", "-m", "src.main"]
"""
        with open(actor_dir / "Dockerfile", "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        # 5. Génération du requirements.txt de l'Actor
        actor_reqs = "requests>=2.31.0\nbeautifulsoup4>=4.12.3\npydantic>=2.7.0\n"
        with open(actor_dir / "requirements.txt", "w", encoding="utf-8") as f:
            f.write(actor_reqs)

        # 6. Génération de src/main.py via Gemini
        main_py_code = self._generate_main_py_code(idea, input_schema)
        with open(actor_dir / "src" / "main.py", "w", encoding="utf-8") as f:
            f.write(main_py_code)

        # 7. Génération du README.md pour Apify Store (SEO & Monétisation)
        readme_content = self._generate_store_readme(idea)
        with open(actor_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

        logger.info(f"Fichiers générés avec succès pour '{idea.slug}'.")
        return actor_dir

    def _generate_input_schema(self, idea: ActorIdea) -> Dict[str, Any]:
        """Génère un schéma d'entrée Apify valide avec les valeurs par défaut."""
        properties = {}
        required = []

        for key, val in idea.default_input.items():
            required.append(key)
            if isinstance(val, bool):
                prop_type = "boolean"
            elif isinstance(val, int):
                prop_type = "integer"
            elif isinstance(val, float):
                prop_type = "number"
            elif isinstance(val, list):
                prop_type = "array"
            else:
                prop_type = "string"

            properties[key] = {
                "title": key.replace("_", " ").title(),
                "type": prop_type,
                "description": f"Paramètre d'entrée : {key}",
                "default": val,
                "prefill": val
            }

        return {
            "title": f"Input Schema for {idea.name}",
            "type": "object",
            "schemaVersion": 1,
            "properties": properties,
            "required": required
        }

    def _generate_main_py_code(self, idea: ActorIdea, input_schema: Dict[str, Any]) -> str:
        """Fait rédiger le script d'exécution Python complet et résilient par Gemini."""
        prompt = f"""
Tu es l'Ingénieur en Chef Python spécialisé dans les Actors Apify déterministes et ultra-fiables.
Écris le code COMPLET, FONCTIONNEL et ROBUSTE du fichier `src/main.py` pour cet Actor :

Nom: {idea.name}
Slug: {idea.slug}
Catégorie: {idea.category}
Protocole: {idea.protocol}
Description: {idea.description}
Schéma d'Entrée & Valeurs par défaut: {json.dumps(idea.default_input, indent=2)}

RÈGLES D'OR TECHNIQUES D'EXÉCUTION :
1. AUCUN PLACEHOLDER, AUCUN TODO, AUCUN 'pass'. Le code doit fonctionner immédiatement et produire des données réelles.
2. Gestion de l'input :
   - Doit tenter de charger l'entrée depuis `./storage/key_value_stores/default/INPUT.json` ou depuis la variable d'environnement `APIFY_INPUT_VALUE`.
   - Si absent, utiliser IMMÉDIATEMENT le dictionnaire des valeurs par défaut : {json.dumps(idea.default_input)}.
3. Sauvegarde des résultats (Apify Dataset & Local) :
   - Écrire chaque enregistrement dans le dataset local : créer le dossier `./storage/datasets/default/` et sauvegarder les items sous forme de fichiers JSON indexés (`000000001.json`, etc.) OU un fichier consolidé `results.json`.
   - Si les variables d'environnement `APIFY_TOKEN` et `APIFY_DEFAULT_DATASET_ID` sont définies, faire un POST HTTP vers `https://api.apify.com/v2/datasets/<APIFY_DEFAULT_DATASET_ID>/items`.
   - Afficher au moins un log JSON clair sur `sys.stdout` contenant la clé `APIFY_DATASET_COUNT` indiquant le nombre d'éléments enregistrés.
4. Règle Zéro-Proxy : Utiliser la bibliothèque `requests` standard avec un User-Agent professionnel légitime. Si BeautifulSoup est nécessaire, l'utiliser proprement.
5. Gestion des exceptions : Capturer les erreurs réseau proprement avec un fallback ou un enregistrement d'erreur structuré afin que l'Actor produise TOUJOURS au moins 1 enregistrement dans le dataset même si la cible externe répond une erreur HTTP.
6. Ne renvoie QUE le code Python pur, sans explications bavardes, à l'intérieur d'un bloc ```python ... ```.
"""

        raw_response = self._call_gemini(prompt)
        code_match = re.search(r"```python(.*?)```", raw_response, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            code = raw_response.strip()

        # Nettoyage si markdown résiduel
        code = re.sub(r"^```.*\n", "", code)
        code = re.sub(r"\n```$", "", code)
        return code

    def _generate_store_readme(self, idea: ActorIdea) -> str:
        """Génère un README orienté SEO et conversion pour l'Apify Store."""
        return f"""# {idea.name}

> High-performance, zero-proxy, deterministic B2B micro-actor designed for Make.com, n8n, Zapier, and autonomous AI Agents.

[![Apify Actor](https://apify.com/actor-badge?actor={idea.slug})](https://apify.com/)
[![Protocol](https://img.shields.io/badge/Protocol-{idea.protocol.replace(' ', '%20')}-blue.svg)](#)
[![Zero Proxy Required](https://img.shields.io/badge/Proxy-Zero%20Proxy%20Required-success.svg)](#)

---

## ⚡ What is {idea.name}?

**{idea.name}** is an enterprise-grade automated tool engineered to {idea.description.lower()}.

Unlike fragile web scrapers that break upon layout changes or require expensive residential proxies, this Actor leverages standard, open protocols ({idea.protocol}) to deliver **100% deterministic, high-speed results** at the lowest possible computing cost.

### 🎯 Ideal For:
- **Automation Builders**: Seamlessly plug into **Make.com**, **n8n**, **Zapier**, and custom webhooks.
- **AI Agent Engineers**: Feed fresh, verified structured data directly to LLMs (Claude, OpenAI, Gemini) and RAG pipelines.
- **B2B Professionals**: {idea.target_users}.

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
{self._format_inputs_table(idea.default_input)}

---

## 📤 Sample Output

```json
[
  {{
    "scrapedAt": "2026-10-18T08:00:00Z",
    "status": "SUCCESS",
    "protocol": "{idea.protocol}",
    "data": {{
      "exampleKey": "exampleValue"
    }}
  }}
]
```

---

## 🔗 Integration Examples

### Make.com / n8n
1. Add an **Apify** node to your workflow.
2. Select **Run Actor** and choose `{idea.slug}`.
3. Map the output dataset to your downstream CRM, Slack, Notion, or PostgreSQL database.

### Python / cURL
```bash
curl "https://api.apify.com/v2/acts/{idea.slug}/runs?token=$APIFY_API_TOKEN" \\
  -X POST \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(idea.default_input)}'
```

---

## 💼 Pricing & Support

- **Rental Model**: ${idea.pricing_suggestion_usd:.0f}/month with unlimited runs under platform fair-use.
- **SLA & Maintenance**: Monitored and verified automatically.
- **Custom Integrations**: Open an issue or contact support via Apify Console.
"""

    def _format_inputs_table(self, default_inputs: Dict[str, Any]) -> str:
        """Génère la table Markdown des entrées."""
        rows = []
        for k, v in default_inputs.items():
            t = type(v).__name__
            rows.append(f"| `{k}` | `{t}` | `{v}` | Input argument for `{k}` |")
        return "\n".join(rows) if rows else "| `input` | `object` | `{}` | Standard configuration object |"
