import os
import socket
from fastapi import FastAPI
import docker
try:
    import config
except ImportError:
    from src import config

app = FastAPI()

@app.get("/")
async def root():
    """
    Sonde basique de disponibilité (Healthcheck).
    """
    return {"hello": "world"}

def run_vectorization_pipeline(action: str) -> dict:
    """
    Lance le pipeline de vectorisation (init ou update) dans des conteneurs Docker batch distincts
    via le socket Docker de l'hôte (DooD - Docker-out-of-Docker), un conteneur par modèle configuré
    (allMin, distiluse, e5-large).
    Les paramètres (typologie, concepts/chaînes, CSV) sont extraits directement
    de la configuration applicative afin de prévenir toute injection de commande.

    :param action: Action à exécuter ('init' ou 'update').
    :return: Dictionnaire contenant le statut et les détails d'exécution de chaque conteneur.
    """
    concepts_or_chains = config.VECTORIZE_CONCEPTS_OR_CHAINS
    avec_these = config.VECTORIZE_AVEC_THESE
    csv_filename = config.CSV_INIT_FILENAME if action == "init" else config.CSV_UPDATE_FILENAME
    models_to_run = getattr(config, "MODELS", ["allMin", "distiluse", "e5-large"])

    print(f"Lancement de la vectorisation conteneurisée (action={action}) pour les modèles: {models_to_run}")

    try:
        client = docker.DockerClient(base_url=config.DOCKER_SOCK)
        device_requests = [docker.types.DeviceRequest(device_ids=['0'], capabilities=[['gpu']])] if config.ENABLE_GPU else None

        # Détection automatique du chemin de volume hôte monté sur /app/data
        volume_bind = None
        if os.path.exists("/.dockerenv"):
            try:
                hostname = socket.gethostname()
                try:
                    current_container = client.containers.get(hostname)
                except Exception:
                    current_container = client.containers.get("iar-vectorisation")

                for mount in current_container.attrs.get("Mounts", []):
                    if mount.get("Destination") == "/app/data":
                        volume_bind = mount.get("Source")
                        print(f"Volume hôte détecté depuis le conteneur parent : {volume_bind} -> /app/data")
                        break
            except Exception as vol_err:
                print(f"Impossible de détecter le volume hôte automatiquement : {vol_err}")

        if not volume_bind:
            volume_bind = os.path.abspath(config.DOCKER_VOLUME_BIND)

        # Transmission des variables d'environnement au conteneur batch
        batch_env = {
            "QDRANT_HOST": config.QDRANT_HOST,
            "QDRANT_PORT": str(config.QDRANT_PORT),
            "QDRANT_TEST_LIMIT": str(getattr(config, "QDRANT_TEST_LIMIT", 6)),
            "QDRANT_MIN_VECTORS": str(getattr(config, "QDRANT_MIN_VECTORS", 1000)),
            "APP_DATA_DIR": config.APP_DATA_DIR,
            "CSV_DIR": config.CSV_DIR,
            "PKL_DIR": config.PKL_DIR,
            "CSV_INIT_FILENAME": config.CSV_INIT_FILENAME,
            "CSV_UPDATE_FILENAME": config.CSV_UPDATE_FILENAME,
            "VECTORIZE_CONCEPTS_OR_CHAINS": config.VECTORIZE_CONCEPTS_OR_CHAINS,
            "VECTORIZE_AVEC_THESE": config.VECTORIZE_AVEC_THESE,
        }

        launched_containers = []
        for model in models_to_run:
            command_args = [
                "python", "rameau_vectorize.py",
                "--action", action,
                "--conceptsORchains", concepts_or_chains,
                "--alias_model", model,
                "--avec_these", avec_these,
                "--csv_filename", csv_filename
            ]

            run_kwargs = {
                "network": config.DOCKER_NETWORK,
                "environment": batch_env,
                "command": command_args,
                "volumes": {
                    volume_bind: {
                        "bind": "/app/data",
                        "mode": "rw",
                    }
                },
                "detach": True
            }
            if device_requests:
                run_kwargs["device_requests"] = device_requests

            try:
                container = client.containers.run(config.DOCKER_IMAGE_BATCH, **run_kwargs)
            except Exception as launch_err:
                # En cas d'échec lié au runtime GPU (ex: WSL sans adaptateur GPU NVIDIA), repli automatique en mode CPU
                err_str = str(launch_err).lower()
                if device_requests and any(k in err_str for k in ("gpu", "nvidia", "adapters were found", "device_requests")):
                    print(f"Échec d'allocation GPU pour {model} ({launch_err}). Repli automatique sur l'exécution en mode CPU...")
                    run_kwargs.pop("device_requests", None)
                    container = client.containers.run(config.DOCKER_IMAGE_BATCH, **run_kwargs)
                else:
                    raise launch_err

            print(f"Conteneur batch lancé pour le modèle '{model}' : ID={container.short_id}")
            launched_containers.append({
                "model": model,
                "container_id": container.short_id,
                "command": command_args
            })

        return {
            "status": "success",
            "message": f"{len(launched_containers)} conteneurs batch lancés avec succès ({action})",
            "containers": launched_containers
        }
    except Exception as e:
        print(f"Erreur lors du lancement Docker: {e}")
        return {
            "status": "error",
            "message": f"Impossible de contacter le démon Docker: {str(e)}"
        }


@app.post("/init")
@app.get("/init")
async def init_vectorization():
    """
    Route dédiée pour lancer une initialisation complète du corpus vectoriel RAMEAU.
    Les paramètres sont issus de la configuration (config.py / .env).
    """
    return run_vectorization_pipeline("init")


@app.post("/update")
@app.get("/update")
async def update_vectorization():
    """
    Route dédiée pour lancer une mise à jour différentielle du corpus vectoriel RAMEAU.
    Les paramètres sont issus de la configuration (config.py / .env).
    """
    return run_vectorization_pipeline("update")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("load_qdrant_ws:app", host=config.API_HOST, port=config.API_PORT, workers=1)