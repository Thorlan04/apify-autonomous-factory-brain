"""
Module ComptaManager - Livre des Recettes Officiel & Fiscalité Micro-BNC.

Gère la conformité fiscale française pour Micro-Entrepreneur (BNC) :
- Enregistrement chronologique officiel des encaissements (Livre des Recettes - art. 286 du CGI).
- Calcul automatique des reports fiscaux Déclaration 2042-C-PRO (Cases 5HQ et 5TE).
- Suivi de la TVA intracommunautaire (Règle d'autoliquidation UE / DES).
- Analyse des seuils URSSAF et Franchise en base de TVA.
"""

import csv
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger("ComptaManager")

# Paramètres fiscaux officiels Micro-Entreprise BNC (Prestations intellectuelles & redevances logicielles)
TAUX_ABATTEMENT_FORFAITAIRE_BNC = 0.34      # 34% d'abattement automatique par l'administration fiscale
TAUX_VERSEMENT_LIBERATOIRE_BNC = 0.022      # 2,2% de versement libératoire IR si éligible (case 5TE)
TAUX_COTISATIONS_URSSAF_BNC = 0.231         # 23,1% de cotisations sociales de base
PLAFOND_MICRO_BNC_ANNUEL = 77700.0          # Seuil maximum du régime micro-BNC
PLAFOND_FRANCHISE_TVA_SERVICES = 36800.0    # Seuil franchise de TVA en prestation de services


