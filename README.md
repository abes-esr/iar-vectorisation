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

| Fichier                   | Rôle                                                                                                                                              |
| :------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`load_qdrant_ws.py`**   | Web service REST FastAPI (Port `8100`) servant d'API d'orchestration pour lancer les tâches de vectorisation et télécharger les logs d'exécution. |
| **`rameau_vectorize.py`** | Script Batch / CLI qui effectue le nettoyage des CSV, le calcul des embeddings, l'agrégation et l'ingestion dans Qdrant.                          |

---

## 📡 Endpoints du Web Service REST (`load_qdrant_ws.py`)

### 1. `GET /lanceVectorisation/`

Déclenche une tâche de vectorisation en arrière-plan.

#### Paramètres :

- `action` (`str`) : Type de tâche (`init`, `update`, `auto`, `restore`).
- `conceptsORchains` (`str`) : Type de sujet (`concepts`, `chains`).
- `alias_model` (`str`) : Modèle (`allMin`, `distiluse`, `e5-large`).
- `avec_these` (`str`) : Périmètre (`only_mono`, `only_theses`, `with_theses`).

#### Exemple :

```bash
curl -X GET "http://localhost:8100/lanceVectorisation/?action=update&conceptsORchains=concepts&alias_model=allMin&avec_these=only_mono"
```

---

### 2. `GET /log`

Permet de consulter / télécharger le fichier journal d'une exécution de vectorisation spécifique.

#### Paramètres :

- `action`, `conceptsORchains`, `alias_model`, `avec_these`

---

### 3. `POST /uploadfile/`

Permet de téléverser un nouveau fichier d'export de notices (`export_rameau.csv` ou `export_rameau_update.csv`) sur le serveur.

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
