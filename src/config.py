import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

APP_DATA_DIR = os.getenv("APP_DATA_DIR", "./data")
DOCKER_VOLUME_BIND = os.getenv("DOCKER_VOLUME_BIND", "./volumes")
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "mon_reseau")
DOCKER_IMAGE_BATCH = os.getenv("DOCKER_IMAGE_BATCH", "rameau_vectorize_batch:latest")
DOCKER_SOCK = os.getenv("DOCKER_SOCK", "unix:///var/run/docker.sock")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8100"))
