"""
Module BrainIdeator - Cerveau d'idéation de l'Usine à Robots Apify.

Sélectionne ou conçoit de nouveaux Actors B2B conformes à la règle absolue :
'Zéro-Proxy Payant / Zéro Fragilité / Déterministe / 100% Protocoles Ouverts'.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger("BrainIdeator")

FORBIDDEN_KEYWORDS = [
    "instagram",
    "tiktok",
    "linkedin",
    "facebook",
    "twitter",
    "x.com",
    "recaptcha",
    "turnstile",
    "cloudflare-bypass",
    "residential-proxy",
    "puppeteer-stealth",
]

ALLOWED_CATEGORIES = [
    "ai-llm-data-prep",
    "e-commerce",
    "european-compliance",
    "infrastructure-security",
    "recruitment-ats",
    "b2b-intelligence",
    "seo-tech",
]


class ActorIdea(BaseModel):
    """Modèle représentant une idée qualifiée d'Actor Apify B2B."""
    id: str
    slug: str
    name: str
    category: str
    protocol: str
    description: str
    target_users: str
    default_input: Dict[str, Any] = Field(default_factory=dict)
    pricing_suggestion_usd: float = 19.0
    status: str = "pending"


class BrainIdeator:
    """Moteur d'idéation et de sélection de micro-services B2B pour Apify."""

    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            self.registry_path = Path(__file__).resolve().parent.parent / "data" / "factory_registry.json"
        else:
            self.registry_path = Path(registry_path)
        self.data: Dict[str, Any] = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Charge le registre de l'usine depuis le disque."""
        if not self.registry_path.exists():
            logger.warning(f"Registre introuvable à {self.registry_path}, création d'un registre par défaut.")
            return {"factory_metadata": {}, "deployed_actors": [], "ideas_backlog": []}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du registre: {e}")
            return {"factory_metadata": {}, "deployed_actors": [], "ideas_backlog": []}

    def save_registry(self) -> None:
        """Sauvegarde l'état du registre sur le disque."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        logger.info(f"Registre sauvegardé avec succès dans {self.registry_path}")

    def is_idea_compliant(self, idea_dict: Dict[str, Any]) -> bool:
        """Vérifie la conformité stricte à la Règle d'Or Zéro-Proxy."""
        text_corpus = (
            f"{idea_dict.get('slug', '')} {idea_dict.get('name', '')} "
            f"{idea_dict.get('description', '')} {idea_dict.get('protocol', '')}"
        ).lower()

        for forbidden in FORBIDDEN_KEYWORDS:
            if forbidden in text_corpus:
                logger.warning(f"Rejet de l'idée: mot-clé interdit détecté '{forbidden}'")
                return False

        slug = idea_dict.get("slug", "")
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
            logger.warning(f"Rejet de l'idée: slug invalide '{slug}'. Format attendu: kebab-case.")
            return False

        return True

    def get_deployed_slugs(self) -> List[str]:
        """Retourne la liste des slugs déjà déployés."""
        deployed = self.data.get("deployed_actors", [])
        return [actor.get("slug") for actor in deployed if actor.get("slug")]

    def select_next_idea(self, force_slug: Optional[str] = None) -> ActorIdea:
        """
        Sélectionne la prochaine idée prioritaire.
        Priorise le backlog pré-qualifié. Si une idée spécifique est demandée via force_slug, la charge.
        Si le backlog est épuisé, fait appel à Gemini pour inventer une nouvelle opportunité.
        """
        deployed_slugs = set(self.get_deployed_slugs())
        backlog = self.data.get("ideas_backlog", [])

        # Si l'utilisateur force un slug précis
        if force_slug:
            for item in backlog:
                if item.get("slug") == force_slug:
                    logger.info(f"Idée forcée sélectionnée dans le backlog: {force_slug}")
                    return ActorIdea(**item)

        # Recherche de la première idée non encore déployée et valide
        for item in backlog:
            slug = item.get("slug")
            status = item.get("status", "pending")
            if slug not in deployed_slugs and status == "pending":
                if self.is_idea_compliant(item):
                    logger.info(f"Idée sélectionnée depuis le backlog pré-qualifié: '{item.get('name')}' ({slug})")
                    return ActorIdea(**item)

        # Si toutes les 30 idées ont été déployées, génération créative avec Gemini
        logger.info("Backlog pré-qualifié épuisé ou indisponible. Activation de l'idéateur génératif Gemini...")
        return self._generate_novel_idea_with_gemini(deployed_slugs)

    def _generate_novel_idea_with_gemini(self, deployed_slugs: set) -> ActorIdea:
        """Génère une idée inédite et 100% zero-proxy grâce à Gemini."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY manquant pour l'idéation générative automatique.")

        prompt = f"""
