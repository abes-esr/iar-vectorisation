#!/usr/bin/env python
# coding: utf-8

import os
import re
import sys
import pickle
import optparse
import configparser
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer

load_dotenv()


def launch(action_in, conceptsORchains, alias_model, avec_these):
    root = ''
    root1 = ''
    cwd = str(Path.cwd())

    if "/app" in cwd:
        root = '/app/'
        root1 = '/app/'

    adress_qdrant = os.getenv("QDRANT_HOST", "localhost")
    port_qdrant = int(os.getenv("QDRANT_PORT", 6333))
    action = action_in
    nettoie_file_trv = True
    train_filename = "export_rameau"
    nb_lots_de_moyenne = 100

    bibprepared_filename = f"{train_filename}_{conceptsORchains}_{alias_model}_{avec_these}"
    RameauVectors = f"{conceptsORchains}_{alias_model}_{avec_these}"

    try:
        date_init_file = str(datetime.fromtimestamp(os.path.getmtime("export_rameau.csv")))
    except FileNotFoundError:
        date_init_file = "pas de fichier export_rameau.csv"
    print(f"date file init: {date_init_file}")

    try:
        date_update_file = str(datetime.fromtimestamp(os.path.getmtime("export_rameau_update.csv")))
    except FileNotFoundError:
        date_update_file = "pas de fichier export_rameau_update.csv"
    print(f"date file update: {date_update_file}")

    config_init = configparser.ConfigParser()
    try:
        config_init.read(root + bibprepared_filename + '_init.ini')
        date_init_file_last = config_init['DEFAULT']['date_mod']
    except Exception:
        date_init_file_last = "null"
        config_init['DEFAULT'] = {'date_mod': 'null'}
        with open(root + bibprepared_filename + '_init.ini', 'w') as configfile:
            config_init.write(configfile)

    print(f"adress_qdrant: {adress_qdrant}:{port_qdrant}")

    config_update = configparser.ConfigParser()
    try:
        config_update.read(root + bibprepared_filename + '_update.ini')
        date_update_file_last = config_update['DEFAULT']['date_mod']
    except Exception:
        date_update_file_last = "null"
        config_update['DEFAULT'] = {'date_mod': 'null'}
        with open(root + bibprepared_filename + '_update.ini', 'w') as configfile:
            config_update.write(configfile)

    update = True
    if action == "init":
        print("mode init")
        update = False
    elif action == "update":
        print("mode update")
        update = True
    elif action == "auto":
        if date_init_file != date_init_file_last:
            action = "init"
            update = False
            print("mode init")
        elif date_update_file != date_update_file_last:
            action = "update"
            update = True
            print("mode update")
        else:
            print("rien à traiter, on quitte.")
            return

    size_csv = 0
    size_csv_update = 0
    size_origine = 0
    size_origine_new = 0

    if action in ["init", "update", "restore"]:
        if update:
            train_filename = "export_rameau_update"
        else:
            train_filename = "export_rameau"

        if alias_model == 'allMin':
            emb_model = 'all-MiniLM-L6-v2'
        elif alias_model == 'distiluse':
            emb_model = 'sentence-transformers/distiluse-base-multilingual-cased-v2'
        elif alias_model == 'e5-large':
            emb_model = 'intfloat/multilingual-e5-large'

        encoder = SentenceTransformer(emb_model)

    if action in ["init", "update"]:
        def encode_concepts(text):
            return text.replace(' -- ', ';')

        def encode_special(text):
            return text.replace('_', '#u#').replace('"', '#d#').replace('\'', '#c#').replace(' ', '_').replace(',', '_').replace(';', ',')

        columns = ['PPN', 'THESE', 'TITRE', 'RESUME', 'RAMEAU', 'lang']
        print(f"\nChargement du fichier tabulé : {train_filename}.csv")
        training_data = pd.read_csv(root + train_filename + ".csv", sep='\t', header=None, names=columns)

        if avec_these == 'only_theses':
            training_data = training_data[training_data.THESE.notnull()]
        elif avec_these == 'only_mono':
            training_data = training_data[training_data.THESE.isnull()]

        if conceptsORchains == 'concepts':
            training_data['RAMEAU'] = training_data['RAMEAU'].apply(encode_concepts)

        training_data['TITRE'] = training_data['TITRE'].apply(lambda x: str(x).replace("\x98", "").replace("\x9c", ""))
        training_data['RAMEAU'] = training_data['RAMEAU'].apply(encode_special)
        training_data["DESCR"] = training_data['TITRE'].astype(str) + ", " + training_data["RESUME"].astype(str)

        print(f"Sauvegarde dans le fichier : {bibprepared_filename}.pkl")
        training_data.to_pickle(root + bibprepared_filename + '.pkl')
        size_csv = len(training_data)

        training_data = pd.read_pickle(root + bibprepared_filename + '.pkl')
        training_data = training_data[['PPN', 'DESCR', 'RAMEAU']]

        if len(training_data.index) < 2:
            print("Les données à charger sont vides, fin du traitement.")
            return

        def encode_batches(data, encoder, batch_size):
            encoded_batches = []
            num_batches = int(np.ceil(len(data) / batch_size))
            for i in range(num_batches):
                batch_data = data.iloc[i * batch_size: (i + 1) * batch_size]
                encoded_batch = encoder.encode(batch_data['DESCR'].tolist(), show_progress_bar=False)
                encoded_batches.append(encoded_batch)
            return np.concatenate(encoded_batches)

        print("\nCalcul des embeddings par lots de 5000...")
        start_time = datetime.now()

        for file in Path(root1).glob(f'df_all_{RameauVectors}*.pkl'):
            os.remove(file)

        bt_size = 5000
        nb_tours = len(training_data) // bt_size

        for i in range(0, nb_tours + 1):
            df4 = training_data.iloc[(i * bt_size):(i * bt_size) + bt_size].reset_index(drop=True)
            if df4.empty:
                continue
            encoded_articles = encode_batches(df4, encoder, bt_size)
            df4['content_vector'] = pd.Series(encoded_articles.tolist())
            df4 = df4.drop(columns=['DESCR'])

            with open(f"{root}df_all_{RameauVectors}_{i+1}.pkl", 'wb') as f:
                pickle.dump(df4, f)

        print(f"Temps d'exécution total de l'embedding : {(datetime.now() - start_time).total_seconds() * 1000:.2f} ms")

    if action == "init":
        print(f"\nMode init : fusion des fichiers vectorisés")
        list_of_files = list(Path(root1).glob(f'df_all_{RameauVectors}*.pkl'))
        result_dfs = [pd.read_pickle(file) for file in list_of_files]
        if result_dfs:
            result = pd.concat(result_dfs, ignore_index=True)
            size_csv_update = len(result)
            size_origine_new = len(result)
            with open(f"{root}{RameauVectors}.pkl", 'wb') as f:
                pickle.dump(result, f)

    elif action == "update":
        print("\nMode update...")
        global_pkl = f"{root}{RameauVectors}.pkl"
        if not os.path.exists(global_pkl):
            print(f"Le fichier global {global_pkl} n'existe pas, mise à jour impossible.")
            return

        df4 = pd.read_pickle(global_pkl)
        size_origine = len(df4)

        list_of_files = list(Path(root1).glob(f'df_all_{RameauVectors}*.pkl'))
        update_dfs = [pd.read_pickle(file) for file in list_of_files]
        if update_dfs:
            result = pd.concat(update_dfs, ignore_index=True)
            df4 = df4[~df4['PPN'].isin(result['PPN'])]
            df4 = pd.concat([df4, result], ignore_index=True)
            size_origine_new = len(df4)

            with open(global_pkl, 'wb') as f:
                pickle.dump(df4, f)

        for file in list_of_files:
            os.remove(file)

    if action in ["init", "update"]:
        print("\nRegroupement et calcul des moyennes vectorielles par concept...")
        global_df = pd.read_pickle(f"{root}{RameauVectors}.pkl")
        global_df.dropna(subset=['content_vector'], inplace=True)
        global_df = global_df.rename(columns={'RAMEAU': 'RAMEAU_list'})
        global_df['RAMEAU_list'] = global_df['RAMEAU_list'].apply(lambda x: re.split(r',', str(x)))
        exploded = global_df.explode('RAMEAU_list')

        label_vectors = exploded.groupby('RAMEAU_list').agg(
            mean=('content_vector', lambda x: np.vstack(x).mean(axis=0).tolist())
        ).reset_index()

        label_vectors.columns = ['label', 'content_vector']
        result_qdrant = label_vectors[['content_vector', 'label']]

        print(f"Sauvegarde de l'archive Qdrant : archive_{RameauVectors}.pkl")
        result_qdrant.to_pickle(f"{root}archive_{RameauVectors}.pkl")

    if action in ["init", "update", "restore"]:
        archive_path = f"{root}archive_{RameauVectors}.pkl"
        if not os.path.exists(archive_path):
            print(f"L'archive vectorielle '{archive_path}' est introuvable.")
            return

        result = pd.read_pickle(archive_path)
        collection_name = f"{conceptsORchains}_{alias_model}_{avec_these}"

        client = QdrantClient(host=adress_qdrant, port=port_qdrant)

        print(f"\nSuppression / Reconstitution de la collection Qdrant '{collection_name}'...")
        try:
            client.delete_collection(collection_name=collection_name)
        except Exception:
            pass

        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=encoder.get_sentence_embedding_dimension(),
                    distance=Distance.COSINE,
                    on_disk=True
                ),
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        always_ram=True,
                    ),
                ),
            )

        print("Chargement des vecteurs dans Qdrant...")
        client.upload_records(
            collection_name=collection_name,
            records=[
                models.Record(
                    id=idx,
                    vector=list(doc[0]),
                    payload={"label": doc[1]}
                ) for idx, doc in enumerate(result.values)
            ]
        )

        print("\nTest de recherche sur Qdrant (requête : 'la radio') :")
        hits = client.search(
            collection_name=collection_name,
            query_vector=encoder.encode("la radio").tolist(),
            limit=5
        )
        for hit in hits:
            print(f" - Score: {hit.score:.4f} | Label: {hit.payload.get('label')}")


def main():
    parser = optparse.OptionParser()
    parser.add_option('--action', '-a', default="update")
    parser.add_option('--conceptsORchains', '-c', default="concepts")
    parser.add_option('--alias_model', '-m', default="allMin")
    parser.add_option('--avec_these', '-t', default="only_mono")
    options, _ = parser.parse_args()

    if options.action not in ['init', 'update', 'auto', 'restore']:
        print('action doit être : init, update, auto ou restore')
        sys.exit(1)

    launch(options.action, options.conceptsORchains, options.alias_model, options.avec_these)


if __name__ == '__main__':
    main()