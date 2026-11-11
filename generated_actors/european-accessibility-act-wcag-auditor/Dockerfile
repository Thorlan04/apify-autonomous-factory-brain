# Dockerfile standard Apify Python optimisé
FROM python:3.11-slim

# Configuration d'environnement Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /usr/src/app

# Installation des dépendances
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . ./

# Commande d'exécution officielle Apify
CMD ["python3", "-m", "src.main"]
