"""
Suite de tests unitaires et d'intégration pour l'Usine à Robots Apify Autonome.
"""

import json
import shutil
import tempfile
from pathlib import Path
import pytest

from src.brain_ideator import BrainIdeator, ActorIdea
from src.compta_manager import ComptaManager
from src.apify_api_deployer import ApifyApiDeployer
from src.fleet_maintainer import FleetMaintainer


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


def test_registry_contains_30_zero_proxy_ideas():
    """Vérifie que le registre par défaut contient bien les 30 idées B2B Zéro-Proxy."""
    registry_file = Path(__file__).resolve().parent.parent / "data" / "factory_registry.json"
    assert registry_file.exists()
    with open(registry_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    backlog = data.get("ideas_backlog", [])
    assert len(backlog) >= 30, f"Attendu >= 30 idées, trouvé: {len(backlog)}"

    ideator = BrainIdeator(registry_path=registry_file)
    for idea in backlog:
        assert ideator.is_idea_compliant(idea), f"L'idée {idea.get('slug')} ne respecte pas les règles Zero-Proxy."


def test_brain_ideator_selects_first_pending_idea(temp_dir):
    """Vérifie la sélection de la première idée non encore déployée."""
    mock_registry = temp_dir / "test_registry.json"
    registry_data = {
        "factory_metadata": {},
        "deployed_actors": [{"slug": "first-actor"}],
        "ideas_backlog": [
            {
                "id": "1",
                "slug": "first-actor",
                "name": "First Actor",
                "category": "e-commerce",
                "protocol": "HTTP",
                "description": "First description",
                "target_users": "Users 1",
                "default_input": {"url": "https://example.com"},
                "status": "deployed"
            },
            {
                "id": "2",
                "slug": "second-actor",
                "name": "Second Actor",
                "category": "ai-llm-data-prep",
                "protocol": "HTTP GET",
                "description": "Second description",
                "target_users": "Users 2",
                "default_input": {"param": "val"},
                "status": "pending"
            }
        ]
    }
    with open(mock_registry, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)

    ideator = BrainIdeator(registry_path=mock_registry)
    idea = ideator.select_next_idea()
    assert idea.slug == "second-actor"
    assert idea.name == "Second Actor"


def test_forbidden_keywords_rejection():
    """Vérifie le blocage automatique des scrapers de réseaux sociaux interdits."""
    ideator = BrainIdeator()
    forbidden_idea = {
        "slug": "instagram-profile-scraper",
        "name": "Instagram Scraper",
        "description": "Scrapes user followers on Instagram",
        "protocol": "HTTP requests"
    }
    assert ideator.is_idea_compliant(forbidden_idea) is False


def test_compta_manager_calculations(temp_dir):
    """Vérifie le Livre des Recettes et le calcul des cases 5HQ et 5TE."""
    compta = ComptaManager(compta_dir=temp_dir)

    # Ajout de 2 virements Apify
    compta.add_payout_entry("APIFY-2026-01", 1200.0, date_str="15/01/2026")
    compta.add_payout_entry("APIFY-2026-02", 800.0, date_str="15/02/2026")

    summary = compta.recalculate_fiscal_summary()

    # Recettes totales = 2000 €
    assert summary["synthese_encaissements"]["total_recettes_brutes_eur"] == 2000.0
    assert summary["synthese_encaissements"]["nombre_payouts_enregistres"] == 2

    # Case 5HQ = 2000 €
    assert summary["declaration_impot_sur_le_revenu_2042_c_pro"]["case_5HQ_recettes_brutes_sans_abattement"] == 2000.0

    # Abattement 34% = 680 € -> Net imposable = 1320 €
    assert summary["declaration_impot_sur_le_revenu_2042_c_pro"]["abattement_forfaitaire_34_pct"] == 680.0
    assert summary["declaration_impot_sur_le_revenu_2042_c_pro"]["revenu_net_fiscal_apres_abattement"] == 1320.0

    # Cotisations URSSAF 23.1% de 2000 € = 462 €
    assert summary["cotisations_sociales_urssaf_estimees"]["montant_a_payer_urssaf"] == 462.0


def test_fleet_maintainer_round_robin(temp_dir):
    """Vérifie la sélection de maintenance par tri d'ancienneté."""
    mock_registry = temp_dir / "registry.json"
    registry_data = {
        "deployed_actors": [
            {
                "slug": "actor-recent",
                "apify_act_id": "act-1",
                "last_maintenance_at": "2026-10-15T10:00:00Z"
            },
            {
                "slug": "actor-oldest",
                "apify_act_id": "act-2",
                "last_maintenance_at": "2026-09-01T10:00:00Z"
            },
            {
                "slug": "actor-never-updated",
                "apify_act_id": "act-3",
                "last_maintenance_at": None
            }
        ]
    }
    with open(mock_registry, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)

    maintainer = FleetMaintainer(registry_path=mock_registry)
    selected = maintainer.select_actor_for_maintenance()
    assert selected["slug"] == "actor-never-updated"


def test_apify_deployer_budget_simulation():
    """Vérifie le comportement de sécurité budgétaire du déployeur."""
    deployer = ApifyApiDeployer(apify_token=None)
    ok, info = deployer.check_apify_budget()
    assert ok is True
    assert info.get("simulation") is True
