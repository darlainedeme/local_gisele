    # -*- coding: utf-8 -*-
"""
Created on Wed Nov 30 14:18:38 2022

@author: EDEME_D
"""
import os
import streamlit as st
import matplotlib.pyplot as plt
from streamlit_folium import folium_static
import folium
import geopandas as gpd

import numpy as np 
from geopy.geocoders import Nominatim
import fiona
import warnings
import osmnx as ox
#import geemap.foliumap as geemap
import ee
import requests
import json
import tempfile
import uuid
from folium.features import DivIcon
from folium.plugins import MarkerCluster
import rioxarray
from pystac_client import Client
import planetary_computer as pc
from shapely.geometry import Polygon, mapping
import rasterio
import warnings
import pystac

warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

online = True
if online:
    json_data = st.secrets["json_data"]
    service_account = st.secrets["service_account"]
    
    # Preparing values
    json_object = json.loads(json_data, strict=False)
    service_account = json_object['client_email']
    json_object = json.dumps(json_object)
    # Authorising the app
    credentials = ee.ServiceAccountCredentials(service_account, key_data=json_object)
    ee.Initialize(credentials)

else:
    ee.Initialize()

warnings.filterwarnings("ignore")
st.set_page_config(layout="wide")

extensionsToCheck = ('.shp', '.gpkg', '.geojson')
colours = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']

which_modes = ['By address', 'By coordinates', 'Upload file']
which_mode = st.sidebar.selectbox('Select mode', which_modes, index=2)

st.title("Local GISEle")


# List key-value pairs for tags
tags = {'building': True}   

    
def create_map(latitude, longitude, sentence, area_gdf, gdf_edges, buildings_gdf, pois, lights):
    m = folium.Map(location=[latitude, longitude], zoom_start=25)
    
    tile = folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=False,
        control=True
    ).add_to(m)

    tile = folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Hybrid',
        overlay=False,
        control=True
    ).add_to(m)
    
    tile = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    

# =============================================================================
#     tile = folium.TileLayer('Mapbox Bright').add_to(m)
#     
#     tile = folium.TileLayer('Mapbox Control Room').add_to(m)
#     
#     tile = folium.TileLayer('stamentoner').add_to(m)
#     
#     tile = folium.TileLayer('cartodbdark_matter').add_to(m)
#     
# =============================================================================
    
    if sentence:
        feature_group_3 = folium.FeatureGroup(name=sentence, show=True)
                    
    new_lat = latitude
    new_long = longitude
    
    if area_gdf is not None:
        feature_group_1 = folium.FeatureGroup(name='Selected Area', show=True)
        style1 = {'fillColor': 'blue', 'color': 'blue'}    
         
        folium.GeoJson(area_gdf.to_json(), name='Selected Area',
                    style_function=lambda x: style1).add_to(feature_group_1)
        
    if gdf_edges is not None:
        feature_group_2 = folium.FeatureGroup(name='Roads', show=True)
        style2 = {'fillColor': 'orange', 'color': 'orange'}    
         
        folium.GeoJson(gdf_edges.to_json(), name='Roads',
                    style_function=lambda x: style2).add_to(feature_group_2)

    if buildings_gdf is not None:
        feature_group_4 = folium.FeatureGroup(name='Buildings', show=False)
        style4 = {'fillColor': 'green', 'color': 'green'}    
         
        folium.GeoJson(buildings_gdf.to_json(), name='Buildings',
                    style_function=lambda x: style4).add_to(feature_group_4)
        
        feature_group_7 = folium.FeatureGroup(name='Buildings clusters', show=True)
        
        marker_cluster = MarkerCluster(name='Buildings clusters').add_to(m)
        buildings_gdf['geometry'] = buildings_gdf.centroid
        for point in range(0, len(buildings_gdf)):
            # folium.Marker([infrastructure_gdf.iloc[point].geometry.y, infrastructure_gdf.iloc[point].geometry.x], popup=infrastructure_gdf.iloc[point]['Plant']).add_to(marker_cluster)
            folium.Marker([buildings_gdf.iloc[point].geometry.y, buildings_gdf.iloc[point].geometry.x]).add_to(marker_cluster)

    if lights is not None:
        folium.raster_layers.ImageOverlay(
            name="Probability of being electrified",
            image=lights,
            opacity=1,
            bounds=[[create_map.bounds.values.tolist()[0][0], 
         create_map.bounds.values.tolist()[0][1]],
        [create_map.bounds.values.tolist()[0][2],
         create_map.bounds.values.tolist()[0][3]]],
            show=True
        ).add_to(m)

    if pois is not None:
        feature_group_5 = folium.FeatureGroup(name='Points of interest', show=True)
        style5 = {'fillColor': 'blue', 'color': 'blue'}    
        
        
        folium.GeoJson(pois.to_json(), name='Points of interest', tooltip=folium.GeoJsonTooltip(aliases=['Info:'],fields=['amenity']),
                    style_function=lambda x: style5).add_to(feature_group_5)

        
        feature_group_6 = folium.FeatureGroup(name='Info', show=False)
        for index, row in pois.iterrows():
            
            if 'POINT' in str(row['geometry']):
                depot_node = (row.geometry.y, row.geometry.x)
            
            else:
                depot_node = (row.geometry.centroid.y, row.geometry.centroid.x)
                
            folium.map.Marker(depot_node,
                              icon=DivIcon(
                                  icon_size=(30,30),
                                  icon_anchor=(5,14),
                                  html=f'<div style="font-size: 14pt">%s</div>' % str(row['amenity'])                              )
                             ).add_to(feature_group_6)
    
                 
 
    if area_gdf is not None:
        feature_group_1.add_to(m)
                       
    if buildings_gdf is not None:
        feature_group_4.add_to(m)

    if gdf_edges is not None:
        feature_group_2.add_to(m)

    if pois is not None:
        feature_group_5.add_to(m) 
        feature_group_6.add_to(m) 
                    
    if sentence:
        # add marker
        tooltip = sentence
        folium.Marker(
            [new_lat, new_long], popup=sentence, tooltip=tooltip
        ).add_to(feature_group_3)
        feature_group_3.add_to(m)
    
    folium.plugins.Draw(export=True, filename='data.geojson', position='topleft', draw_options=None,
                        edit_options=None).add_to(m)
    folium.plugins.Fullscreen(position='topleft', title='Full Screen', title_cancel='Exit Full Screen',
                              force_separate_button=False).add_to(m)
    folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='meters', secondary_length_unit='miles',
                                  primary_area_unit='sqmeters', secondary_area_unit='acres').add_to(m)
    folium.LayerControl().add_to(m)
    
    # Displaying a map         
    
    folium_static(m, width=1500, height=800)
    


