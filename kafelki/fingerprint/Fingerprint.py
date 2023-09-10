import wget
from .utilis import *
from google.cloud import automl_v1beta1
from google.cloud import datastore
import requests
from google.cloud import storage
import threading
import concurrent.futures
import csv


# pip install --upgrade google-cloud-automl
# pip install --upgrade google-cloud-storage
# pip install google-cloud-datastore
# GOOGLE_APPLICATION_CREDENTIALS=/home/panjacob/Dokumenty/PROJEKTY/tile-master/fingerprint/project_key.json
# export GOOGLE_APPLICATION_CREDENTIALS=/home/panjacob/PROJEKTY/tile-master/fingerprint/project_key.json

# project_id = 'kafelki-297818'
# model_id = 'ICN8664514465712046080'

# PYTHONUNBUFFERED=1;GOOGLE_APPLICATION_CREDENTIALS=/home/panjacob/Dokumenty/PROJEKTY/tile-master/fingerprint/project_key.json

class Fingerprint:
    def __init__(self):
        self.datastore_client = datastore.Client()
        self.bucket_name = "pokazowy2"

    def get_similar_tiles(self, img_path):
        print("O! zaczynam szukać!")
        query = self.datastore_client.query(kind='Tile')
        try:
            attribute = self.get_description(img_path)
            print('Attribute: ', attribute)
            query.add_filter('attribute', '=', attribute)
            entities = list(query.fetch())
            if len(entities) < 1:
                raise Exception("That attribute has no images, comparing only with colors!")
        except Exception as e:
            print('AutoML error!')
            query = self.datastore_client.query(kind='Tile')
            entities = list(query.fetch())

        matched_entities = self.get_similar_tiles_by_color(img_path, entities)
        result = []

        for url in matched_entities[:20]:
            query = self.datastore_client.key('Tile', url)
            entity = self.datastore_client.get(key=query)
            tile = {}
            tile['title'] = entity['title']
            tile['image_url'] = entity['image_url']
            tile['url'] = url
            result.append(tile)


        return result

    def get_similar_tiles_by_color(self, img_path, tiles):
        fingerprint_to_compare = generate_fingerprint(img_path)
        list_of_differences = get_list_of_differences(tiles, fingerprint_to_compare)
        sorted_tiles = sort_map(list_of_differences)
        tiles_id_sorted = []
        for key in sorted_tiles.keys():
            tiles_id_sorted.append(key)
        return tiles_id_sorted

    def generate_most_common_titles(self, titles_list):
        self.most_common_titles = get_most_common_titles(titles_list)

    def give_attribute(self, title):
        for t in title.split(' '):
            t = t.lower()
            for title in self.most_common_titles:
                if t == title:
                    return title.title()
        return 'Roznorodny'

    @staticmethod
    def get_description(img_path):
        r = requests.get(img_path, stream=False)
        if r.status_code == 200:
            r.raw.decode_content = True
            content = r.content

        project_id = 'kafelki-297818'
        model_id = 'ICN8664514465712046080'
        prediction_client = automl_v1beta1.PredictionServiceClient()
        name = 'projects/{}/locations/us-central1/models/{}'.format(project_id, model_id)
        payload = {'image': {'image_bytes': content}}
        params = {}
        request = prediction_client.predict(name=name, payload=payload, params=params)
        return request.payload[0].display_name

    @staticmethod
    def get_tiles_matches_attribute(tiles, description):
        result = []
        for tile in tiles:
            if tile['attribute'] == description:
                result.append(tile)
        return result

    def update_fingerprints(self):
        query = self.datastore_client.query(kind='Tile')
        query.add_filter('fingerprint', '=', None)
        entities = list(query.fetch())
        for i, entity in enumerate(entities):
            try:
                fingerprint = generate_fingerprint(entity['image_url'])
                entity['fingerprint'] = fingerprint
                self.datastore_client.put(entity)
                print(i, "/", len(entities), "  ", fingerprint)
            except Exception as e:
                entity['fingerprint'] = None
                print(i + 1, "/", len(entities), "  ERROR", e)

    def update_attributes(self):
        query = self.datastore_client.query(kind='Tile')
        tiles = list(query.fetch())
        titles_list = []
        for tile in tiles:
            titles_list.extend(tile['title'].split(' '))

        self.generate_most_common_titles(titles_list)

        for i, tile in enumerate(tiles):
            attribute = self.give_attribute(tile['title'])
            if attribute == "På‚Ytka" or attribute == "på‚Ytka":
                attribute = "Plytka"
            tile['attribute'] = attribute
            self.datastore_client.put(tile)
            print(i + 1, "/", len(tiles), "  Updating attribute")

    def update_datastore(self):
        query = self.datastore_client.query(kind='Tile')
        query.add_filter('isdatastore', '=', False)
        tiles = list(query.fetch())
        tiles_len = len(tiles)
        get_or_create_dir("./temp")
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for i, tile in enumerate(tiles):
                futures.append(executor.submit(self.push_thread, tile=tile, bucket=bucket, tiles_len=tiles_len, i=i))
            for future in concurrent.futures.as_completed(futures):
                result = future.result()

    def push_thread(self, tile, bucket, tiles_len, i):
        try:
            source_file_name = wget.download(tile['image_url'], out="./temp")
            destination_blob_name = "img/" + os.path.basename(source_file_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            os.remove(source_file_name)
            tile['isdatastore'] = True
            self.datastore_client.put(tile)
            print("File {}/{} uploaded to {}.".format(i + 1, tiles_len, source_file_name, destination_blob_name))
        except Exception as e:
            print(i, e, tile['image_url'])
            tile['isdatastore'] = False
            self.datastore_client.put(tile)

    def generate_csv(self):
        query = self.datastore_client.query(kind='Tile')
        query.add_filter('isdatastore', '=', True)
        tiles = list(query.fetch())
        csv_filename = 'automl.csv'
        directory = "gs://" + self.bucket_name + "/img/"
        with open(csv_filename, 'w', newline='') as file:
            writer = csv.writer(file)
            for tile in tiles:
                print(tile['attribute'])
                tile_dir = directory + os.path.basename(tile['image_url'])
                writer.writerow(["TRAIN", tile_dir, tile['attribute']])
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(csv_filename)
        blob.upload_from_filename(csv_filename)
