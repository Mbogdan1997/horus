import folium
from folium import plugins
from HorusSettings import start_coords, tolerance
from HorusSettings import TEMPLATE_FOLDER, UPLOAD_FOLDER
from folium.plugins import MarkerCluster
# from shapely.geometry import Polygon
# import geopandas as gpd
import json


# def get_bounding_box_coord(lat, lon):
#     lleft_lng, lleft_lat = (1 - tolerance) * min(lon), (1 - tolerance) * min(lat)
#     urright_lng, uright_lat = (1 + tolerance) * max(lon), (1 + tolerance) * max(lat)
#     x = [lleft_lng, urright_lng, urright_lng, lleft_lng]
#     y = [lleft_lat, lleft_lat, uright_lat, uright_lat]
#     polygon_points = Polygon(zip(x,y))
#     crs = {'init': 'epsg:4326'}
#     polygon = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[polygon_points]) 
#     #df_bbox = [lleft_lng, lleft_lat, urright_lng, uright_lat]
#     # print('   - Data frame bounding box: {}'.format(df_bbox))
#     return polygon


def mapGenerator(save = True , mapfilename = 'map.html'):
    # draw tools
    map_draw = folium.Map(location = start_coords,
                          zoom_start = 13,
                          tiles = 'OpenStreetMap' 
                         )

    # # export=True exports the drawn shapes as a geojson file
    # draw = plugins.Draw(export = True,
    #                     filename = 'my_data.geojson',
    #                     position = 'topleft',
    #                     draw_options = {'polyline': {'allowIntersection': False}},
    #                     edit_options = {'poly': {'allowIntersection': False}}
    #                    )

    # add latitude and longitude tool to map
    map_draw.add_child(folium.LatLngPopup())

    # # add draw tools to map
    # draw.add_to(map_draw)

    if save == True:
        map_draw.save(mapfilename)
        return map_draw
    else:
        return map_draw

def mapPOIUpdate(filename, outputfile):
    print(filename, outputfile)
    # generating new map with the points from the selected file
    m = folium.Map(location = start_coords,
                          zoom_start = 13,
                          tiles = 'OpenStreetMap', height='100%' 
                         )
    
    # import map points
    marker_cluster = MarkerCluster().add_to(m)
    try:
        with open(UPLOAD_FOLDER + filename, 'r') as fp:
            measurement_points = json.load(fp)
    except:
        print('File {} not found.'.format(UPLOAD_FOLDER + filename))
        measurement_points = []
    lat, lon, labels, popups = [], [], [], []
    for mp in measurement_points:
        lat.append(mp.get('lat'))
        lon.append(mp.get('lon'))
        labels.append(mp.get('label'))
        popups.append('Point {0}<br>Lon:{1}<br>Lat:{2}'.format(mp.get('pointname'), mp.get('lon'), mp.get('lat')))

    locations = list(zip(lat, lon))
    points = list(zip(lat, lon, labels))
    
    marker_cluster = MarkerCluster(
        locations=locations, popups=popups,
        overlay=True,
        control=True
    )

    marker_cluster.add_to(m)

    # poly = get_bounding_box_coord(lat,lon)
    # poly2 = poly.convex_hull

    # folium.GeoJson(poly).add_to(m)
    # folium.GeoJson(poly2).add_to(m)
    folium.LayerControl().add_to(m)

    m.save(TEMPLATE_FOLDER + outputfile)
    print("new map saved at {}".format(TEMPLATE_FOLDER + outputfile))

    return m, points


