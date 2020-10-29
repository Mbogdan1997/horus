#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import os
import sys
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import csv
import ast
import math

from sentinelhub import SHConfig
from sentinelhub import MimeType, CRS, BBox, SentinelHubRequest, \
    SentinelHubDownloadClient, DataSource, bbox_to_dimensions, \
    DownloadRequest, pixel_to_utm, to_wgs84, to_utm_bbox, \
    wgs84_to_pixel, wgs84_to_utm, utm_to_pixel
from HorusWeather import get_OWM_data
from HorusSettings import tolerance, pixel_range

from utils.plots import plot_image, save_image
from utils.constants import PREPROCESS_INPUT_DIR, PREPROCESS_OUTPUT_DIR, INPUT_PLACEMARK, INPUT_JSON, BAND_NAMES, INPUT_LABELS_FILE

WORKING_DIR = os.path.dirname(__file__).split('worker')[0]


# In case you put the credentials into the configuration file you can leave the
# following Id and Secret key as empty strings
CLIENT_ID = '96b1057d-b63d-40c2-83f3-3bac64e3d4cd'
CLIENT_SECRET = 'uWcfirBlKkh;)/$2mf3@e@5vr-dj/ijBAN[7Vof!'


def connect_to_sentinelhub(id = '', secret = ''):
    global config
    try:
        config = SHConfig()

        if CLIENT_ID and CLIENT_SECRET:
            config.sh_client_id = id 
            config.sh_client_secret = secret

        if config.sh_client_id == '' or config.sh_client_secret == '':
            print("Warning! To use Sentinel Hub services, please provide the credentials (client ID and client secret).")
            sys.exit()

        return config

    except Exception as e:
        print(e)

def get_Bbox_from_points_set(json_file, points):

    lat, lng = [], []
    for current_measurement_point in points:
        lat.append(current_measurement_point[0])
        lng.append(current_measurement_point[1])

    lleft_lng, lleft_lat = (1 - tolerance) * min(lng), (1 - tolerance) * min(lat)
    urright_lng, uright_lat = (1 + tolerance) * max(lng), (1 + tolerance) * max(lat)
    pts_bbox = [lleft_lng, lleft_lat, urright_lng, uright_lat]
    print('   - Points set bounding box: {}'.format(pts_bbox))

    return pts_bbox


def get_point_distance(p1, p2, res):
    geom_dist = math.sqrt( (p1[0]-p2[0]) ** 2, (p1[1]-p2[1]) ** 2)
    return res*geom_dist

def get_longlat_distance(ll1, ll2):
    R = 6371; # Radius of the earth in km
    dLat = np.deg2rad (ll2[1]-ll1[1])  # deg2rad below
    dLon = np.deg2rad(ll2[0]-ll1[0]) 
    a =  Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) * Math.sin(dLon/2) * Math.sin(dLon/2)
    c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)) 
    d = R * c; # Distance in km
    return d


def get_map_size(coordinates, res = 2.5):

    mbbox = BBox(bbox=coordinates, crs=CRS.WGS84)
    utm_mbbox = to_utm_bbox(mbbox)
    msize = bbox_to_dimensions(mbbox, res)
    max_size = max(msize)
    if max_size > 2500:
        res = int(res * max_size / 2500) +1
        msize = bbox_to_dimensions(mbbox, res)

    return mbbox, msize, utm_mbbox, res


