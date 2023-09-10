import json
import numpy as np
from skimage import io, img_as_float
import cv2
import collections
import os

"""
Title
-----
    Fingerprint algorithm
Author
-------
    Jakub Kwiatkowski
Description
-----------
generate_fingerprint(img_path)
Takes image path or image_url 
        Parameters
        ----------
            img_path : String
                User-specified image path
        Returns
        -------
            fingerprint which is a tuple of four values
                (first_most_popular_color, second_most_popular_color, third_most_popular_color, average_color_of_all_pixels)
            each value is compressed (divided by 16) and transformated to hex value
            ex. first_most_popular_color = 1af 
                                        r = 1
                                        g = a
                                        b = f
"""


def get_or_create_dir(my_dir):
    if not os.path.exists(my_dir):
        os.makedirs(my_dir)
        files = []
    else:
        files = os.listdir(my_dir)
    return files


def if_not_exist_create_dir(my_dir):
    if not os.path.exists(my_dir):
        os.makedirs(my_dir)


def json_open(json_dir):
    with open(json_dir) as json_file:
        return json.load(json_file)


def json_save(json_dir, result):
    with open(json_dir, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def load_image(img_path):
    return img_as_float(io.imread(img_path))


def crop_borders(image):
    accuracy = 0.25
    white = np.array([1, 1, 1])
    mask = np.abs(image - white).sum(axis=0) < accuracy

    coords = np.array(np.nonzero(~mask))
    top_left = np.min(coords, axis=1)
    bottom_right = np.max(coords, axis=1)

    out = image[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]]

    out = cv2.convertScaleAbs(out, alpha=255.0)
    return out


def approx_color(r, g, b, accuracy):
    r_approx = int(r / accuracy)
    g_approx = int(g / accuracy)
    b_approx = int(b / accuracy)
    return r_approx, g_approx, b_approx


def color_to_hex(color):
    [r, g, b] = color
    r = format(r, 'x')
    g = format(g, 'x')
    b = format(b, 'x')
    return r + g + b


def hex_to_color(hex_number):
    r = int(hex_number[0], 16)
    g = int(hex_number[1], 16)
    b = int(hex_number[2], 16)
    return [r, g, b]


def average(my_sum, pixel_count):
    return [int(my_sum[0] / pixel_count), int(my_sum[1] / pixel_count), int(my_sum[2] / pixel_count)]


def to_string_hex(approx_color_1, approx_color_2, approx_color_3, average_approx):
    return color_to_hex(approx_color_1) + color_to_hex(approx_color_2) + color_to_hex(approx_color_3) + color_to_hex(
        average_approx)


def hex_to_int(hex_number):
    return int(hex_number, 16)


def calculate_difference(color1, color2):
    color1 = hex_to_int(color1)
    color2 = hex_to_int(color2)
    if color1 >= color2:
        difference = color1 - color2
    else:
        difference = color2 - color1
    return difference


def split_fingerprint_to_colors(fingerprint):
    return [fingerprint[i:i + 3] for i in range(0, len(fingerprint), 3)]


# Comparing fingerprints
def compare_colors(colors1, colors2):
    difference = 0
    for i in range(0, len(colors1)):
        try:
            difference += calculate_difference(colors1[i], colors2[i])
        except:
            # FIX: some fingerprints are shorter
            # I assumed that they are different from color compared so big number is added
            difference += 4095
    return difference


def get_list_of_differences(tiles, fingerprint_to_compare):
    """
                   Takes fingerprint and list of tiles to comprae
                   ----------
                       fingerprint: : String
                           User-specified image path or url
                       tiles : Array of Datastore Entities
                   Returns
                   -------
                       Array of json's
                            key: tile id
                            value: difference
           """
    result = {}
    colors1 = split_fingerprint_to_colors(fingerprint_to_compare)
    for tile in tiles:
        try:
            colors2 = split_fingerprint_to_colors(tile['fingerprint'])
            difference = compare_colors(colors1, colors2)
            result[tile.key.id_or_name] = difference
        except Exception as e:
            # print('Zly fingerprint z bazy lub brak', e)
            pass
    return result


def sort_map(my_map):
    return {k: v for k, v in sorted(my_map.items(), key=lambda item: item[1])}


# Keywords which are bad candidates for attribute
forbidden_attributes = ['cm', 'x', 'na', 'taras', 'm2', 'view', 'Alfa-Cer', 'Lux', 'LUX', 'Cersanit', 'Dekor',
                        'Arte', 'Atem', 'BERGEN', 'Cerrad', 'Egen', 'Elastolith', 'FEBE', 'NUBILA', 'Nova', 'VINCI',
                        'SCARLET', 'Opoczno', 'CONVE', 'Burano', 'Vlada', 'beige', 'beż', 'biały', 'Black', 'black',
                        'Blanca', 'brown', 'Castanio', 'Diamond', 'DISENO', 'Dubiel', 'Garda', 'geo', 'gold', 'green',
                        'Pirgos', 'Sarda', 'Stargres', 'white', '-', 'grey', 'Płytka', 'Ceramstic', 'arte', 'colours',
                        'cersanit', 'ceramstic', 'color', 'alfa-cer', 'dekor']


# Determines whether keyword is a good candidate for attribute
def is_candidate_ok(candidate):
    if str(candidate).isnumeric():
        return False
    elif candidate in forbidden_attributes:
        return False
    elif ',' in candidate:
        return False
    elif 'cm' in candidate:
        return False
    else:
        return True


# Generates list of available attributes
# Each attribute in autoML vision should have at least 100 images per attribute to be accurate
def get_most_common_titles(titles_list):
    list_for_statistics = collections.Counter()
    for candidate in titles_list:
        candidate = candidate.lower()
        if is_candidate_ok(candidate):
            list_for_statistics[candidate] += 1

    result = []
    for el in list_for_statistics.most_common():
        if el[1] >= 100:
            result.append(el[0])
    return result


def generate_fingerprint(img_path):
    # loads image from path or url
    image = load_image(img_path)
    approx_color_accuracy1 = 16

    # removing white borders which could distort the result
    # image = crop_borders(image)
    rows, cols, color = image.shape
    pixel_count = rows * cols

    # initializing variables to calculate average_approx
    my_sum = [0, 0, 0]
    approx_colors = collections.Counter()
    for x in range(rows):
        for y in range(cols):
            [r, g, b] = image[x, y]
            if (r, g, b) == (1, 1, 1) or (r, g, b) == (0, 0, 0):
                continue
            r *= 256
            g *= 256
            b *= 256
            print(r, g, b)
            # average_approx
            my_sum[0] += r
            my_sum[1] += g
            my_sum[2] += b
            # statistics to get to know which color is most popular
            approx_colors[approx_color(r, g, b, approx_color_accuracy1)] += 1

    # approx_colors_most = 3 most popular colors
    approx_colors_most = approx_colors.most_common(3)
    approx_color_1 = approx_colors_most[0][0]

    # FIX - some tiles have one color or only two
    if len(approx_colors_most) > 1:
        approx_color_2 = approx_colors_most[1][0]
    else:
        approx_color_2 = [0, 0, 0]
    if len(approx_colors_most) > 2:
        approx_color_3 = approx_colors_most[2][0]
    else:
        approx_color_3 = [0, 0, 0]

    average_colors = average(my_sum, pixel_count)
    average_approx = approx_color(average_colors[0], average_colors[1], average_colors[2], approx_color_accuracy1)
    fingerprint = to_string_hex(approx_color_1, approx_color_2, approx_color_3, average_approx)
    print(fingerprint)
    return fingerprint
