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
    Lance le pipeline de vectorisation (init ou update) dans un conteneur Docker batch
    via le socket Docker de l'hôte (DooD - Docker-out-of-Docker).
    Les paramètres (modèle, typologie, concepts/chaînes, CSV) sont extraits directement
    de la configuration applicative afin de prévenir toute injection de commande.

    :param action: Action à exécuter ('init' ou 'update').
    :return: Dictionnaire contenant le statut et les détails d'exécution.
    """
    concepts_or_chains = config.VECTORIZE_CONCEPTS_OR_CHAINS
    alias_model = config.VECTORIZE_ALIAS_MODEL
    avec_these = config.VECTORIZE_AVEC_THESE
    csv_filename = config.CSV_INIT_FILENAME if action == "init" else config.CSV_UPDATE_FILENAME

    # Construction de la liste d'arguments pour l'exécution du script de vectorisation
    command_args = [
        "python", "rameau_vectorize.py",
        "--action", action,
        "--conceptsORchains", concepts_or_chains,
        "--alias_model", alias_model,
        "--avec_these", avec_these,
        "--csv_filename", csv_filename
    ]

    print(f"Lancement de la vectorisation conteneurisée (action={action}) avec les options: {command_args}")

    try:
        client = docker.DockerClient(base_url=config.DOCKER_SOCK)
        device_requests = [docker.types.DeviceRequest(device_ids=['0'], capabilities=[['gpu']])] if config.ENABLE_GPU else None

        run_kwargs = {
            "network": config.DOCKER_NETWORK,
            "command": command_args,
            "volumes": {
                config.DOCKER_VOLUME_BIND: {
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
                print(f"Échec d'allocation GPU ({launch_err}). Repli automatique sur l'exécution en mode CPU...")
                run_kwargs.pop("device_requests", None)
                container = client.containers.run(config.DOCKER_IMAGE_BATCH, **run_kwargs)
            else:
                raise launch_err

        return {
            "status": "success",
            "message": f"Conteneur batch lancé avec succès ({action})",
            "container_id": container.short_id,
            "command": command_args
        }
    except Exception as e:
        print(f"Erreur lors du lancement Docker: {e}")
        return {
            "status": "error",
            "message": f"Impossible de contacter le démon Docker: {str(e)}",
            "command": command_args
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