# 📘 Guide d'Installation Rapide en 5 Minutes - Usine à Robots Apify

Bienvenue dans l'**Usine à Robots Apify Autonome** (`apify-autonomous-factory-brain`).  
Ce guide vous montre pas à pas comment configurer votre usine pour qu'elle conçoive, code, teste, répare et publie automatiquement un nouvel Actor B2B chaque semaine sur votre compte Apify, **sans engager 1 seul centime (0 € de frais, aucune carte bancaire requise)**.

---

## ⏱️ Sommaire des 5 étapes
1. [Étape 1 : Récupérer votre `APIFY_API_TOKEN` gratuit](#-étape-1--récupérer-votre-apify_api_token-gratuit)
2. [Étape 2 : Obtenir votre clé `GEMINI_API_KEY` gratuite](#-étape-2--obtenir-votre-clé-gemini_api_key-gratuite)
3. [Étape 3 : Configurer les Secrets GitHub](#-étape-3--configurer-les-secrets-github)
4. [Étape 4 : Configurer votre IBAN français pour les Payouts SEPA](#-étape-4--configurer-votre-iban-français-pour-les-payouts-sepa)
5. [Étape 5 : Activer la Monétisation en 1 Clic sur Apify Store](#-étape-5--activer-la-monétisation-en-1-clic-sur-apify-store)

---

## 🔑 Étape 1 : Récupérer votre `APIFY_API_TOKEN` gratuit

Apify offre **5,00 $ de crédits gratuits chaque mois** à chaque compte. L'Usine est calibrée pour consommer moins de **0,80 $/mois** (soit seulement 16% du quota offert).

1. Rendez-vous sur la console Apify : **[https://console.apify.com/](https://console.apify.com/)**
2. Connectez-vous ou créez un compte gratuit (par GitHub ou email).
3. Cliquez sur votre avatar en haut à droite > **Settings** (Paramètres).
4. Allez dans l'onglet **Integrations** (ou directement : [https://console.apify.com/account/integrations](https://console.apify.com/account/integrations)).
5. Sous la section **Personal API tokens**, cliquez sur **Add token** (ou copiez votre token existant).
6. Nommez-le `factory-brain-token` et copiez la valeur (commence par `apify_api_...`).

---

## 🧠 Étape 2 : Obtenir votre clé `GEMINI_API_KEY` gratuite

L'intelligence du Cerveau (idéation, écriture du code Python et auto-guérison) repose sur le modèle de pointe **Gemini 2.5 Flash**.

1. Rendez-vous sur Google AI Studio : **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**
2. Connectez-vous avec votre compte Google.
3. Cliquez sur **Create API key** (Créer une clé API).
4. Copiez votre clé (commence par `AIzaSy...`). Le niveau d'utilisation standard est 100% gratuit.

---

## ⚙️ Étape 3 : Configurer les Secrets GitHub

Pour que l'Usine fonctionne en pilote automatique chaque mercredi sans que votre ordinateur n'ait besoin d'être allumé :

1. Ouvrez votre dépôt GitHub (ex: `https://github.com/votre-nom/apify-autonomous-factory-brain`).
2. Cliquez sur **Settings** (du dépôt) > **Secrets and variables** > **Actions**.
3. Cliquez sur le bouton vert **New repository secret** et ajoutez :
   - Nom : `APIFY_API_TOKEN` | Valeur : Votre token Apify (`apify_api_...`)
   - Nom : `GEMINI_API_KEY` | Valeur : Votre clé Gemini (`AIzaSy...`)
4. Cliquez sur **Settings** > **Actions** > **General** > faites défiler jusqu'à **Workflow permissions** :
   - Cochez **Read and write permissions** (nécessaire pour que l'usine pousse les nouvelles branches `actor/*` et mette à jour le registre).
   - Cliquez sur **Save**.

---

## 🏦 Étape 4 : Configurer votre IBAN français pour les Payouts SEPA

Lorsque les utilisateurs d'Apify louent vos robots, Apify collecte les paiements par carte bancaire internationale et vous reverse vos gains nets directement par virement bancaire SEPA chaque mois.

1. Rendez-vous dans la section monétisation d'Apify : **[https://console.apify.com/billing/payouts](https://console.apify.com/billing/payouts)**
2. Cliquez sur **Set up payout method** (ou **Add Bank Account**).
3. Renseignez :
   - **Type de compte** : Entreprise ou Particulier / Auto-Entrepreneur.
   - **Pays de la banque** : `France` (ou votre pays de résidence SEPA).
   - **IBAN** : Votre IBAN français (commençant par `FR76...`).
   - **BIC / SWIFT** : Le code BIC de votre banque.
   - **Adresse fiscale** : Votre adresse légale en France.
4. Les virements mensuels d'Apify proviennent de leur entité européenne officielle :
   > **Apify Technologies s.r.o.**  
   > Vodičkova 704/36, 110 00 Prague 1, République Tchèque  
   > Numéro de TVA intra-UE : `CZ04787261`

---

## 💰 Étape 5 : Activer la Monétisation en 1 Clic sur Apify Store

Dès qu'un robot est déployé par l'Usine :

1. Allez sur **[https://console.apify.com/actors](https://console.apify.com/actors)**.
2. Cliquez sur l'Actor créé (ex : `shopify-fast-catalog-products-json`).
3. Allez dans l'onglet **Publication** (ou **Monetization**).
4. Choisissez le modèle économique recommandé :
   - **Rental (Location Mensuelle)** : Définissez le prix mensuel suggéré par le Cerveau (ex: **19,00 $ / mois**, **29,00 $ / mois** ou **39,00 $ / mois**).
   - Ou **Pay Per Result** : Facturation au volume d'enregistrements (ex: 0,001 $ / item).
5. Cliquez sur **Make public on Apify Store**.
6. Votre robot est désormais visible par les 250 000+ développeurs et agences Make/n8n qui utilisent Apify !

---

## 📋 Déclaration Fiscale Automatisée (Micro-BNC France)

L'Usine met à jour en continu vos documents comptables légaux :
- `compta_impots/livre_recettes_officiel.csv` : Livre des recettes chronologique obligatoire conforme à l'article 286 du CGI.
- `compta_impots/rapport_fiscal_micro_bnc.json` : Tableau de bord fiscal pour votre déclaration de revenus.

### Report sur votre déclaration d'impôt (Formulaire 2042-C-PRO) :
- **Case `5HQ`** : Indiquez le montant brut total figurant dans `rapport_fiscal_micro_bnc.json`. Le fisc appliquera automatiquement l'abattement forfaitaire de **34%**.
- **Case `5TE`** : À remplir uniquement si vous avez opté pour le versement libératoire de l'IR (taux de 2,2%).
- **TVA** : Facturation en franchise de TVA (art. 293 B du CGI) ou autoliquidation B2B intra-UE (Directive 2006/112/CE). Déposer une déclaration européenne de services (DES) sur le portail des douanes.

---

## 🚀 Lancer votre premier robot dès maintenant !

Pour déclencher immédiatement la création d'un premier robot sans attendre le cron du mercredi :
1. Sur votre dépôt GitHub, allez dans l'onglet **Actions**.
2. Cliquez sur le workflow **Apify Factory Autopilot** dans la barre latérale gauche.
3. Cliquez sur **Run workflow** > bouton vert **Run workflow**.
4. Suivez l'exécution en temps réel : Idéation -> Génération -> Test Sandbox -> Auto-réparation -> Publication !