Tu es l'Architecte Principal de l'Usine à Robots Apify.
Génère une NOUVELLE idée d'Actor B2B à forte valeur ajoutée pour Make/n8n/Zapier/Agents IA.

RÈGLES D'OR ABSOLUES :
1. ZÉRO PROXY PAYANT : Pas de réseaux sociaux verrouillés (Instagram, TikTok, LinkedIn, Twitter/X).
2. Protocoles 100% ouverts et déterministes (HTTP GET/REST, RSS/Atom, sitemaps XML, JSON-LD, DNS over HTTPS, SSL Sockets, Open Data public, APIs publiques sans auth obligatoire).
3. Forte rentabilité en location B2B mensuelle (19$ à 49$/mois).
4. Doit appartenir à l'une de ces catégories : {', '.join(ALLOWED_CATEGORIES)}.
5. Slugs déjà existants à NE PAS reproduire : {list(deployed_slugs)[:15]}.

Réponds UNIQUEMENT avec un objet JSON valide suivant exactement ce schéma :
{{
  "id": "idea-dynamic-NN",
  "slug": "nom-kebab-case-court-et-percutant",
  "name": "Nom Propre et Lisible en Anglais pour Apify Store",
  "category": "une des categories permises",
  "protocol": "Protocole technique utilise",
  "description": "Description en 2 phrases de la valeur pour Make / n8n / dev",
  "target_users": "Cible B2B",
  "default_input": {{
    "param1": "valeur_demo_reelle_qui_fonctionne"
  }},
  "pricing_suggestion_usd": 29.0,
  "status": "pending"
}}
"""

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw_text = response.text or "{}"
        except Exception as e:
            logger.warning(f"Erreur d'appel SDK google-genai ({e}), tentative via endpoint REST direct...")
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            res = requests.post(url, json=payload, timeout=30)
            res.raise_for_status()
            raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]

        # Extraction du bloc JSON
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_match:
            raise ValueError(f"Impossible d'extraire du JSON valide de la réponse Gemini: {raw_text[:200]}")

        idea_dict = json.loads(json_match.group(0))
        if not self.is_idea_compliant(idea_dict):
            raise ValueError("L'idée générée par l'IA ne respecte pas les règles d'or Zéro-Proxy.")

        # Ajout au registre
        self.data.setdefault("ideas_backlog", []).append(idea_dict)
        self.save_registry()
        return ActorIdea(**idea_dict)

    def mark_idea_as_deployed(self, slug: str, apify_act_id: str, git_branch: str) -> None:
        """Met à jour le registre après déploiement réussi d'un robot."""
        found = False
        for item in self.data.get("ideas_backlog", []):
            if item.get("slug") == slug:
                item["status"] = "deployed"
                item["deployed_at"] = os.popen("date /t").read().strip() if os.name == "nt" else "now"
                found = True
                break

        deployed = self.data.setdefault("deployed_actors", [])
        # Mise à jour ou ajout
        existing = next((a for a in deployed if a.get("slug") == slug), None)
        actor_entry = {
            "slug": slug,
            "apify_act_id": apify_act_id,
            "git_branch": git_branch,
            "status": "active",
            "health": "healthy",
            "last_maintenance_at": None
        }
        if existing:
            existing.update(actor_entry)
        else:
            deployed.append(actor_entry)

        meta = self.data.setdefault("factory_metadata", {})
        meta["total_actors_deployed"] = len(deployed)
        self.save_registry()
        logger.info(f"Robot '{slug}' enregistré comme déployé ({apify_act_id}).")


if __name__ == "__main__":
    ideator = BrainIdeator()
    idea = ideator.select_next_idea()
    print(f"Idée sélectionnée : {idea.model_dump_json(indent=2)}")
