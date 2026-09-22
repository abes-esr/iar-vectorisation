import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_TEST_LIMIT = int(os.getenv("QDRANT_TEST_LIMIT", "6"))
QDRANT_MIN_VECTORS = int(os.getenv("QDRANT_MIN_VECTORS", "1000"))

APP_DATA_DIR = os.getenv("APP_DATA_DIR", "/app/data")
DOCKER_VOLUME_BIND = os.getenv("DOCKER_VOLUME_BIND", "./volumes")
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "mon_reseau")
DOCKER_IMAGE_BATCH = os.getenv("DOCKER_IMAGE_BATCH", "rameau_vectorize_batch:latest")
DOCKER_SOCK = os.getenv("DOCKER_SOCK", "unix:///var/run/docker.sock")

# Configuration des fichiers CSV d'ingestion RAMEAU
CSV_INIT_FILENAME = os.getenv("CSV_INIT_FILENAME", "export_rameau.csv")
CSV_UPDATE_FILENAME = os.getenv("CSV_UPDATE_FILENAME", "export_rameau_update.csv")
CSV_DIR = os.getenv("CSV_DIR", os.path.join(APP_DATA_DIR, "csv"))
PKL_DIR = os.getenv("PKL_DIR", os.path.join(APP_DATA_DIR, "pkl"))

# Paramètres par défaut pour les pipelines de vectorisation (/init et /update)
VECTORIZE_CONCEPTS_OR_CHAINS = os.getenv("VECTORIZE_CONCEPTS_OR_CHAINS", "concepts")
VECTORIZE_ALIAS_MODEL = os.getenv("VECTORIZE_ALIAS_MODEL", "allMin")
VECTORIZE_AVEC_THESE = os.getenv("VECTORIZE_AVEC_THESE", "only_mono")

# Accélération GPU pour les conteneurs batch (désactivée par défaut pour compatibilité locale)
ENABLE_GPU = os.getenv("ENABLE_GPU", "false").lower() in ("true", "1", "yes")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8100"))
