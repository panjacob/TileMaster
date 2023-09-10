import json
import os
import re
from urllib.request import urlopen, urlretrieve

import bs4

from ..utils import threaded_map, relative_to_absolute_path

BASE_URL = 'https://www.obi.pl'
TILE_URLS_PATH = relative_to_absolute_path(__file__, './obi_tile_urls.json')
TILE_OBJECTS_PATH = relative_to_absolute_path(__file__, './obi_tile_objects.json')
TILE_IMAGES_DIR = relative_to_absolute_path(__file__, './images/')

IMAGE_SIZE = '256x256'


def _get_categories():
    soup = bs4.BeautifulSoup(urlopen('https://www.obi.pl/budowac/plytki/c/308'), 'html.parser')
    return [element.next.attrs['href'] for element in soup.find_all('div', {'class': 'categoryitem'})]


def _category_url_to_tile_urls(url: str):
    result = []
    soup = bs4.BeautifulSoup(urlopen(url).read(), 'html.parser')
    result += [i.attrs['href'] for i in soup.find_all('a', {'class': 'product-wrapper wt_ignore'})]
    last_page = int(next(soup.find_all('a', {'class': 'pagination-bar__link'})[-1].children).text)
    i = 2
    while i <= last_page:
        soup = bs4.BeautifulSoup(urlopen(url + f'?page={i}').read(), 'html.parser')
        result += [i.attrs['href'] for i in soup.find_all('a', {'class': 'product-wrapper wt_ignore'})]
        i += 1
    return result


def _tile_url_to_json(url):
    soup = bs4.BeautifulSoup(urlopen(url).read(), 'html.parser')
    json_data = {}
    json_data['title'] = soup.find('h1', {'class': 'overview__heading'}).text
    json_data['url'] = url

    image_url = soup.find('img', {'class': 'ads-slider__image'}).attrs['src']
    image_url = 'https:' + re.sub('\\d+x\\d+', IMAGE_SIZE, image_url)
    json_data['image_url'] = image_url
    json_data['category'] = re.match('.+\\.pl/(.*?)/.*', url).group(1)

    try:
        json_data['width'] = soup.find('td', {'data-label': 'Szerokość'}).text
        json_data['height'] = soup.find('td', {'data-label': 'Wysokość'}).text
    except AttributeError as e:
        print(e, 'in', url)

    return json_data


def update_tile_urls():
    data = _get_categories()
    threaded_map(data, _category_url_to_tile_urls, 4)
    result = []
    for category in data:
        result += [BASE_URL + url for url in category]
    json.dump(result, open(TILE_URLS_PATH, 'w'))


def update_local_objects():
    update_tile_urls()
    tile_urls = json.load(open(TILE_URLS_PATH))[:100]
    threaded_map(tile_urls, _tile_url_to_json, 8)
    try:
        json.dump(tile_urls, open(TILE_OBJECTS_PATH, 'w', encoding='utf8'), ensure_ascii=False)
    except Exception as e:
        print(e)
        print('Printing the result...')
        print(tile_urls)


def save_images():
    def download_img(tile):
        file_name = os.path.join(TILE_IMAGES_DIR, tile['url'].split('/')[-1] + '.jpg')
        urlretrieve(tile['image_url'], file_name)

    data = json.load(open(TILE_OBJECTS_PATH))
    threaded_map(data, download_img, 8)


def tile_url_to_image_url(url, size=IMAGE_SIZE):
    if 'obi' in url:
        soup = bs4.BeautifulSoup(urlopen(url).read(), 'html.parser')
        image_url = soup.find('img', {'class': 'ads-slider__image'}).attrs['src']
        image_url = 'https:' + re.sub('\\d+x\\d+', size, image_url)
        return image_url
    else:
        return None