def get_all_bands(satelite, es, rab, tinterval, datafolder, ab_bbox, ab_size):
    if satelite in ["SENTINEL2_L2A", "LANDSAT8_L1C"]:
        if satelite == "SENTINEL2_L2A":
            ds = DataSource.SENTINEL2_L2A
        if satelite == "LANDSAT8_L1C":
            ds = DataSource.LANDSAT8_L1C

        request_all_bands = SentinelHubRequest(
            data_folder = datafolder,
            evalscript = es,
            input_data = [
                SentinelHubRequest.input_data(
                    data_source = ds,
                    time_interval = tinterval,
                    maxcc = 0.1,
                    mosaicking_order = 'leastCC'
            )],
            responses = rab,
            bbox = ab_bbox, 
            size = ab_size, 
            config = config
        )
    else:
        request_all_bands = SentinelHubRequest(
            data_folder = datafolder,
            evalscript= es ,
            input_data=[
                SentinelHubRequest.input_data(
                    data_source=DataSource.MODIS,
                    time_interval = tinterval
                )
            ],
            responses= [
            {
                "identifier": 'default',
                "format": {
                    "type": "image/tiff"
                }
            }],
            bbox = ab_bbox, 
            size = ab_size, 
            config=config
        )

    return request_all_bands.get_data(save_data = True)


def get_pixel_for_lng_lat(lng, lat, utm_box):
    pixel = wgs84_to_pixel(lng, lat, utm_box)

    return pixel


def get_value_for_pixel(pixel, data_array):
    datalist = []
    dataval = None
    if len(data_array.shape) == 3:
        if pixel[0] in range(data_array.shape[0]):
            if pixel[1] in range(data_array.shape[1]):
                datalist = data_array[pixel[0]][pixel[1]]
        return datalist
    if len(data_array.shape) == 2:
        if pixel[0] in range(data_array.shape[0]):
            if pixel[1] in range(data_array.shape[1]):
                dataval = data_array[pixel[0]][pixel[1]]
        return dataval


def get_evalscript_modis(bands):
    varbands = []
    for i in range(len(bands)):
        varbands.append('sample.{}'.format(bands[i]))
    varbands = ", ".join(varbands)
    
    eval_string = """
    //VERSION=3

    function setup() {{
        return {{
            input: [{{
                bands: {0},
                units: "DN"
            }}],
            output: {{
                bands: {1}, sampleType: SampleType.FLOAT32
            }}
        }};
    }}

    function evaluatePixel(sample) {{
        return [{2}].map(a => a / 10000);
    }}
    """.format(bands, len(bands), varbands)
    return eval_string


def get_evalscript_all_bands(bands, indexes):

    if len(bands) !=0 and len(indexes) !=0:
        varbands = []
        for i in range(len(bands)):
            varbands.append('sample.{}'.format(bands[i]))
        varbands = ", ".join(varbands)

        validindexes, outindexes, varindexes, retindexes = [], [], [], []
        for i in range(len(indexes)):
            if indexes[i] not in ['NDVI', 'EVI']:
                validindexes.append(indexes[i])
                outindexes.append('{{id: "{}", bands: 1, sampleType: SampleType.FLOAT32}}'.format(indexes[i]))
                varindexes.append('var {} = [sample.{}]'.format(indexes[i].lower(), indexes[i]))
                retindexes.append('{}: {}'.format(indexes[i], indexes[i].lower()))
            if indexes[i] == 'NDVI' and 'B08' in bands and 'B04' in bands:
                outindexes.append('{{id: "{}", bands: 1, sampleType: SampleType.FLOAT32}}'.format(indexes[i]))
                varindexes.append('var ndvi = [(sample.B08 - sample.B04)/(sample.B08 + sample.B04)]')
                retindexes.append('{}: {}'.format(indexes[i], indexes[i].lower()))
            if indexes[i] == 'EVI' and 'B08' in bands and 'B04' in bands and 'B02' in bands:
                outindexes.append('{{id: "{}", bands: 1, sampleType: SampleType.FLOAT32}}'.format(indexes[i]))
                varindexes.append('var evi = [2.5 * (sample.B08 - sample.B04) / ((sample.B08 + 6.0 * sample.B04 - 7.5 * sample.B02) + 1.0)]')
                retindexes.append('{}: {}'.format(indexes[i], indexes[i].lower()))
        outindexes = ",\n                    ".join(outindexes)
        varindexes = "\n            ".join(varindexes)
        retindexes = ",\n                ".join(retindexes)

        eval_string = """
            //VERSION=3
            function setup() {{
                return {{
                    input: [{{
                        bands: {0},
                        units: "DN"
                    }}],
                    output: [
                        {{id: "Bands", bands: {1}, sampleType: SampleType.FLOAT32}},
                        {2}
                    ]
                }};
            }}

            function evaluatePixel(sample) {{
                var bands = [{3}].map(a => a / 10000)
                {4}

                return {{
                    Bands: bands, 
                    {5}
                }};
            }}""".format(bands+validindexes, len(bands), outindexes, varbands, varindexes, retindexes)

    elif len(indexes) == 0:
        varbands = []
        for i in range(len(bands)):
            varbands.append('sample.{}'.format(bands[i]))
        varbands = ", ".join(varbands)

        eval_string = """
            //VERSION=3
            function setup() {{
                return {{
                    input: [{{
                        bands: {0},
                        units: "DN"
                    }}],
                    output: [
                        {{id: "Bands", bands: {1}, sampleType: SampleType.FLOAT32}}
                    ]
                }};
            }}

            function evaluatePixel(sample) {{
                var bands = [{2}].map(a => a / 10000)

                return {{
                    Bands: bands, 
                }};
            }}""".format(bands, len(bands), varbands)
    return eval_string