@st.cache(allow_output_mutation=True)
def uploaded_file_to_gdf(data):
    _, file_extension = os.path.splitext(data.name)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(tempfile.gettempdir(), f"{file_id}{file_extension}")

    with open(file_path, "wb") as file:
        file.write(data.getbuffer())

    if file_path.lower().endswith(".kml"):
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        gdf = gpd.read_file(file_path, driver="KML")
    
    elif file_path.lower().endswith(".gpkg"):
        gdf = gpd.read_file(file_path, driver="GPKG")
        
    else:
        gdf = gpd.read_file(file_path)

    return gdf


if which_mode == 'By address':  
    geolocator = Nominatim(user_agent="example app")
    
    sentence = st.sidebar.text_input('Scrivi il tuo indirizzo:', value='B12 Bovisa') 

    # try:
    location = geolocator.geocode(sentence)

    if sentence:
        create_map(location.latitude, location.longitude, sentence, None, None, None, None)
    
             
           
elif which_mode == 'By coordinates':  
    latitude = st.sidebar.text_input('Latitude:', value=45.5065) 
    longitude = st.sidebar.text_input('Longitude:', value=9.1598) 
    
    sentence = str((float(latitude), float(longitude)))
    if latitude and longitude:
        create_map(latitude, longitude, sentence, None, None, None, None)

        
    
  
