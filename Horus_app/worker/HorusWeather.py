import requests #pt OWM
import json

# OpenWeatheMap key
OWM_api_key = "8da28ca33181ad8b7dd71cd046041d18"

def get_OWM_data(start_coords):
    # start coords must be a tuple wit (lat, lon)
    #print("         Latitude: {}\n         Longitude: {}".format(start_coords[1], start_coords[0]))
    url = "https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}&units=metric".format(start_coords[1], start_coords[0], OWM_api_key)

    response = requests.get(url)
    OWMdata = json.loads(response.text)
    mainOWMdata = OWMdata.get('main')
    temp = mainOWMdata.get('temp')
    pres = mainOWMdata.get('pressure')
    hum = mainOWMdata.get('humidity')
    
    return {'TEMP': temp, 'PRES': pres,'HUM' : hum}
