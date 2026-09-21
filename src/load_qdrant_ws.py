from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import os
from pathlib import Path
import docker
try:
    import config
except ImportError:
    from src import config

app = FastAPI()

@app.get("/")
async def root():
    return {"hello": "world"}
    
@app.get("/log")
async def download_file(action: str, conceptsORchains: str, alias_model: str, avec_these: str):
    file_path = 'log_'+action + '_'+conceptsORchains + '_'+alias_model + '_'+avec_these +'.txt'
    safe_path = os.path.join(config.APP_DATA_DIR, os.path.basename(file_path))
    if not os.path.exists(safe_path):
        if os.path.exists(file_path)==False:
            print("le fichier : "+file_path+"  n existe pas pour ces parametres")
            return "le fichier : "+file_path+"  n existe pas pour ces parametres"
    else:
        file_path = safe_path
    return FileResponse(file_path)

def is_docker():
    cwd = str(Path.cwd())
    print(cwd)
    if "/app" in cwd :
        return True
    else:
        return False

@app.get("/lanceVectorisation/")
async def lanceVectorisation(action: str, conceptsORchains: str, alias_model: str, avec_these: str):
    message="ok"
    if action not in ['init','update','auto','restore']:
        message='action doit avoir :init, update ou auto ou restore'
        
    if conceptsORchains not in ['concepts','chains']:
        message='conceptsORchains doit avoir :concepts ou chains'
         
    if alias_model not in ['allMin','distiluse','e5-large']:
        message='alias_model doit avoir :allMin, distiluse ou e5-large'
        
    if avec_these not in ['only_mono','only_theses','with_theses']:
        message='avec_these doit avoir :only_mono, only_theses ou with_theses'
        
    print(message)
    if message!='ok':
        print(message)
        return {message : ""}
    print("lance La commande:")
    
    if is_docker():
        print("1 Le programme est exécuté dans un conteneur Docker.")
        commande=['--action', action,'--conceptsORchains', conceptsORchains,'--alias_model', alias_model,'--avec_these', avec_these]

        client = docker.DockerClient(base_url=config.DOCKER_SOCK)
        
        container = client.containers.run(
            config.DOCKER_IMAGE_BATCH,
            network=config.DOCKER_NETWORK,
            device_requests=[docker.types.DeviceRequest(device_ids=['0'], capabilities=[['gpu']])], 
            command=commande,
            volumes={
                config.DOCKER_VOLUME_BIND: {
                    "bind": "/app",
                    "mode": "rw",
                }
            },
            detach=True
        )
        return {"La commande docker a été lancée" : str(commande)}
    else:
        print("1 Le programme n'est pas exécuté dans un conteneur Docker.")
        commande ='python rameau_vectorize.py --action '+action+' --conceptsORchains '+conceptsORchains+' --alias_model '+alias_model+' --avec_these '+avec_these 
        print (commande)
        return {"La commande a été lancée" : commande}

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    contents = file.file.read()
    os.makedirs(config.APP_DATA_DIR, exist_ok=True)
    with open(os.path.join(config.APP_DATA_DIR, os.path.basename(file.filename).replace(' ','_')), 'wb') as f:
        f.write(contents)
    return {"ok pour filename": file.filename}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("load_qdrant_ws:app", host=config.API_HOST, port=config.API_PORT, workers=1)