elif which_mode == 'Upload file':
    which_buildings_list = ['OSM', 'Google', 'Microsoft']
    which_buildings = st.sidebar.selectbox('Select building dataset', which_buildings_list, index=1)
    
    data = st.sidebar.file_uploader("Draw the interest area directly on the chart or upload a GIS file.",
                                    type=["geojson", "kml", "zip", "gpkg"])

    if data:
        data_gdf = uploaded_file_to_gdf(data)
        data_gdf_2 = data_gdf.copy()
        data_gdf_2['geometry'] = data_gdf_2.geometry.buffer(0.004)
        
        G = ox.graph_from_polygon(data_gdf_2.iloc[0]['geometry'], network_type='all', simplify=True)
        pois = ox.geometries.geometries_from_polygon(data_gdf.iloc[0]['geometry'], tags={'amenity':True})                       
        # pois = pois[['POINT' in e for e in list(pois.geometry.astype(str))]]
        
        if len(pois) == 0:
            pois = None

        gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
        
        gdf_edges = gpd.clip(gdf_edges, data_gdf)
        
        if which_buildings == 'OSM':
            buildings = ox.geometries_from_polygon(data_gdf.iloc[0]['geometry'], tags)
            buildings = buildings.loc[:,buildings.columns.str.contains('addr:|geometry')]
            buildings = buildings.loc[buildings.geometry.type=='Polygon']        
            buildings_save = buildings.applymap(lambda x: str(x) if isinstance(x, list) else x)
        
        elif which_buildings == 'Google':
            g = json.loads(data_gdf.to_json())

            coords = np.array(g['features'][0]['geometry']['coordinates'])
            geom = ee.Geometry.Polygon(coords[0].tolist())
            fc = ee.FeatureCollection('GOOGLE/Research/open-buildings/v2/polygons')
            
            
            buildings = fc.filter(ee.Filter.intersects('.geo', geom))
            
            downloadUrl = buildings.getDownloadURL('geojson', None, 'buildings')
            
            chunk_size=128
            r = requests.get(downloadUrl, stream=True)
            with open('data/buildings.geojson', 'wb') as fd:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    fd.write(chunk)
            
            buildings_save = gpd.read_file('data/buildings.geojson')


            
        elif which_buildings == 'Microsoft':
            st.write('Feature under development')
            # fc = ee.FeatureCollection('projects/sat-io/open-datasets/MSBuildings/Africa')
            
        # gdf_pois = ox.pois.osm_poi_download(polygon=data_gdf)

        
        # importing nighttime lights from HREA on MS Planeraty computer
        
        # Search against the Planetary Computer STAC API
        catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
        
        # Define your area of interest
        aoi = data_gdf_2.iloc[0]['geometry']
        
        # Define your temporal range
        daterange = {"interval": ["2019-01-01", "2019-12-31"]}
        
        # Define your search with CQL2 syntax
        search = catalog.search(filter_lang="cql2-json", filter={
          "op": "and",
          "args": [
            {"op": "s_intersects", "args": [{"property": "geometry"}, mapping(aoi)]},
            {"op": "anyinteracts", "args": [{"property": "datetime"}, daterange]},
            {"op": "=", "args": [{"property": "collection"}, "hrea"]}
          ], 
            "*": {"warnings": "ignore"}
        })
        
        items = search.get_all_items()
        selected_item = items[0]
        
        item_url = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/hrea/items/HREA_Uganda_2019_v1"
        # Load the individual item metadata and sign the assets
        item = pystac.Item.from_file(item_url)
        signed_item = planetary_computer.sign(item)

        # Grab the first item from the search results and sign the assets
        first_item = next(search.items())
        response = requests.get(pc.sign_item(first_item, copy=True).assets.get('lightscore').href)

        # Open one of the data assets (other asset keys to use: 'light-composite', 'night-proportion', 'estimated-brightness')
        asset_href = signed_item.assets["lightscore"].href
        lights = rioxarray.open_rasterio(asset_href)

        # lights = "light.tif"
        # lights = None

        create_map(data_gdf.centroid.y, data_gdf.centroid.x, False, data_gdf, gdf_edges, buildings_save, pois, lights)


# =============================================================================
# fig, ax = plt.subplots(figsize=(15, 15))
# #data_gdf_2.plot(ax=ax, alpha=0.7, color="green")
# data_gdf.plot(ax=ax, alpha=0.7, color="pink")
# gdf_edges.plot(ax=ax, alpha=0.7, color="red")
# buildings_save.plot(ax=ax)
# 
# =============================================================================




st.sidebar.title("About")
st.sidebar.info(
    """
    Web App URL: <https://darlainedeme-local-gisele-local-gisele-bx888v.streamlit.app/>
    GitHub repository: <https://github.com/darlainedeme/local_gisele>
    """
)

st.sidebar.title("Contact")
st.sidebar.info(
    """
    Darlain Edeme: <http://www.e4g.polimi.it/>
    [GitHub](https://github.com/darlainedeme) | [Twitter](https://twitter.com/darlainedeme) | [LinkedIn](https://www.linkedin.com/in/darlain-edeme')
    """
)

    