def get_response_all_bands(bands, indexes):
     
    response_string = [
            {
                "identifier": "Bands",
                "format": {
                    "type": "image/tiff"
                }
            }]

    for idx in indexes:
        if idx not in ['NDVI', 'EVI']:
            idx_response = "{{'identifier': '{}', 'format': {{'type': 'image/tiff'}}}}".format(idx)
            response_string.append(ast.literal_eval(idx_response))
        if idx == 'NDVI' and 'B08' in bands and 'B04' in bands:
            idx_response = "{{'identifier': '{}', 'format': {{'type': 'image/tiff'}}}}".format(idx)
            response_string.append(ast.literal_eval(idx_response))
        if idx == 'EVI' and 'B08' in bands and 'B04' in bands and 'B02' in bands:
            idx_response = "{{'identifier': '{}', 'format': {{'type': 'image/tiff'}}}}".format(idx)
            response_string.append(ast.literal_eval(idx_response))
    return response_string


def check_valid_bands(row_dict, bands):
    valid_data = False
    for b in range(len(bands)):
        if row_dict.get(b) != 0:
            valid_data = True
            return valid_data
    
    return valid_data



def HorusETL(points, satelite, bands, extra_param, weather, time_interval, learning):
    print("   - Horus ETL library called with:\n       Satelite: {}\n       Bands: {}\n       Extra_parameters: {}\n       Weather: {}\n       Time interval: {}".format(satelite, bands, extra_param, weather, time_interval))
    start_time = time.time()

    # connect to SentinelHub
    connect_to_sentinelhub(CLIENT_ID, CLIENT_SECRET)

    # output and temporary file names
    output_csv = PREPROCESS_OUTPUT_DIR + '{}.csv'.format(time_interval[1])
        
    #convert placemark file to csv
    placemark_bbox = get_Bbox_from_points_set(PREPROCESS_INPUT_DIR + INPUT_JSON, points)

    # map boundingbox coordinates
    map_coords_wgs84 = placemark_bbox
    map_bbox, map_size, utm_bbox, resolution = get_map_size(map_coords_wgs84)
    print('   - Map data:\n       Bounding box: {}\n       Map size: {}\n       UTM box: {}\n'.format(map_bbox, map_size, utm_bbox))
    print('       Image shape at {} m resolution: {} pixels'.format(resolution, map_size))

    # evalscript, response bands and true color setup for different satelites
    if satelite == 'MODIS':
        true_color = [0,3,2] # R=1, G=4, B=3 but index starts at 0
        evalscript_all_bands = get_evalscript_modis(bands)
        response_all_bands = [
            {
                "identifier": "default",
                "format": {
                    "type": "image/tiff"
                }
            }]
    else:
        true_color = [3,2,1] # R=4, G=3, B=2 but index starts at 0
        evalscript_all_bands = get_evalscript_all_bands(bands, extra_param)
        response_all_bands = get_response_all_bands(bands, extra_param)

    # request for all bands
    datafolder = PREPROCESS_OUTPUT_DIR + 'all_bands'
    sentinel_response = get_all_bands(satelite, 
                                      evalscript_all_bands, 
                                      response_all_bands, 
                                      time_interval, 
                                      datafolder, 
                                      map_bbox, 
                                      map_size)

    sentinel_response_img_number = len(sentinel_response)
    print("Downloaded images: {}".format(sentinel_response_img_number))
    print('The output directory has been created and a tiff file with all 13 bands was saved into ' \
        'the following structure:')
    for folder, _, filenames in os.walk(datafolder):
        for filename in filenames:
            print('   {}'.format(os.path.join(folder, filename)))

    # plot sequence for truecolor image, factor 3.5 to increase brightness
    image_file_dir = WORKING_DIR + '/worker/static/img/'
    true_image_file_path = image_file_dir + 'true_color.png'
    if satelite == 'MODIS':
        image = sentinel_response[0]
    else:
        image = sentinel_response[0].get('Bands.tif')
    for i in range(image.shape[-1]):
        save_image(image[:,:,i], 
                   filename=image_file_dir + '{}_{}_band{}.png'.format(satelite, time_interval[1], BAND_NAMES['SENTINEL2_L2A'][i]),
                   res=100,
                   factor = 2.5)
    save_image(image[:,:,true_color], filename=true_image_file_path, res=100, factor = 3.5, clip_range = (0,1))

    # get transform parameter to interchange coordinate systems
    transform = (utm_bbox.lower_left[0], resolution, 0, utm_bbox.upper_right[1], 0, -resolution)

    # define new dataframe for file export
    col_names = bands + extra_param + weather  
    if learning == 'Supervised':
        col_names += ['label']
    ndfx = pd.DataFrame(columns=col_names)
    rangexl = pixel_range
    rangexr = map_size[0] - pixel_range
    rangeyd = pixel_range
    rangeyu = map_size[1] - pixel_range


    # extract pixels for each interest POI
    pointswittemperature = []
    pointswittemperature2 = []
    for i in range(len(points)):

        # long-lat distance (Harvesine)
        px_col = (points[i][1], points[i][0])

        # # weather data selection with Haversine function
        # if len(pointswittemperature) == 0:
        #     # request OpenWeather data
        #     px_weather = get_OWM_data(px_col)
        #     if 'TEMP' in weather:
        #         temp_dict = {'TEMP': px_weather.get('TEMP')}
        #     if 'PRES' in weather:
        #         pres_dict = {'PRES': px_weather.get('PRES')}
        #     if 'HUM' in weather:
        #         hum_dict = {'HUM': px_weather.get('HUM')}
        # else:

        #     ispointok = True
        #     for pt in pointswittemperature:
        #         if get_longlat_distance(px_col, pt) >= 300:
                    
        #             # request OpenWeather data
        #             px_weather = get_OWM_data(px_col)
        #             if 'TEMP' in weather:
        #                 temp_dict = {'TEMP': px_weather.get('TEMP')}
        #             if 'PRES' in weather:
        #                 pres_dict = {'PRES': px_weather.get('PRES')}
        #             if 'HUM' in weather:
        #                 hum_dict = {'HUM': px_weather.get('HUM')}
        #             ispointok =  False
        #         else:
        #             if 'TEMP' in weather:
        #                 temp_dict = {'TEMP': pt.get('TEMP')}
        #             if 'PRES' in weather:
        #                 pres_dict = {'PRES': pt.get('PRES')}
        #             if 'HUM' in weather:
        #                 hum_dict = {'HUM': pt.get('HUM')}
        #     if not ispointok:
        #         px_weather = get_OWM_data(px_col)
        #         pt['TEMP'] = px_weather.get('TEMP')
        #         pt['PRES'] = px_weather.get('PRES')
        #         pt['HUM'] = px_weather.get('HUM')
        

        pxc = get_pixel_for_lng_lat(px_col[0], px_col[1], transform)

        # weather data selection for geometrical distance
        if len(pointswittemperature2) == 0:
            # request OpenWeather data
            px_weather = get_OWM_data(px_col)
            if 'TEMP' in weather:
                temp_dict = {'TEMP': px_weather.get('TEMP')}
            if 'PRES' in weather:
                pres_dict = {'PRES': px_weather.get('PRES')}
            if 'HUM' in weather:
                hum_dict = {'HUM': px_weather.get('HUM')}
        else:

            ispointok = True
            for pt2 in pointswittemperature2:
                if get_point_distance(pxc, pt2, resolution) >= 300:
                    
                    # request OpenWeather data
                    px_weather = get_OWM_data(px_col)
                    if 'TEMP' in weather:
                        temp_dict = {'TEMP': px_weather.get('TEMP')}
                    if 'PRES' in weather:
                        pres_dict = {'PRES': px_weather.get('PRES')}
                    if 'HUM' in weather:
                        hum_dict = {'HUM': px_weather.get('HUM')}
                    ispointok =  False
                else:
                    if 'TEMP' in weather:
                        temp_dict = {'TEMP': pt.get('TEMP')}
                    if 'PRES' in weather:
                        pres_dict = {'PRES': pt.get('PRES')}
                    if 'HUM' in weather:
                        hum_dict = {'HUM': pt.get('HUM')}
            if not ispointok:
                px_weather = get_OWM_data(px_col)
                pt2['TEMP'] = px_weather.get('TEMP')
                pt2['PRES'] = px_weather.get('PRES')
                pt2['HUM'] = px_weather.get('HUM')




        point_x_1 = pxc[0] - pixel_range
        point_x_2 = pxc[0] + pixel_range +1
        point_y_1 = pxc[1] - pixel_range
        point_y_2 = pxc[1]+ pixel_range + 1



        for x in range(point_x_1, point_x_2):
            for y in range(point_y_1, point_y_2):
                if px_col[0] > rangexl  and px_col[0] < rangexr and px_col[1] > rangeyd and px_col[1] < rangeyu:    
                    row, bands_px = {}, {}
                    if satelite == 'MODIS':
                        b_px_value = get_value_for_pixel((x,y), sentinel_response[0])
                    else:
                        b_px_value = get_value_for_pixel((x,y), sentinel_response[0].get('Bands.tif'))
                    for j in range(len(bands)):
                        bands_px[bands[j]] = b_px_value[j]
                    row.update(bands_px)

                    indexes_px = {}
                    for idx in extra_param:
                        i_px_value = get_value_for_pixel((x,y), sentinel_response[0].get(str(idx)+'.tif'))
                        indexes_px[idx] = i_px_value
                    row.update(indexes_px)

                    if 'TEMP' in weather:
                        row.update(temp_dict)
                    if 'PRES' in weather:
                        row.update(pres_dict)
                    if 'HUM' in weather:                
                        row.update(hum_dict)

                    if learning == 'Supervised':
                        label_px = {}
                        label_px['label'] = points[i][2]
                        row.update(label_px)
                    elif learning == 'Semi-supervised':
                        if points[2] != 0:
                            label_px = {}
                            label_px['label'] = points[i][2]
                            row.update(label_px)

                    if check_valid_bands(row, bands):
                        ndfx = ndfx.append(row, ignore_index=True)

    ndfx.to_csv(output_csv, sep=';', index = False, header=True)

    total_exec_time = round((time.time() - start_time) / 60, 2)
    print('Total Execution Time: {} minutes'.format(total_exec_time))

    return map_bbox, map_size, sentinel_response_img_number, 'true_color.png' , output_csv, total_exec_time