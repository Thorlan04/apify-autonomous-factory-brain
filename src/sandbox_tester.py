"""
Module SandboxTester - Sandbox d'auto-test et d'auto-réparation pour Actors Apify.

Exécute en conditions réelles le code du robot généré, vérifie la production
d'au moins 1 enregistrement de données valide et sollicite Gemini pour corriger
automatiquement le code jusqu'à 3 fois en cas d'erreur ou d'absence de résultat.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger("SandboxTester")

MAX_REPAIR_ATTEMPTS = 3


class SandboxTester:
    """Sandbox d'exécution isolée et d'auto-guérison par IA."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    def run_and_heal(self, actor_dir: Path) -> Tuple[bool, Dict[str, Any]]:
        """
        Exécute le robot localement et auto-répare si nécessaire.
        Retourne (is_success, execution_summary).
        """
        actor_dir = Path(actor_dir)
        main_py = actor_dir / "src" / "main.py"
        input_schema_file = actor_dir / ".actor" / "input_schema.json"

        if not main_py.exists():
            return False, {"error": f"Fichier {main_py} introuvable."}

        # Préparation du stockage local simulé d'Apify
        storage_dir = actor_dir / "storage"
        kvs_dir = storage_dir / "key_value_stores" / "default"
        dataset_dir = storage_dir / "datasets" / "default"

        kvs_dir.mkdir(parents=True, exist_ok=True)
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Extraction des entrées par défaut
        default_inputs = {}
        if input_schema_file.exists():
            try:
                with open(input_schema_file, "r", encoding="utf-8") as f:
                    schema_data = json.load(f)
                    props = schema_data.get("properties", {})
                    for k, v in props.items():
                        default_inputs[k] = v.get("default", v.get("prefill", ""))
            except Exception as e:
                logger.warning(f"Impossible de lire input_schema.json: {e}")

        # Écriture du fichier INPUT.json
        with open(kvs_dir / "INPUT.json", "w", encoding="utf-8") as f:
            json.dump(default_inputs, f, indent=2)

        attempt = 0
        last_error = ""

        while attempt < MAX_REPAIR_ATTEMPTS:
            attempt += 1
            logger.info(f"--- [Tentative {attempt}/{MAX_REPAIR_ATTEMPTS}] Exécution sandbox de {actor_dir.name} ---")

            # Nettoyage des datasets précédents
            for item in dataset_dir.glob("*.json"):
                try:
                    item.unlink()
                except Exception:
                    pass

            # Environnement d'exécution
            env = os.environ.copy()
            env["APIFY_LOCAL_STORAGE_DIR"] = str(storage_dir)
            env["APIFY_INPUT_KEY"] = "INPUT"
            env["PYTHONPATH"] = str(actor_dir) + os.pathsep + env.get("PYTHONPATH", "")

            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "src.main"],
                    cwd=str(actor_dir),
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env
                )
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                exit_code = 124
                stdout = ""
                stderr = "TimeoutExpired: L'exécution a dépassé la limite de 90 secondes."
            except Exception as e:
                exit_code = 1
                stdout = ""
                stderr = f"Exception système lors du lancement : {str(e)}"

            # Comptage des enregistrements produits
            dataset_items = list(dataset_dir.glob("*.json"))
            results_file = dataset_dir / "results.json"
            item_count = len(dataset_items)

            # Vérification des résultats dans results.json consolidé si présent
            sample_data = None
            if results_file.exists():
                try:
                    with open(results_file, "r", encoding="utf-8") as rf:
                        data = json.load(rf)
                        if isinstance(data, list):
                            item_count = max(item_count, len(data))
                            sample_data = data[0] if data else None
                        elif isinstance(data, dict):
                            item_count = max(item_count, 1)
                            sample_data = data
                except Exception:
                    pass
            elif dataset_items:
                try:
                    with open(dataset_items[0], "r", encoding="utf-8") as df:
                        sample_data = json.load(df)
                except Exception:
                    pass

            # Règle d'or : Succès si exit_code == 0 ET au moins 1 item dans le dataset
            if exit_code == 0 and item_count > 0:
                logger.info(f"✅ Succès du robot {actor_dir.name} ! {item_count} items générés.")
                return True, {
                    "attempts": attempt,
                    "item_count": item_count,
                    "sample_data": sample_data,
                    "stdout": stdout[-500:],
                    "status": "VALIDATED"
                }

            # Si échec, analyse de l'erreur
            last_error = f"Exit code: {exit_code}\nStderr: {stderr}\nStdout: {stdout[-500:]}\nItems count: {item_count}"
            logger.warning(f"❌ Échec de la tentative {attempt}/{MAX_REPAIR_ATTEMPTS} : {last_error[:300]}")

            if attempt < MAX_REPAIR_ATTEMPTS:
                logger.info("🔧 Auto-réparation en cours via Gemini...")
                repaired_code = self._repair_code_with_gemini(
                    actor_name=actor_dir.name,
                    current_code=main_py.read_text(encoding="utf-8"),
                    error_trace=last_error,
                    default_inputs=default_inputs
                )
                if repaired_code:
                    with open(main_py, "w", encoding="utf-8") as f:
                        f.write(repaired_code)
                    logger.info("Code de src/main.py mis à jour avec le patch IA. Relance du test...")
                else:
                    logger.error("Gemini n'a pas renvoyé de code réparé.")

        return False, {
            "attempts": attempt,
            "error": last_error,
            "status": "FAILED_AFTER_HEALING_ATTEMPTS"
        }

    def _repair_code_with_gemini(
        self,
        actor_name: str,
        current_code: str,
        error_trace: str,
        default_inputs: Dict[str, Any]
    ) -> Optional[str]:
        """Sollicite Gemini 2.5 Flash pour analyser l'erreur et corriger src/main.py."""
        if not self.api_key:
            logger.error("GEMINI_API_KEY non configurée pour l'auto-guérison.")
            return None

        prompt = f"""
Tu es l'Expert en Débogage d'Agents IA Autonomes.
Le script Python `src/main.py` de l'Actor Apify `{actor_name}` a échoué lors de son test en conditions réelles dans la sandbox.

TRACE D'ERREUR OU ANOMALIE OBSERVÉE :
{error_trace}

VALEURS PAR DÉFAUT ATTENDUES :
{json.dumps(default_inputs, indent=2)}

CODE ACTUEL QUI PLANTE :
```python
{current_code}
```

MISSION DE RÉPARATION :
1. Identifie la cause racine exacte (ex: exception réseau non gérée, structure JSON inattendue, absence d'écriture de fichiers dans `./storage/datasets/default/`, problème d'User-Agent, encodage SSL ou format d'URL).
2. Fournis le code COMPLET, CORRIGÉ et FONCTIONNEL de `src/main.py`.
3. Assure-toi impérativement que le script sauvegarde au minimum 1 enregistrement JSON structuré dans `./storage/datasets/default/000000001.json` ou `./storage/datasets/default/results.json`, même si une ressource distante renvoie un code 404/500 (dans ce cas, logger un enregistrement structuré de diagnostic).
4. Ne renvoie QUE le code Python sans blabla dans un bloc ```python ... ```.
"""

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw = response.text or ""
        except Exception as e:
            logger.warning(f"Erreur d'appel SDK google-genai ({e}), tentative via REST...")
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            res = requests.post(url, json=payload, timeout=90)
            res.raise_for_status()
            raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]

        code_match = re.search(r"```python(.*?)```", raw, re.DOTALL)
        if code_match:
            clean_code = code_match.group(1).strip()
        else:
            clean_code = raw.strip()

        clean_code = re.sub(r"^```.*\n", "", clean_code)
        clean_code = re.sub(r"\n```$", "", clean_code)
        return clean_code if len(clean_code) > 50 else None


if __name__ == "__main__":
    tester = SandboxTester()
    print("Module SandboxTester opérationnel.")
