import os
import docker
import aiofiles
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Response, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Orchestrateur Vectorisation RAMEAU")

DATA_DIR = os.getenv("APP_DATA_DIR", "./data")
DOCKER_VOLUME = os.getenv("DOCKER_VOLUME_BIND", "/app")


def is_docker() -> bool:
    cwd = str(Path.cwd())
    return "/app" in cwd


@app.get("/")
async def root():
    return {"status": "online", "service": "RAMEAU Vectorization Orchestrator"}


@app.get("/log")
async def download_file(action: str, conceptsORchains: str, alias_model: str, avec_these: str):
    file_path = f"log_{action}_{conceptsORchains}_{alias_model}_{avec_these}.txt"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Le fichier de log '{file_path}' n'existe pas.")
    return FileResponse(file_path)


@app.get("/lanceVectorisation/")
async def lanceVectorisation(action: str, conceptsORchains: str, alias_model: str, avec_these: str):
    if action not in ['init', 'update', 'auto', 'restore']:
        return JSONResponse(status_code=400, content={"error": "action doit être : init, update, auto ou restore"})

    if conceptsORchains not in ['concepts', 'chains']:
        return JSONResponse(status_code=400, content={"error": "conceptsORchains doit être : concepts ou chains"})

    if alias_model not in ['allMin', 'distiluse', 'e5-large']:
        return JSONResponse(status_code=400, content={"error": "alias_model doit être : allMin, distiluse ou e5-large"})

    if avec_these not in ['only_mono', 'only_theses', 'with_theses']:
        return JSONResponse(status_code=400, content={"error": "avec_these doit être : only_mono, only_theses ou with_theses"})

    if is_docker():
        print("Exécution dans un conteneur Docker.")
        commande = ['--action', action, '--conceptsORchains', conceptsORchains, '--alias_model', alias_model, '--avec_these', avec_these]

        client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        container = client.containers.run(
            "rameau_vectorize_batch:latest",
            network="mon_reseau",
            device_requests=[docker.types.DeviceRequest(device_ids=['0'], capabilities=[['gpu']])],
            command=commande,
            volumes={
                DOCKER_VOLUME: {
                    "bind": "/app",
                    "mode": "rw",
                }
            },
            detach=True
        )
        return {"status": "Docker container lancé", "container_id": container.id, "command": commande}
    else:
        print("Exécution en local (hors Docker).")
        import subprocess
        
        # Sécurisé : Liste d'arguments sans shell=True
        args = [
            "python3", "rameau_vectorize.py",
            "--action", action,
            "--conceptsORchains", conceptsORchains,
            "--alias_model", alias_model,
            "--avec_these", avec_these
        ]
        log_filename = f"log_{action}_{conceptsORchains}_{alias_model}_{avec_these}.txt"
        
        with open(log_filename, "w") as log_file:
            subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT)

        return {"status": "Commande locale lancée", "command": " ".join(args), "log_file": log_filename}


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    os.makedirs(DATA_DIR, exist_ok=True)
    clean_filename = file.filename.replace(' ', '_')
    target_path = os.path.join(DATA_DIR, clean_filename)

    contents = await file.read()
    async with aiofiles.open(target_path, 'wb') as f:
        await f.write(contents)

    return {"status": "Fichier sauvegardé avec succès", "filename": clean_filename, "path": target_path}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("load_qdrant_ws:app", host="0.0.0.0", port=8100, workers=1)