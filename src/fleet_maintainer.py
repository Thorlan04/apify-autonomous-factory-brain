"""
Module FleetMaintainer - Maintenance automatique de la flotte d'Actors Apify.

Sélectionne 1 robot déployé par semaine (stratégie Round-Robin) pour vérifier
sa santé opérationnelle, rafraîchir son build et maintenir le badge "Recently Updated"
sur l'Apify Store, tout en respectant scrupuleusement le quota gratuit de 5 $/mois.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger("FleetMaintainer")

APIFY_BASE_URL = "https://api.apify.com/v2"


class FleetMaintainer:
    """Agent de maintenance continue et d'optimisation SEO de la flotte."""

    def __init__(self, registry_path: Optional[Path] = None, apify_token: Optional[str] = None):
        if registry_path is None:
            self.registry_path = Path(__file__).resolve().parent.parent / "data" / "factory_registry.json"
        else:
            self.registry_path = Path(registry_path)
        self.apify_token = apify_token or os.getenv("APIFY_API_TOKEN")
        self.data: Dict[str, Any] = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Charge le registre des robots."""
        if not self.registry_path.exists():
            return {"factory_metadata": {}, "deployed_actors": [], "ideas_backlog": []}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement registre dans FleetMaintainer : {e}")
            return {"factory_metadata": {}, "deployed_actors": [], "ideas_backlog": []}

    def save_registry(self) -> None:
        """Sauvegarde le registre mis à jour."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def select_actor_for_maintenance(self) -> Optional[Dict[str, Any]]:
        """
        Sélectionne le robot nécessitant le plus une mise à jour (round-robin).
        Trie par la date `last_maintenance_at` la plus ancienne ou nulle.
        """
        deployed = self.data.get("deployed_actors", [])
        if not deployed:
            logger.info("Aucun robot déployé dans la flotte pour le moment.")
            return None

        # Tri : ceux sans last_maintenance_at en premier, puis les plus anciens
        def get_sort_key(actor: Dict[str, Any]) -> str:
            return actor.get("last_maintenance_at") or "1970-01-01T00:00:00Z"

        sorted_fleet = sorted(deployed, key=get_sort_key)
        selected = sorted_fleet[0]
        logger.info(f"Robot sélectionné pour la maintenance hebdomadaire : {selected.get('slug')} (ID: {selected.get('apify_act_id')})")
        return selected

    def perform_weekly_maintenance(self) -> Dict[str, Any]:
        """
        Exécute la routine hebdomadaire sur 1 robot :
        1. Vérifie l'état des derniers runs sur Apify.
        2. Déclenche un rebuild léger pour rafraîchir le badge Apify Store.
        3. Met à jour le statut dans le registre.
        """
        target = self.select_actor_for_maintenance()
        if not target:
            return {"maintenance_executed": False, "reason": "No deployed actors"}

        slug = target.get("slug")
        act_id = target.get("apify_act_id")

        now_iso = datetime.now(timezone.utc).isoformat()
        health_status = "healthy"
        rebuild_triggered = False

        if not self.apify_token or act_id.startswith("simulated-"):
            logger.info(f"Simulation de maintenance pour l'Actor {slug}...")
            target["last_maintenance_at"] = now_iso
            target["health"] = "healthy"
            self.save_registry()
            return {
                "maintenance_executed": True,
                "slug": slug,
                "act_id": act_id,
                "simulation": True,
                "timestamp": now_iso
            }

        headers = {
            "Authorization": f"Bearer {self.apify_token}",
            "Content-Type": "application/json"
        }

        # 1. Vérification des derniers runs
        try:
            runs_res = requests.get(f"{APIFY_BASE_URL}/acts/{act_id}/runs?limit=3", headers=headers, timeout=15)
            if runs_res.status_code == 200:
                runs = runs_res.json().get("data", {}).get("items", [])
                if runs:
                    last_status = runs[0].get("status")
                    if last_status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                        health_status = "degraded"
                        logger.warning(f"Dernier run de {slug} en anomalie : {last_status}")
                    else:
                        health_status = "healthy"
        except Exception as e:
            logger.warning(f"Impossible de vérifier les runs de {slug} : {e}")

        # 2. Déclenchement du rebuild pour rafraîchir le badge 'Recently Updated'
        try:
            build_res = requests.post(f"{APIFY_BASE_URL}/acts/{act_id}/builds", headers=headers, timeout=20)
            if build_res.status_code in [200, 201]:
                rebuild_triggered = True
                logger.info(f"Rebuild de maintenance lancé avec succès pour {slug}.")
            else:
                logger.warning(f"Rebuild refusé ({build_res.status_code}) : {build_res.text[:150]}")
        except Exception as eb:
            logger.warning(f"Erreur lors du déclenchement du build : {eb}")

        # 3. Sauvegarde dans le registre
        target["last_maintenance_at"] = now_iso
        target["health"] = health_status
        target["status"] = "active"
        self.save_registry()

        return {
            "maintenance_executed": True,
            "slug": slug,
            "act_id": act_id,
            "health": health_status,
            "rebuild_triggered": rebuild_triggered,
            "timestamp": now_iso
        }


if __name__ == "__main__":
    maintainer = FleetMaintainer()
    result = maintainer.perform_weekly_maintenance()
    print(f"Résultat maintenance : {json.dumps(result, indent=2)}")
