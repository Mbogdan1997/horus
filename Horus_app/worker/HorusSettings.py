import os, sys, uuid

SECRET_KEY = uuid.uuid4().bytes
DEBUG=True

HOSTNAME = 'http://localhost:5000'

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = APP_ROOT.split('worker')[0]+'data/preprocess/input/'
OUTPUT_FOLDER = APP_ROOT.split('worker')[0]+'data/nn/output/'
TEMPLATE_FOLDER = APP_ROOT.split('worker')[0]+'worker/templates/'
ALLOWED_EXTENSIONS = {'txt', 'json'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

secret_key = 'b3nzisp3ctr4l3'
#TEMPLATES_AUTO_RELOAD = True

BAND_VALUES = {'SENTINEL2_L2A': ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B11', 'B12'],
              'LANDSAT8_L1C' : ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B10', 'B11'],
              'MODIS' : ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07']
             }

OTHER_INDEXES = {'SENTINEL2_L2A': ['SCL', 'SNW', 'CLD', 'NDVI', 'EVI'],
                 'LANDSAT8_L1C' : ['NDVI', 'EVI'],
                 'MODIS' : ''
                }

start_coords = (46.9294,23.902473)
tolerance = 0.00025
pixel_range = 3

