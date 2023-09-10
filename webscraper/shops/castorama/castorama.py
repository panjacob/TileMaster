import json
from urllib import request
from urllib.request import urlopen

from bs4 import BeautifulSoup

from ..utils import relative_to_absolute_path, threaded_map, sum_list

BASE_URL = 'https://www.castorama.pl'

TILE_OBJECTS_PATH = relative_to_absolute_path(__file__, './castorama_tile_objects.json')


def _get_categories():
    # soup = bs4.BeautifulSoup(
    #     request.urlopen('https://www.castorama.pl/produkty/wykonczenie/plytki-scienne-podlogowe-i-elewacyjne.html'),
    #     'html.parser'
    # )
    # return [BASE_URL + element.attrs['href'] for element in soup.find_all('a', {'class': 'category-item__name'})
    #         if 'akcesori' not in element.attrs['href']]
    return {
        "2037": "plytki-podlogowe",
        "2038": "plytki-scienne",
        "2039": "plytki-elewacyjne",
        "8259": "plytki-uniwersalne"
    }


def _get_page_json(category_id, page) -> dict:
    item_count_per_page = 47
    url = f'https://www.castorama.pl/api/rest/headless/public/categories/products?searchCriteria[currentPage]={page}&searchCriteria[filterGroups][0][filters][0][conditionType]=eq&searchCriteria[filterGroups][0][filters][0][field]=category&searchCriteria[filterGroups][0][filters][0][value]={category_id}&searchCriteria[pageSize]={item_count_per_page}&searchCriteria[sortOrders][0][direction]=desc&searchCriteria[sortOrders][0][field]=promoted&storeId=default'
    return json.loads(request.urlopen(url).read())


def _category_id_to_tile_objects(category_id):
    result = []
    category = _get_categories()[category_id]

    item_count_per_page = 47
    data = _get_page_json(category_id, 1)
    item_count = data['all']
    page_count = item_count // item_count_per_page
    if item_count % item_count_per_page:
        page_count += 1

    for i in range(page_count):
        data = _get_page_json(category_id, i + 1)['items']
        data = [
            {
                'title': i['name'],
                'tile_id': i['entity_id'],
                'url': i['url'],
                'image_url': i['image'],
                'category': category,
            } for i in data]

        result += data

    return result


def update_local_objects():
    ids = list(_get_categories().keys())
    threaded_map(ids, _category_id_to_tile_objects, 2)

    json.dump(sum_list(ids), open(TILE_OBJECTS_PATH, 'w'))


def tile_url_to_image_url(url):
    if 'castorama' in url:
        soup = BeautifulSoup(urlopen(url), 'html.parser')
        return json.loads(soup.find_all('script')[2].contents[0])['image']
    else:
        return None
