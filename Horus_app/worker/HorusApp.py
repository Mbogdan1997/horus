from flask import Flask, render_template, request, redirect, url_for, json, make_response, jsonify, session
from HorusForms import HorusForm
from HorusMaps import mapGenerator, mapPOIUpdate
from bs4 import BeautifulSoup as bs
from bs4 import Doctype
# from werkzeug import MultiDict

import os
import requests #pt OWM
import json
import pandas as pd
from datetime import date
import Horus_ETL_lib

from HorusSettings import BAND_VALUES, OTHER_INDEXES, TEMPLATE_FOLDER, start_coords
from HorusWeather import get_OWM_data
import HorusSettings as settings


# App initialisation
app = Flask(__name__)
app.config.from_object(settings)
newpoints = []

class HorusSession:
    def __init__(self, satelite, bands, indexes, weather, datefrom, dateto, points, learning):
        self.satelite = satelite
        self.bands = bands
        self.indexes = indexes
        self.weather = weather
        self.datefrom = datefrom
        self.dateto = dateto 
        self.points = points 
        self.learning = learning

# Routes
@app.route('/', methods = ['GET', 'POST'])
def index():
    print(request)
    form = HorusForm()
    if request.method == 'POST':
        print("in post")
        ses = session.get('select')
        default_satlites = ses.get('satelite')
        default_bands = ses.get('bands')
        default_index = ses.get('indexes')
        filename = ses.get('points')
        print("session {}".format(default_satlites))
        print(default_bands)
        print(default_index)
        dfrom = ses.get('date_from')
        print(dfrom)
        dto = ses.get('date_to')
    else:
        default_satlites = list(BAND_VALUES.keys())[0]
        default_bands = list(BAND_VALUES.values())[0]
        default_index = list(OTHER_INDEXES.values())[0]
        #dfrom = date.today().strftime('%Y-%m-%d')
        #dto = date.today()
        print("print date {}".format(type(date.today().strftime('%Y-%m-%d'))))

    #print(form.bands.choices)
    
    form.bands.choices = [(x, x) for x in default_bands]
    form.indexes.choices = [(x, x) for x in default_index]
    form.extra.choices = [(x, x) for x in ['TEMP', 'HUM', 'PRES']]
    # form.date_from = dfrom
    # form.date_to = dto

    filename = 'map.html'
    map = mapGenerator(save = True, mapfilename = TEMPLATE_FOLDER + filename)
    #print("initial map: {} from ".format(map_draw, path+filename))

    #session['HorusQuery'] = form
    #                         default_satlites,
    #                         default_bands,
    #                         default_index,
    #                         map,
    #                         filename
    #                         ]
    # print(session)

    return render_template('index.html', 
                            form = form, 
                            selectSatelite = default_satlites,
                            selectBand = default_bands,
                            selectIndex = default_index,
                            #map=map,
                            mapName = filename
                          )


@app.route('/map', methods = ['POST'])
def update_file():
    global newpoints

    selected_file = request.form.get('selected_file')
    
    pointsfn = 'pointsmap.html'
    updatedMap, newpoints = mapPOIUpdate(selected_file, pointsfn)

    return updatedMap._repr_html_()


@app.route('/_update_dropdown', methods = ['GET', 'POST'])
def update_dropdown():
       
    # the value of the satelite dropdown (selected by the user)
    selected_satelite = request.form.get('selected_satelite')

    updated_bands = BAND_VALUES[selected_satelite]
    updated_index = OTHER_INDEXES[selected_satelite]

    nform = HorusForm(request.form)
    nform.bands.choices = [(x, x) for x in updated_bands]
    nform.indexes.choices = [(x, x) for x in updated_index]
    
    new_template =  render_template('index.html', 
                            form = nform, 
                            selectSatelite = selected_satelite,
                            selectBand = updated_bands,
                            selectIndex = updated_index,
                            mapName = 'map.html'
                        )

    soup  = bs(new_template,'html.parser')
    bands_div = str(soup.find("div", {"id" : "bands"}))
    indexes_div = str(soup.find("div", {"id" : "indexes"}))

    return {'bands': bands_div, 'indexes': indexes_div}



