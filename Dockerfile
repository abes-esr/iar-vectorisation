# ==============================================================================
# Étape de Base (base)
# Image PyTorch avec support CUDA 12.6 / cuDNN 9 pour GPU Volta (ex: Tesla V100S)
FROM pytorch/pytorch:2.14.0-cuda12.6-cudnn9-devel AS base

# Empêcher la création de fichiers .pyc et activer la sortie immédiate des logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONPATH=/app:/app/src

WORKDIR /app

# Installation des dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Création du groupe docker et d'un utilisateur non-root pour la sécurité
RUN (groupadd -g 999 docker 2>/dev/null || groupadd docker) && \
    useradd -u 1000 -m -s /bin/bash appuser && \
    usermod -aG docker appuser && \
    mkdir -p /app/data /app/volumes && \
    chown -R appuser:appuser /app

# ==============================================================================
# Étape de Production (production / app)
# ==============================================================================
FROM base AS vectorisation-image

# Copie des sources de l'application
COPY --chown=appuser:appuser src/ /app/src/

# Pour faciliter l'exécution directe des scripts à la racine du conteneur
RUN ln -s /app/src/load_qdrant_ws.py /app/load_qdrant_ws.py && \
    ln -s /app/src/rameau_vectorize.py /app/rameau_vectorize.py && \
    ln -s /app/src/config.py /app/config.py

USER appuser

EXPOSE 8100

# Vérification de l'état de santé du service
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8100/ || exit 1

# Commande par défaut : lancement du web service FastAPI
CMD ["uvicorn", "load_qdrant_ws:app", "--host", "0.0.0.0", "--port", "8100"]