class ComptaManager:
    """Gestionnaire de comptabilité et de fiscalité Micro-Entreprise."""

    def __init__(self, compta_dir: Optional[Path] = None):
        if compta_dir is None:
            self.compta_dir = Path(__file__).resolve().parent.parent / "compta_impots"
        else:
            self.compta_dir = Path(compta_dir)
        self.compta_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.compta_dir / "livre_recettes_officiel.csv"
        self.fiscal_json_path = self.compta_dir / "rapport_fiscal_micro_bnc.json"

        self._ensure_files_exist()

    def _ensure_files_exist(self) -> None:
        """Initialise le fichier CSV et le rapport JSON avec l'en-tête officiel si inexistants."""
        if not self.csv_path.exists():
            headers = [
                "date_encaissement",
                "reference_piece",
                "client_debiteur",
                "nature_prestation",
                "montant_brute_eur",
                "mode_reglement",
                "mention_tva",
                "declaration_europeenne_services_des",
                "pays_debiteur"
            ]
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(headers)
            logger.info(f"Livre des recettes initialisé à {self.csv_path}")

        if not self.fiscal_json_path.exists():
            self.recalculate_fiscal_summary()

    def add_payout_entry(
        self,
        reference_piece: str,
        montant_eur: float,
        date_str: Optional[str] = None,
        nature: str = "Redevances mensuelles exploitation Store Apify (Actors B2B)"
    ) -> Dict[str, Any]:
        """
        Enregistre un nouveau virement d'Apify dans le Livre des Recettes officiel.
        """
        if date_str is None:
            date_str = datetime.now().strftime("%d/%m/%Y")

        entry = [
            date_str,
            reference_piece,
            "Apify Technologies s.r.o. (CZ04787261)",
            nature,
            f"{montant_eur:.2f}",
            "Virement Bancaire SEPA",
            "Autoliquidation - Art. 196 Directive 2006/112/CE",
            "OUI (Prestation B2B intracommunautaire UE)",
            "Tchéquie (UE)"
        ]

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(entry)

        logger.info(f"Recette enregistrée : {montant_eur:.2f} € (Réf: {reference_piece})")
        return self.recalculate_fiscal_summary()

    def recalculate_fiscal_summary(self) -> Dict[str, Any]:
        """
        Calcule les montants consolidés, les cases déclaratives d'impôts
        (5HQ et 5TE) et les estimations de cotisations URSSAF.
        """
        total_recettes = 0.0
        nb_transactions = 0

        if self.csv_path.exists():
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    try:
                        montant_str = row.get("montant_brute_eur", "0").replace(",", ".")
                        total_recettes += float(montant_str)
                        nb_transactions += 1
                    except (ValueError, TypeError):
                        pass

        # Calculs fiscaux micro-BNC
        assiette_imposable_apres_abattement = total_recettes * (1.0 - TAUX_ABATTEMENT_FORFAITAIRE_BNC)
        cotisations_urssaf_estimees = total_recettes * TAUX_COTISATIONS_URSSAF_BNC
        versement_liberatoire_estime = total_recettes * TAUX_VERSEMENT_LIBERATOIRE_BNC
        reste_net_en_poche_estime = total_recettes - cotisations_urssaf_estimees - versement_liberatoire_estime

        # Vérification des seuils
        alerte_tva = total_recettes > PLAFOND_FRANCHISE_TVA_SERVICES
        alerte_plafond_bnc = total_recettes > PLAFOND_MICRO_BNC_ANNUEL

        report = {
            "regime_fiscal": "Micro-BNC (Professions Libérales / Services Informatiques)",
            "derniere_mise_a_jour": datetime.now(timezone.utc).isoformat(),
            "synthese_encaissements": {
                "total_recettes_brutes_eur": round(total_recettes, 2),
                "nombre_payouts_enregistres": nb_transactions,
                "devise": "EUR"
            },
            "declaration_impot_sur_le_revenu_2042_c_pro": {
                "case_5HQ_recettes_brutes_sans_abattement": round(total_recettes, 2),
                "explication_5HQ": "Montant brut total des encaissements de l'année civile. L'administration appliquera l'abattement forfaitaire de 34%.",
                "abattement_forfaitaire_34_pct": round(total_recettes * TAUX_ABATTEMENT_FORFAITAIRE_BNC, 2),
                "revenu_net_fiscal_apres_abattement": round(assiette_imposable_apres_abattement, 2),
                "case_5TE_versement_liberatoire": round(total_recettes, 2),
                "explication_5TE": "À remplir UNIQUEMENT si vous avez opté pour le versement libératoire de l'impôt sur le revenu auprès de l'URSSAF (taux 2,2%)."
            },
            "cotisations_sociales_urssaf_estimees": {
                "taux_applique": "23,10 %",
                "montant_a_payer_urssaf": round(cotisations_urssaf_estimees, 2),
                "net_apres_urssaf": round(total_recettes - cotisations_urssaf_estimees, 2)
            },
            "conformite_tva_et_ue": {
                "regime_tva": "Franchise en base de TVA (Art. 293 B du CGI) ou Prestation B2B intracommunautaire (Autoliquidation)",
                "payout_apify_tva": "0% TVA facturée (Autoliquidation par le client Apify en République Tchèque - Art. 196 Directive 2006/112/CE)",
                "declaration_europeenne_de_services_des": "À déposer mensuellement sur douane.gouv.fr pour les ventes B2B en UE sans TVA.",
                "depassement_seuil_franchise_tva": alerte_tva,
                "seuil_franchise_tva_services_eur": PLAFOND_FRANCHISE_TVA_SERVICES
            },
            "alertes_seuils_fiscaux": {
                "seuil_micro_bnc_eur": PLAFOND_MICRO_BNC_ANNUEL,
                "pourcentage_seuil_consomme": round((total_recettes / PLAFOND_MICRO_BNC_ANNUEL) * 100, 2),
                "depassement_seuil_micro_bnc": alerte_plafond_bnc
            }
        }

        with open(self.fiscal_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Rapport fiscal mis à jour dans {self.fiscal_json_path}")
        return report

    def sync_apify_payouts_simulation(self) -> Dict[str, Any]:
        """
        Synchronise ou simule les payouts Apify Store.
        Si la flotte génère des revenus d'abonnements, les consigne dans le livre officiel.
        """
        # Vérification si un enregistrement initial existe
        if self.csv_path.exists():
            with open(self.csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if len(lines) <= 1:
                    # Ajout d'une ligne d'exemple claire
                    self.add_payout_entry(
                        reference_piece="APIFY-PAYOUT-INITIAL-DEMO",
                        montant_eur=0.00,
                        date_str=datetime.now().strftime("%d/%m/%Y"),
                        nature="Initialisation Usine Apify - Solde d'amorçage"
                    )

        return self.recalculate_fiscal_summary()


if __name__ == "__main__":
    compta = ComptaManager()
    summary = compta.recalculate_fiscal_summary()
    print(f"Synthèse fiscale : {json.dumps(summary, indent=2)}")