@app.route('/send', methods = ['GET', 'POST'])
def send():
    print(newpoints)
    if request.method == 'POST':
        print(request.form)
        satelite = request.form.get('satelite')
        dateFrom = request.form.get('date_from')
        dateTo = request.form.get('date_to')
        learningType = request.form.get('learning')

        new_bands = []
        new_indices = []
        new_weather = []
        for item in dict(request.form):
            if "bands" in item:
                new_bands.append(request.form.get(item))
            if "indexes" in item:
                new_indices.append(request.form.get(item))
            if "weather" in item:
                new_weather.append(request.form.get(item))

        
        # validation for NDVI and EVI indexes
        if 'NDVI' in new_indices:
            if 'B04' not in new_bands:
                new_bands.append('B04')
            if 'B08' not in new_bands:
                new_bands.append('B08')
        
        if 'EVI' in new_indices:
            if 'B02' not in new_bands:
                new_bands.append('B02')
            if 'B04' not in new_bands:
                new_bands.append('B04')
            if 'B08' not in new_bands:
                new_bands.append('B08')


        bands = BAND_VALUES.get(satelite)
        timeframe = (dateFrom,dateTo)

    session['select'] = HorusSession(satelite, new_bands, new_indices, new_weather, dateFrom, dateTo, 'map.html', learningType ).__dict__
    print('Satelite: {}\n  Bands: {}\n  Date from: {}\n  Date to: {}'.format(satelite, bands, dateFrom, dateTo))
    mapBox, mapSize, imageNumber, image_file, output_file, tet = Horus_ETL_lib.HorusETL(newpoints, satelite, new_bands, new_indices ,new_weather, timeframe, learningType)
    bb = [i for i in mapBox]
    lllon, lllat, urlon, urlat = round(bb[0], 4), round(bb[1], 4), round(bb[2], 4), round(bb[3], 4)
    print('  Bounding Box: {}\n  Map Size: {}\n  Images downloaded: {}\n  Output file: {}\n'.format(mapBox, mapSize, imageNumber, output_file))

    return render_template('processing.html', satelite=satelite, 
                                              bands=new_bands,
                                              extraParam=new_indices,
                                              weather=new_weather,
                                              dateFrom=dateFrom,
                                              dateTo=dateTo,
                                              bbox=mapBox,
                                              lllon=lllon,
                                              lllat=lllat,
                                              urlon=urlon,
                                              urlat=urlat,
                                              mapsize=mapSize,
                                              imgnumber=imageNumber,
                                              imgfile = image_file,
                                              nnfile=output_file.split('data')[-1],
                                              totalExec=tet
                          ) 
    

@app.route('/new_select', methods = ['GET', 'POST'])
def new_select():
    # if request.method == 'POST':
    if request.method == 'POST':
        form = HorusForm()
        ses = session.get('select')
        default_satlites = ses.get('satelite')
        default_bands = ses.get('bands')
        default_index = ses.get('indexes')
        filename = ses.get('points')
        print(default_satlites)
        print(default_bands)
        print(default_index)
    
    return redirect(url_for('index'))

        # return render_template('index.html', 
        #                         form = form, 
        #                         selectSatelite = default_satlites,
        #                         selectBand = default_bands,
        #                         selectIndex = default_index,
        #                         #map=map,
        #                         mapName = filename
        #                     )

@app.after_request
def adding_header_content(head):
    head.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    head.headers["Pragma"] = "no-cache"
    head.headers["Expires"] = "0"
    head.headers['Cache-Control'] = 'public, max-age=0'
    return head

if __name__ == '__main__':
    app.run(debug=True)