"""
Module FactoryOrchestrator - Chef d'orchestre principal de l'Usine à Robots Apify.

Orchestre de bout en bout le cycle de vie autonome hebdomadaire :
1. Contrôle des budgets et quotas Apify (Règle des 5 $/mois).
2. Idéation B2B Zéro-Proxy déterministe (BrainIdeator).
3. Génération de code complète sans placeholder (ActorCodeGenerator).
4. Auto-test en conditions réelles et auto-réparation IA jusqu'à 3 fois (SandboxTester).
5. Publication Git et déploiement API REST Apify (ApifyApiDeployer).
6. Maintenance continue de la flotte existante (FleetMaintainer).
7. Tenue des comptes officiels et fiscalité Micro-BNC (ComptaManager).
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Chargement des variables d'environnement si un fichier .env existe
load_dotenv()

# Assure la présence de la racine du projet dans sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.brain_ideator import BrainIdeator
from src.actor_code_generator import ActorCodeGenerator
from src.sandbox_tester import SandboxTester
from src.apify_api_deployer import ApifyApiDeployer
from src.fleet_maintainer import FleetMaintainer
from src.compta_manager import ComptaManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("FactoryOrchestrator")


def print_banner() -> None:
    banner = """
================================================================================
          APIFY AUTONOMOUS FACTORY BRAIN - USINE A ROBOTS 100% AUTONOME
               Budget Protection: Free Tier $5.00/mo (0€ de frais)
================================================================================
    """
    print(banner)


def run_factory_cycle(
    force_slug: str = None,
    skip_deploy: bool = False,
    maintenance_only: bool = False,
    create_only: bool = False
) -> int:
    """Exécute le cycle complet de l'Usine."""
    print_banner()
    logger.info("Démarrage du cycle opérationnel de l'Usine...")

    ideator = BrainIdeator()
    code_generator = ActorCodeGenerator()
    sandbox = SandboxTester()
    deployer = ApifyApiDeployer()
    maintainer = FleetMaintainer()
    compta = ComptaManager()

    # 1. Vérification du budget et de la santé du compte Apify
    logger.info("Étape 1/6 : Audit du budget Apify et des plafonds de gratuité...")
    budget_ok, budget_info = deployer.check_apify_budget()
    if not budget_ok:
        logger.error(f"Arrêt préventif du cycle : risque de dépassement de quota ({budget_info}).")
        return 1

    deployment_result = None

    if not maintenance_only:
        # 2. Idéation et sélection de la prochaine opportunité B2B
        logger.info("Étape 2/6 : Sélection d'une niche B2B Zéro-Proxy déterministe...")
        try:
            idea = ideator.select_next_idea(force_slug=force_slug)
            logger.info(f"Opportunité qualifiée : '{idea.name}' ({idea.slug}) - Catégorie : {idea.category}")
        except Exception as e:
            logger.error(f"Échec lors de l'idéation : {e}")
            return 1

        # 3. Génération du code source complet de l'Actor
        logger.info(f"Étape 3/6 : Génération IA du code de l'Actor '{idea.slug}'...")
        try:
            actor_dir = code_generator.generate_actor_files(idea)
            logger.info(f"Fichiers créés avec succès dans : {actor_dir}")
        except Exception as e:
            logger.error(f"Échec lors de la génération du code de l'Actor : {e}")
            return 1

        # 4. Sandbox d'auto-test et d'auto-réparation
        logger.info(f"Étape 4/6 : Test d'exécution sandbox et boucle d'auto-guérison...")
        success, test_report = sandbox.run_and_heal(actor_dir)

        if not success:
            logger.critical(
                f"🚨 Le robot '{idea.slug}' a échoué son test d'auto-réparation. "
                f"Conformément à la Règle 2, aucun déploiement ne sera effectué sur Apify. "
                f"Rapport : {test_report}"
            )
            return 2

        logger.info(f"🎉 Validation sandbox réussie : {test_report.get('item_count')} items générés.")

        # 5. Déploiement Git et Enregistrement API Apify
        if not skip_deploy:
            logger.info(f"Étape 5/6 : Déploiement Git et enregistrement API Apify...")
            try:
                git_branch = deployer.deploy_to_git_branch(actor_dir, idea.slug)
                deployment_result = deployer.register_or_update_apify_actor(
                    actor_dir=actor_dir,
                    actor_slug=idea.slug,
                    actor_name=idea.name,
                    actor_description=idea.description,
                    git_branch=git_branch
                )
                logger.info(f"Déploiement Apify finalisé : {deployment_result}")

                # Enregistrement dans la mémoire de l'Usine
                ideator.mark_idea_as_deployed(
                    slug=idea.slug,
                    apify_act_id=deployment_result.get("act_id", "pending"),
                    git_branch=git_branch
                )
            except Exception as e:
                logger.error(f"Erreur lors du déploiement : {e}")
                return 1
        else:
            logger.info("Mode --skip-deploy actif. Déploiement Git/Apify ignoré.")

    # 6. Maintenance de la flotte existante
    if not create_only:
        logger.info("Étape 6/6 : Maintenance de la flotte et optimisation SEO Store...")
        try:
            maint_result = maintainer.perform_weekly_maintenance()
            logger.info(f"Rapport de maintenance flotte : {maint_result}")
        except Exception as em:
            logger.warning(f"Avertissement lors de la maintenance flotte : {em}")

    # 7. Synchronisation de la comptabilité Micro-BNC
    try:
        fiscal_summary = compta.sync_apify_payouts_simulation()
        logger.info(
            f"Livre des recettes à jour. Total brut encaissé : "
            f"{fiscal_summary['synthese_encaissements']['total_recettes_brutes_eur']} € "
            f"(Case 5HQ déclarée)."
        )
    except Exception as ec:
        logger.warning(f"Avertissement lors de la mise à jour comptable : {ec}")

    # Mise à jour de l'horodatage du cycle
    registry_meta = ideator.data.setdefault("factory_metadata", {})
    registry_meta["last_cycle_timestamp"] = datetime.now(timezone.utc).isoformat()
    ideator.save_registry()

    logger.info("================================================================================")
    logger.info("✅ CYCLE DE L'USINE TERMINE AVEC SUCCES.")
    logger.info("================================================================================")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Usine à Robots Apify Autonome")
    parser.add_argument("--force-slug", type=str, default=None, help="Force le déploiement d'une idée précise")
    parser.add_argument("--skip-deploy", action="store_true", help="Ignore le push Git et l'appel API Apify")
    parser.add_argument("--maintenance-only", action="store_true", help="N'exécute que la maintenance de la flotte")
    parser.add_argument("--create-only", action="store_true", help="N'exécute que la création d'un nouveau robot")
    args = parser.parse_args()

    exit_code = run_factory_cycle(
        force_slug=args.force_slug,
        skip_deploy=args.skip_deploy,
        maintenance_only=args.maintenance_only,
        create_only=args.create_only
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
