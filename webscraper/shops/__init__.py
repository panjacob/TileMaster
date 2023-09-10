import os
import json
import importlib
from .utils import sum_list, relative_to_absolute_path

TILE_OBJECT_KEYS = [
    "title",
    "url",
    "image_url"
]

_shops = ['castorama', 'obi']
_shops_dir = relative_to_absolute_path(__file__, '')
_shop_paths = [os.path.join(_shops_dir, i) for i in _shops]

shop_modules = []
for module_name in _shops:
    shop_modules.append(importlib.import_module('.' + module_name, 'shops'))


def get_local_tiles():
    return sum_list([
        json.load(open(os.path.join(_shops_dir, f'./{i}/{i}_tile_objects.json')))
        for i in _shops
    ])


def update_local():
    for shop in shop_modules:
        update_local_objects = getattr(shop, 'update_local_objects', None)
        if update_local_objects:
            update_local_objects()


def update_datastore():
    from google.cloud import datastore
    client = datastore.Client()

    def create_or_update(kind, name, **kwargs):
        key = client.key(kind, name)
        new_entity = client.get(key=key)
        if not new_entity:
            new_entity = datastore.Entity(key=key)

        for _property in kwargs:
            new_entity[_property] = kwargs[_property]

        client.put(new_entity)

    local_tiles = get_local_tiles()

    for i, json_tile in enumerate(local_tiles):
        if i % (len(local_tiles) // 100) == 0:
            print(i * 100 / len(local_tiles))

        create_or_update(
            'Tile', json_tile['url'], image_url=json_tile['image_url'], title=json_tile['title']
        )


def update_all():
    update_local()
    update_datastore()


def tile_url_to_image_url(url):
    for shop in shop_modules:
        method = getattr(shop, 'tile_url_to_image_url', None)
        if method:
            try:
                result = method(url)
            except ValueError:
                result = None
            if result:
                return result
