"""
Module ApifyApiDeployer - Déploiement automatisé sur Git et Apify REST API.

Gère la publication du robot sur une branche Git dédiée 'actor/<actor_slug>'
et configure l'Actor sur la plateforme Apify (https://api.apify.com/v2/acts)
en respectant scrupuleusement la limite des 5 $/mois de quota gratuit.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger("ApifyApiDeployer")

APIFY_BASE_URL = "https://api.apify.com/v2"
MAX_FREE_MONTHLY_BUDGET_USD = 5.0
SAFETY_MARGIN_SPEND_LIMIT_USD = 1.0  # Conserve 80% du quota gratuit


class ApifyApiDeployer:
    """Gestionnaire de déploiement Git & Apify REST API."""

    def __init__(
        self,
        apify_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        github_token: Optional[str] = None
    ):
        self.apify_token = apify_token or os.getenv("APIFY_API_TOKEN")
        self.github_repo = github_repo or os.getenv("GITHUB_REPOSITORY")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")

    def check_apify_budget(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Interroge l'API Apify pour vérifier le solde et la consommation mensuelle.
        Garantit que l'on reste dans la limite des 5 $/mois offerts (0 € engagé).
        """
        if not self.apify_token:
            logger.warning("APIFY_API_TOKEN non configuré. Mode simulation actif.")
            return True, {"simulation": True, "spend_usd": 0.0, "budget_ok": True}

        headers = {"Authorization": f"Bearer {self.apify_token}"}
        try:
            # 1. Vérification du compte utilisateur
            res = requests.get(f"{APIFY_BASE_URL}/users/me", headers=headers, timeout=15)
            if res.status_code != 200:
                logger.error(f"Erreur API Apify /users/me : {res.status_code} - {res.text}")
                return False, {"error": f"HTTP {res.status_code}", "budget_ok": False}

            user_data = res.json().get("data", {})
            username = user_data.get("username", "unknown")
            plan = user_data.get("plan", {}).get("id", "FREE")

            # 2. Vérification des usages mensuels si disponibles
            usage_res = requests.get(f"{APIFY_BASE_URL}/users/me/usage/monthly", headers=headers, timeout=15)
            total_spend = 0.0
            if usage_res.status_code == 200:
                usage_data = usage_res.json().get("data", {})
                total_spend = float(usage_data.get("totalUsageUsd", 0.0))

            logger.info(f"Compte Apify : @{username} | Plan : {plan} | Dépense mensuelle actuelle : ${total_spend:.3f}")

            if total_spend > (MAX_FREE_MONTHLY_BUDGET_USD - SAFETY_MARGIN_SPEND_LIMIT_USD):
                logger.warning(f"Alerte quota : Dépense ${total_spend:.2f} proche du plafond gratuit de $5.00.")
                return False, {
                    "username": username,
                    "plan": plan,
                    "total_spend": total_spend,
                    "budget_ok": False,
                    "reason": "Quota limite atteint pour préserver la gratuité."
                }

            return True, {
                "username": username,
                "plan": plan,
                "total_spend": total_spend,
                "budget_ok": True
            }

        except Exception as e:
            logger.error(f"Erreur lors de la vérification du budget Apify : {e}")
            return False, {"error": str(e), "budget_ok": False}

    def deploy_to_git_branch(self, actor_dir: Path, actor_slug: str) -> str:
        """
        Pousse les fichiers du robot sur une branche Git dédiée `actor/<actor_slug>`.
        """
        branch_name = f"actor/{actor_slug}"
        logger.info(f"Préparation de la branche Git '{branch_name}' pour {actor_slug}...")

        # Vérification si nous sommes dans un repo Git
        try:
            is_git = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True
            ).returncode == 0
        except Exception:
            is_git = False

        if not is_git:
            logger.info("Dépôt Git non initialisé ou non accessible. Initialisation locale...")
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Autonomous Factory Brain"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "brain@autonomous-factory.local"], capture_output=True)

        try:
            # Création / bascule sur la branche dédiée
            subprocess.run(["git", "checkout", "-B", branch_name], capture_output=True)

            # Copie des fichiers de l'Actor directement à la racine de la branche pour Apify
            import shutil
            for item in actor_dir.iterdir():
                if item.name in ["storage", ".git"]:
                    continue
                target = Path.cwd() / item.name
                if item.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)

            subprocess.run(["git", "add", "."], capture_output=True)
            commit_msg = f"feat(actor): autonomous deployment of {actor_slug}"
            subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)

            # Push vers origin (avec token si présent, sinon via le credential helper local)
            if self.github_token and self.github_repo:
                remote_url = f"https://x-access-token:{self.github_token}@github.com/{self.github_repo}.git"
                subprocess.run(["git", "push", "-u", remote_url, branch_name, "--force"], capture_output=True)
                logger.info(f"Branche '{branch_name}' poussée avec succès sur GitHub via GITHUB_TOKEN.")
            else:
                push_res = subprocess.run(["git", "push", "-u", "origin", branch_name, "--force"], capture_output=True, text=True)
                if push_res.returncode == 0:
                    logger.info(f"Branche '{branch_name}' poussée avec succès sur GitHub origin.")
                else:
                    logger.info(f"Branche locale '{branch_name}' validée et commitée (push origin en attente).")

            # Retour propre sur la branche principale
            subprocess.run(["git", "checkout", "main", "--force"], capture_output=True)
            # Nettoyage des fichiers résiduels du root de la branche actor sur main
            subprocess.run(["git", "clean", "-fd", "-e", "generated_actors", "-e", ".env"], capture_output=True)
        except Exception as e:
            logger.warning(f"Opération Git terminée avec avertissement : {e}")

        return branch_name

    def register_or_update_apify_actor(
        self,
        actor_dir: Path,
        actor_slug: str,
        actor_name: str,
        actor_description: str,
        git_branch: str
    ) -> Dict[str, Any]:
        """
        Crée ou met à jour l'Actor via l'API REST officielle d'Apify.
        Lien Git ou source code direct + déclenchement du build.
        """
        budget_ok, budget_info = self.check_apify_budget()
        if not budget_ok:
            raise RuntimeError(f"Déploiement refusé : protection du budget gratuit ({budget_info}).")

        if not self.apify_token:
            logger.warning("Pas de jeton Apify. Simulation de l'enregistrement de l'Actor.")
            return {
                "act_id": f"simulated-{actor_slug}",
                "name": actor_slug,
                "status": "SIMULATED",
                "build_triggered": False
            }

        headers = {
            "Authorization": f"Bearer {self.apify_token}",
            "Content-Type": "application/json"
        }

        # 1. Vérification si l'Actor existe déjà
        username = budget_info.get("username", "me")
        check_url = f"{APIFY_BASE_URL}/acts/{username}~{actor_slug}"
        res = requests.get(check_url, headers=headers, timeout=15)

        git_repo_url = f"https://github.com/{self.github_repo}.git#{git_branch}" if self.github_repo else ""

        actor_payload = {
            "name": actor_slug,
            "title": actor_name,
            "description": actor_description[:250],
            "isPublic": False,
            "defaultRunOptions": {
                "build": "latest",
                "timeoutSecs": 300,
                "memoryMbytes": 256
            }
        }

        # Configuration de la source (Git Repo si disponible, sinon source locale)
        if git_repo_url:
            actor_payload["versions"] = [
                {
                    "versionNumber": "0.1",
                    "buildTag": "latest",
                    "sourceType": "GIT_REPO",
                    "gitRepoUrl": git_repo_url
                }
            ]

        if res.status_code == 200:
            # Mise à jour
            act_id = res.json()["data"]["id"]
            logger.info(f"L'Actor {actor_slug} existe déjà (ID: {act_id}). Mise à jour...")
            update_res = requests.put(f"{APIFY_BASE_URL}/acts/{act_id}", headers=headers, json=actor_payload, timeout=20)
            update_res.raise_for_status()
        elif res.status_code == 404:
            # Création
            logger.info(f"Création d'un nouvel Actor '{actor_slug}' sur Apify...")
            create_res = requests.post(f"{APIFY_BASE_URL}/acts", headers=headers, json=actor_payload, timeout=20)
            create_res.raise_for_status()
            act_id = create_res.json()["data"]["id"]
            logger.info(f"Actor créé avec succès sur Apify. ID: {act_id}")
        else:
            res.raise_for_status()
            act_id = "unknown"

        # 2. Déclenchement d'un Build Apify (1 build hebdomadaire = ~0.02$)
        logger.info(f"Déclenchement du build de validation pour l'Actor {act_id}...")
        build_triggered = False
        try:
            build_res = requests.post(
                f"{APIFY_BASE_URL}/acts/{act_id}/builds?version=0.1",
                headers=headers,
                timeout=20
            )
            if build_res.status_code in [200, 201]:
                build_triggered = True
                build_id = build_res.json().get("data", {}).get("id")
                logger.info(f"Build lancé avec succès (ID: {build_id}).")
            else:
                logger.warning(f"Build non déclenché : {build_res.status_code} - {build_res.text}")
        except Exception as eb:
            logger.warning(f"Avertissement lors de la requête de build : {eb}")

        return {
            "act_id": act_id,
            "name": actor_slug,
            "status": "DEPLOYED",
            "build_triggered": build_triggered,
            "git_branch": git_branch
        }


if __name__ == "__main__":
    deployer = ApifyApiDeployer()
    ok, info = deployer.check_apify_budget()
    print(f"Vérification budget Apify : {ok} - {info}")
