# ⚙️ Service de Vectorisation & Ingestion Qdrant RAMEAU

Ce module constitue le pipeline de **vectorisation batch et d'ingestion vectorielle** pour le projet RAMEAU de l'ABES. Il prend en entrée des exports de notices bibliographiques (RAMEAU), calcule les représentations vectorielles (_embeddings_) via des modèles de Transformers, effectue des agrégations par moyenne de vecteurs sur les vedettes-matières, et alimente la base de données vectorielle **Qdrant**.

---

## 📌 Sommaire

- [Vue d'ensemble & Architecture](#-vue-densemble--architecture)
- [Fonctionnalités Principales](#-fonctionnalités-principales)
- [Description des Scripts](#-description-des-scripts)
- [Ajustements Sécurité & Corrections Appliquées](#-ajustements-sécurité--corrections-appliquées)
- [Endpoints du Web Service REST (`load_qdrant_ws.py`)](#-endpoints-du-web-service-rest)
- [Pipeline de Vectorisation Batch (`rameau_vectorize.py`)](#-pipeline-de-vectorisation-batch)
- [Installation & Déploiement](#-installation--déploiement)
- [Lancement en Local de Python (Linux, Windows, Git Bash, PowerShell)](#-lancement-en-local-de-python-linux-windows-git-bash-powershell)
- [Lancement en Local avec Docker (Linux, Windows, Git Bash, PowerShell)](#-lancement-en-local-avec-docker-linux-windows-git-bash-powershell)
- [Tests & Évaluation](#-tests--évaluation)

---

## 🏗 Vue d'ensemble & Architecture

Le composant de vectorisation orchestre le traitement par lots volumineux de notices bibliographiques.

```
┌─────────────────────────────────────────────────────────────┐
│             Export RAMEAU (CSV/TSV Tabulé)                  │
│       (export_rameau.csv / export_rameau_update.csv)        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Orchestrateur FastAPI                       │
│                 (`load_qdrant_ws.py`)                       │
└──────────────────────────────┬──────────────────────────────┘
                               │ Execution Local / Docker GPU
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Calculateur d'Embeddings Batch                  │
│                (`rameau_vectorize.py`)                      │
│   • Encodage par mini-lots (SentenceTransformers)           │
│   • Explosion des chaînes / concepts RAMEAU                 │
│   • Agrégation vectorielle par moyenne (NumPy/Pandas)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Base Vectorielle Qdrant (INT8)                  │
│           Collection RAMEAU (Port 6333)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Fonctionnalités Principales

1. **Calcul par Lots Optimisé (Batching) :** Traitement des corpus par lots de 5 000 notices pour maximiser le rendement mémoire et GPU sans risque de dépassement de RAM.
2. **Support Multi-modèles :**
   - `allMin` : `all-MiniLM-L6-v2`
   - `distiluse` : `distiluse-base-multilingual-cased-v2`
   - `e5-large` : `intfloat/multilingual-e5-large`
3. **Agrégation de Vecteurs par Concept :** Pour une vedette RAMEAU donnée, les vecteurs de tous les documents associés sont regroupés et moyennés pour créer l'empreinte vectorielle unique de la vedette.
4. **Alimentation Qdrant avec Quantification INT8 :** Ingestion optimisée dans Qdrant avec quantification scalaire (`INT8`) maintenue en RAM pour une vitesse de recherche maximale.
5. **Orchestration Hybride (Host / Conteneur Docker GPU) :** Détection automatique de l'environnement d'exécution (`is_docker()`) et lancement de conteneurs Docker éphémères munis du passthrough GPU si nécessaire.

---

## 📄 Description des Scripts

| Fichier                   | Rôle                                                                                                                     |
| :------------------------ | :----------------------------------------------------------------------------------------------------------------------- |
| **`load_qdrant_ws.py`**   | Web service REST FastAPI (Port `8100`) servant d'API d'orchestration pour lancer les tâches de vectorisation.            |
| **`rameau_vectorize.py`** | Script Batch / CLI qui effectue le nettoyage des CSV, le calcul des embeddings, l'agrégation et l'ingestion dans Qdrant. |

---

## 📡 Endpoints du Web Service REST (`load_qdrant_ws.py`)

### 1. `POST /init` ou `GET /init`

Déclenche l'initialisation complète du corpus vectoriel RAMEAU.  
Pour des raisons de sécurité, les paramètres (`conceptsORchains`, `avec_these`, noms des CSV) sont directement configurés dans [.env](file:///c:/Projets/iar/iar-vectorisation/.env). Le webservice lance automatiquement 3 conteneurs batch en parallèle, un pour chaque modèle supporté (`allMin`, `distiluse`, `e5-large`).

```bash
curl -X POST "http://localhost:8100/init"
```

### 2. `POST /update` ou `GET /update`

Déclenche la mise à jour différentielle du corpus vectoriel RAMEAU à partir de la configuration applicative.

```bash
curl -X POST "http://localhost:8100/update"
```

### 3. `POST /init/upload`

Permet d'uploader le fichier CSV d'initialisation. Le fichier est automatiquement conformé sous le nom attendu par l'initialisation (`export_rameau.csv` ou configuré via `IAR_CSV_INIT_FILENAME`) et écrase le fichier précédent dans `/app/data/csv`.

```bash
curl -X POST -F "file=@mon_export.csv" "http://localhost:8100/init/upload"
```

### 4. `POST /update/upload`

Permet d'uploader le fichier CSV de mise à jour différentielle. Le fichier est automatiquement conformé sous le nom attendu par la mise à jour (`export_rameau_update.csv` ou configuré via `IAR_CSV_UPDATE_FILENAME`) et écrase le fichier précédent dans `/app/data/csv`.

```bash
curl -X POST -F "file=@mon_delta.csv" "http://localhost:8100/update/upload"
```

---

## 💻 Pipeline de Vectorisation Batch (`rameau_vectorize.py`)

Le script CLI s'exécute directement en ligne de commande :

```bash
python rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
```

### Options CLI :

- `--action` / `-a` : `init` (recharge tout), `update` (mise à jour différentielle), `auto` (détection selon la date des fichiers), `restore` (ré-ingestion dans Qdrant depuis l'archive `.pkl`).
- `--conceptsORchains` / `-c` : `concepts` ou `chains`.
- `--alias_model` / `-m` : `allMin`, `distiluse`, `e5-large`.
- `--avec_these` / `-t` : `only_mono`, `only_theses`, `with_theses`.

---

## 📦 Installation & Déploiement

### 1. Prérequis

- Python 3.10+
- GPU NVIDIA recommandé (avec drivers CUDA) pour l'accélération `SentenceTransformer`.
- Docker Engine (si exécution conteneurisée).

### 2. Installation via `requirements.txt`

Cloner le dépôt et installer les dépendances Python spécifiées dans le fichier `requirements.txt` :

```bash
# Création d'un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Sur Linux/macOS
# venv/Scripts/activate  # Sur Windows

# Installation des paquets
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Lancement du service d'orchestration

```bash
python -m uvicorn load_qdrant_ws:app --host 0.0.0.0 --port 8100
```

### 4. Déploiement Conteneurisé (Docker)

Le projet peut être entièrement exécuté sous forme de conteneurs Docker (Web Service FastAPI, instance vectorielle Qdrant et conteneurs batch éphémères).  
👉 Pour le détail complet des commandes selon votre terminal (Linux, Windows PowerShell, Git Bash, CMD), consultez la section dédiée : **[Lancement en Local avec Docker](#-lancement-en-local-avec-docker-linux-windows-git-bash-powershell)**.

---

## 🚀 Lancement en Local de Python (Linux, Windows, Git Bash, PowerShell)

Pour exécuter le projet localement sans passer par Docker, créez un environnement virtuel Python (`venv`) puis activez-le selon votre système d'exploitation et votre shell :

### 🐧 1. Linux & macOS (Bash / Zsh)

```bash
# 1. Création de l'environnement virtuel
python3 -m venv venv

# 2. Activation de l'environnement virtuel
source venv/bin/activate

# 3. Installation des dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Lancement du Web Service (FastAPI)
python -m uvicorn src.load_qdrant_ws:app --host 0.0.0.0 --port 8100 --reload

# 5. Ou exécution du script batch de vectorisation
python src/rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
```

---

### 💻 2. Windows — PowerShell

> [!TIP]
> Si l'exécution de scripts PowerShell est bloquée par la stratégie de sécurité Windows (`ExecutionPolicy`), autorisez-la temporairement pour la session en cours avec :  
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`

```powershell
# 1. Création de l'environnement virtuel
python -m venv venv

# 2. Activation de l'environnement virtuel
.\venv\Scripts\Activate.ps1

# 3. Installation des dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Lancement du Web Service (FastAPI)
python -m uvicorn src.load_qdrant_ws:app --host 0.0.0.0 --port 8100 --reload

# 5. Ou exécution du script batch de vectorisation
python src\rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
```

---

### 🪟 3. Windows — Git Bash

> [!NOTE]
> Sous Git Bash sur Windows, le dossier contenant les binaires Python du `venv` est `Scripts` (et non `bin`).

```bash
# 1. Création de l'environnement virtuel
python -m venv venv

# 2. Activation de l'environnement virtuel
source venv/Scripts/activate

# 3. Installation des dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Lancement du Web Service (FastAPI)
python -m uvicorn src.load_qdrant_ws:app --host 0.0.0.0 --port 8100 --reload

# 5. Ou exécution du script batch de vectorisation
python src/rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
```

---

### 🔲 4. Windows — Invite de commandes (CMD)

```cmd
:: 1. Création de l'environnement virtuel
python -m venv venv

:: 2. Activation de l'environnement virtuel
venv\Scripts\activate.bat

:: 3. Installation des dépendances
pip install --upgrade pip
pip install -r requirements.txt

:: 4. Lancement du Web Service (FastAPI)
python -m uvicorn src.load_qdrant_ws:app --host 0.0.0.0 --port 8100 --reload

:: 5. Ou exécution du script batch de vectorisation
python src\rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
```

---

### ⚡ Astuce : Exécution directe sans activation

Si vous préférez ne pas activer le `venv` dans votre invite de commandes, vous pouvez appeler directement son exécutable Python :

- **Linux / macOS :**
  ```bash
  ./venv/bin/python -m pip install -r requirements.txt
  ./venv/bin/python -m uvicorn src.load_qdrant_ws:app --port 8100
  ```
- **Windows (PowerShell, CMD, Git Bash) :**
  ```bash
  ./venv/Scripts/python -m pip install -r requirements.txt
  ./venv/Scripts/python -m uvicorn src.load_qdrant_ws:app --port 8100
  ```

---

## 🐳 Lancement en Local avec Docker (Linux, Windows, Git Bash, PowerShell)

L'exécution avec Docker isole entièrement l'environnement, simplifie l'accès GPU et assure la communication avec la base vectorielle **Qdrant**.

### 1. Création du réseau Docker & Démarrage de Qdrant

Les conteneurs communiquent via un réseau Docker partagé (défini par `DOCKER_NETWORK=mon_reseau` dans [.env](file:///c:/Projets/iar/iar-vectorisation/.env)) :

```bash
# Créer le réseau Docker partagé s'il n'existe pas encore
docker network create mon_reseau
```

Lancer une instance locale de **Qdrant** sur ce réseau :

- **Linux / macOS & Git Bash :**

  ```bash
  docker run -d --name qdrant \
    --network mon_reseau \
    -p 6333:6333 \
    -v "$(pwd)/volumes/qdrant_storage":/qdrant/storage \
    qdrant/qdrant
  ```

- **Windows — PowerShell :**

  ```powershell
  docker run -d `
    --name qdrant `
    --network mon_reseau `
    -p 6333:6333 `
    -v ${PWD}/volumes/qdrant/storage:/qdrant/storage `
    qdrant/qdrant
  ```

- **Windows — Invite de commandes (CMD) :**
  ```cmd
  docker run -d ^
    --name qdrant ^
    --network mon_reseau ^
    -p 6333:6333 ^
    -v "%cd%/volumes/qdrant_storage":/qdrant/storage ^
    qdrant/qdrant
  ```

---

### 2. Construction des Images Docker

Construisez l'image principale et appliquez le tag requis pour les sous-tâches de vectorisation batch :

```bash
# Construction de l'image de base
docker build -t iar-vectorisation .

# Tag nécessaire pour les conteneurs éphémères déclenchés par le Web Service
docker tag iar-vectorisation rameau_vectorize_batch:latest
```

---

### 3. Lancement du Web Service d'orchestration (`load_qdrant_ws.py`)

Le Web Service FastAPI écoute sur le port `8100` et monte le socket Docker de l'hôte afin de pouvoir instancier les conteneurs de vectorisation à la demande (architecture Docker-out-of-Docker) :

#### 🐧 Linux & macOS (Bash / Zsh)

```bash
docker run -d \
  --name iar-vectorisation \
  --user root \
  --network mon_reseau \
  -p 8100:8100 \
  --env-file .env \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)/volumes":/app/data \
  iar-vectorisation
```

#### 💻 Windows — PowerShell

```powershell
docker run -d `
  --name iar-vectorisation `
  --user root `
  --network mon_reseau `
  -p 8100:8100 `
  --env-file .env `
  -v //var/run/docker.sock:/var/run/docker.sock `
  -v ${PWD}/volumes:/app/data `
  iar-vectorisation
```

#### 🪟 Windows — Git Bash

```bash
docker run -d \
  --name iar-vectorisation \
  --user root \
  --network mon_reseau \
  -p 8100:8100 \
  --env-file .env \
  -v //var/run/docker.sock:/var/run/docker.sock \
  -v "${PWD}/volumes":/app/data \
  iar-vectorisation
```

#### 🔲 Windows — Invite de commandes (CMD)

```cmd
docker run -d ^
  --name iar-vectorisation ^
  --user root ^
  --network mon_reseau ^
  -p 8100:8100 ^
  --env-file .env ^
  -v //var/run/docker.sock:/var/run/docker.sock ^
  -v "%cd%/volumes":/app/data ^
  iar-vectorisation
```

> [!IMPORTANT]
>
> - **Dossier des données :** Vos fichiers CSV d'entrée (`export_rameau.csv`, etc.) doivent être placés dans `./volumes/csv/` sur l'hôte, ce qui correspond à `/app/data/csv/` dans le conteneur.
> - **Configuration Qdrant :** Si le Web Service tourne dans Docker, réglez `QDRANT_HOST=qdrant` dans votre fichier `.env` (nom du conteneur sur le réseau `mon_reseau`).

---

### 4. Exécution ponctuelle directe du Batch (`rameau_vectorize.py`) via Docker

Pour exécuter la vectorisation ponctuellement sans démarrer le serveur d'API (lancement direct en ligne de commande dans un conteneur éphémère `--rm`) :

- **Avec accélération GPU NVIDIA (recommandé si supporté par l'hôte) :**

  ```bash
  docker run --rm -it \
    --network mon_reseau \
    --gpus all \
    -v "$(pwd)/volumes":/app/data \
    iar-vectorisation \
    python rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
  ```

- **Sans GPU (exécution CPU uniquement) :**
  ```bash
  docker run --rm -it \
    --network mon_reseau \
    -v "$(pwd)/volumes":/app/data \
    iar-vectorisation \
    python rameau_vectorize.py --action init --conceptsORchains concepts --alias_model allMin --avec_these only_mono
  ```

_(Sous PowerShell, remplacez `$(pwd)` par `${PWD}` ; sous CMD, par `%cd%` ; sous Git Bash, par `/$(pwd -W)`)_

---

### 5. Commandes de gestion utiles

```bash
# Visualiser les logs du Web Service en direct
docker logs -f iar-vectorisation

# Ouvrir un terminal interactif dans le conteneur
docker exec -it iar-vectorisation bash

# Arrêter et supprimer le conteneur
docker stop iar-vectorisation && docker rm iar-vectorisation
```

---

## 🧪 Tests & Évaluation

Le dossier [test/](test/) contient les scripts de validation technique de l'environnement de vectorisation.

### 1. Script de Vérification Pré-Vol (`test_preflight_checks.py`)

Ce script s'assure que la machine dispose des prérequis matériels nécessaires (mémoire RAM disponible) et valide la cohérence des arguments passés en ligne de commande pour le pipeline de vectorisation batch (`rameau_vectorize.py`). Il évite les plantages système en plein milieu d'une exécution de vectorisation lourde.

**Exécution :**

```bash
python test/test_preflight_checks.py --action update --conceptsORchains concepts --alias_model allMin --avec_these only_mono
```

### 2. Données de Test (`test/data/`)

- [test_data.csv](test/data/test_data.csv) : Fichier de référence contenant la liste de PPN exclus de l'entraînement (et donc du calcul de la moyenne vectorielle par concept). Il garantit que le pipeline d'ingestion n'introduit aucun biais sur l'ensemble d'évaluation (pas de _data leakage_).
