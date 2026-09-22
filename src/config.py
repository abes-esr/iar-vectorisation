import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("IAR_QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("IAR_QDRANT_PORT", "6333"))
QDRANT_TEST_LIMIT = int(os.getenv("IAR_QDRANT_TEST_LIMIT", "6"))
QDRANT_MIN_VECTORS = int(os.getenv("IAR_QDRANT_MIN_VECTORS", "1000"))

APP_DATA_DIR = os.getenv("IAR_APP_DATA_DIR", "/app/data")
DOCKER_VOLUME_BIND = os.getenv("IAR_DOCKER_VOLUME_BIND", "./volumes")
DOCKER_NETWORK = os.getenv("IAR_DOCKER_NETWORK", "mon_reseau")
DOCKER_IMAGE_BATCH = os.getenv("IAR_DOCKER_IMAGE_BATCH", "rameau_vectorize_batch:latest")
DOCKER_SOCK = os.getenv("IAR_DOCKER_SOCK", "unix:///var/run/docker.sock")
DOCKER_BATCH_USER = os.getenv("IAR_DOCKER_BATCH_USER", "root")

# Configuration des fichiers CSV d'ingestion RAMEAU
CSV_INIT_FILENAME = os.getenv("IAR_CSV_INIT_FILENAME", "export_rameau.csv")
CSV_UPDATE_FILENAME = os.getenv("IAR_CSV_UPDATE_FILENAME", "export_rameau_update.csv")
CSV_DIR = os.getenv("IAR_CSV_DIR", os.path.join(APP_DATA_DIR, "csv"))
PKL_DIR = os.getenv("IAR_PKL_DIR", os.path.join(APP_DATA_DIR, "pkl"))

# Paramètres par défaut pour les pipelines de vectorisation (/init et /update)
VECTORIZE_CONCEPTS_OR_CHAINS = os.getenv("IAR_VECTORIZE_CONCEPTS_OR_CHAINS", "concepts")
VECTORIZE_AVEC_THESE = os.getenv("IAR_VECTORIZE_AVEC_THESE", "only_mono")
MODELS = ["allMin", "distiluse", "e5-large"]

# Accélération GPU pour les conteneurs batch (désactivée par défaut pour compatibilité locale)
ENABLE_GPU = os.getenv("ENABLE_GPU", "false").lower() in ("true", "1", "yes")

API_HOST = os.getenv("IAR_VECTORISATION_HOST", "0.0.0.0")
API_PORT = int(os.getenv("IAR_VECTORISATION_PORT", "6381"))
