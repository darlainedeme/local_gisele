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
import ee
import requests
import json
import tempfile
import uuid
from folium.features import DivIcon
from folium.plugins import MarkerCluster
import rioxarray
from pystac_client import Client
from shapely.geometry import Polygon, mapping
import rasterio
import pystac

warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

# Initialize Earth Engine API
def initialize_ee(online, json_data=None):
    if online:
        json_object = json.loads(json_data, strict=False)
        service_account = json_object['client_email']
        json_object = json.dumps(json_object)
        credentials = ee.ServiceAccountCredentials(service_account, key_data=json_object)
        ee.Initialize(credentials)
    else:
        ee.Initialize()

initialize_ee(online=True, json_data=st.secrets["json_data"])

st.set_page_config(layout="wide")

# Define constants
EXTENSIONS_TO_CHECK = ('.shp', '.gpkg', '.geojson')
COLOURS = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 
           'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
WHICH_MODES = ['By address', 'By coordinates', 'Upload file']

which_mode = st.sidebar.selectbox('Select mode', WHICH_MODES, index=2)
st.title("Local GISEle")

# Tags for OSM data
TAGS = {'building': True}

def create_map(latitude, longitude, sentence, area_gdf, gdf_edges, buildings_gdf, pois, lights):
    m = folium.Map(location=[latitude, longitude], zoom_start=25)

    # Add base tiles
    tile_layers = [
        ('http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}', 'Google Maps'),
        ('http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}', 'Google Hybrid'),
        ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 'Esri Satellite')
    ]
    
    for tile_url, tile_name in tile_layers:
        folium.TileLayer(
            tiles=tile_url,
            attr=tile_name,
            name=tile_name,
            overlay=False,
            control=True
        ).add_to(m)

    # Add feature groups
    if area_gdf is not None:
        add_geojson_feature(m, area_gdf, 'Selected Area', 'blue')
        
    if gdf_edges is not None:
        add_geojson_feature(m, gdf_edges, 'Roads', 'orange')

    if buildings_gdf is not None:
        add_buildings(m, buildings_gdf)
        
    if lights is not None:
        add_lights_overlay(m, lights)

    if pois is not None:
        add_pois(m, pois)

    if sentence:
        add_marker(m, latitude, longitude, sentence)

    # Add map plugins
    add_map_plugins(m)

    # Display the map
    folium_static(m, width=1500, height=800)

def add_geojson_feature(map_obj, gdf, name, color):
    feature_group = folium.FeatureGroup(name=name, show=True)
    style = {'fillColor': color, 'color': color}
    folium.GeoJson(gdf.to_json(), name=name, style_function=lambda x: style).add_to(feature_group)
    feature_group.add_to(map_obj)

def add_buildings(map_obj, buildings_gdf):
    feature_group = folium.FeatureGroup(name='Buildings', show=False)
    style = {'fillColor': 'green', 'color': 'green'}
    folium.GeoJson(buildings_gdf.to_json(), name='Buildings', style_function=lambda x: style).add_to(feature_group)
    feature_group.add_to(map_obj)

    marker_cluster = MarkerCluster(name='Buildings clusters').add_to(map_obj)
    buildings_gdf['geometry'] = buildings_gdf.centroid
    for _, row in buildings_gdf.iterrows():
        folium.Marker([row.geometry.y, row.geometry.x]).add_to(marker_cluster)

def add_lights_overlay(map_obj, lights):
    folium.raster_layers.ImageOverlay(
        name="Probability of being electrified",
        image=np.moveaxis(lights, 0, -1),
        opacity=0.5,
        bounds=bbox,
        interactive=True,
        show=True
    ).add_to(map_obj)

def add_pois(map_obj, pois):
    feature_group = folium.FeatureGroup(name='Points of interest', show=True)
    style = {'fillColor': 'blue', 'color': 'blue'}
    folium.GeoJson(pois.to_json(), name='Points of interest', tooltip=folium.GeoJsonTooltip(aliases=['Info:'], fields=['amenity']),
                   style_function=lambda x: style).add_to(feature_group)
    feature_group.add_to(map_obj)

    info_group = folium.FeatureGroup(name='Info', show=False)
    for _, row in pois.iterrows():
        depot_node = (row.geometry.y, row.geometry.x) if 'POINT' in str(row['geometry']) else (row.geometry.centroid.y, row.geometry.centroid.x)
        folium.map.Marker(
            depot_node,
            icon=DivIcon(icon_size=(30,30), icon_anchor=(5,14), html=f'<div style="font-size: 14pt">{str(row["amenity"])}</div>')
        ).add_to(info_group)
    info_group.add_to(map_obj)

def add_marker(map_obj, latitude, longitude, sentence):
    tooltip = sentence
    folium.Marker([latitude, longitude], popup=sentence, tooltip=tooltip).add_to(map_obj)

def add_map_plugins(map_obj):
    folium.plugins.Draw(export=True, filename='data.geojson', position='topleft').add_to(map_obj)
    folium.plugins.Fullscreen(position='topleft', title='Full Screen', title_cancel='Exit Full Screen').add_to(map_obj)
    folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='meters', secondary_length_unit='miles', 
                                  primary_area_unit='sqmeters', secondary_area_unit='acres').add_to(map_obj)
    folium.LayerControl().add_to(map_obj)

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

    return gdf, file_path

def fetch_pois(polygon, tags):
    try:
        pois = ox.geometries.geometries_from_polygon(polygon, tags=tags)
        return pois
    except ox._errors.InsufficientResponseError as e:
        st.sidebar.error(f"Failed to fetch points of interest: {e}")
        return None
    except Exception as e:
        st.sidebar.error(f"An unexpected error occurred: {e}")
        return None

# Mode selection
if which_mode == 'By address':  
    geolocator = Nominatim(user_agent="example app")
    sentence = st.sidebar.text_input('Scrivi il tuo indirizzo:', value='B12 Bovisa') 
    location = geolocator.geocode(sentence)
    if location:
        create_map(location.latitude, location.longitude, sentence, None, None, None, None, None)

elif which_mode == 'By coordinates':  
    latitude = st.sidebar.text_input('Latitude:', value=45.5065) 
    longitude = st.sidebar.text_input('Longitude:', value=9.1598) 
    if latitude and longitude:
        create_map(float(latitude), float(longitude), str((float(latitude), float(longitude))), None, None, None, None, None)

elif which_mode == 'Upload file':
    which_buildings_list = ['OSM', 'Google', 'Microsoft']
    which_buildings = st.sidebar.selectbox('Select building dataset', which_buildings_list, index=1)
    data = st.sidebar.file_uploader("Draw the interest area directly on the chart or upload a GIS file.", type=["geojson", "kml", "zip", "gpkg"])
    if data:
        data_gdf, file_path = uploaded_file_to_gdf(data)
        data_gdf_2 = data_gdf.copy()
        data_gdf_2['geometry'] = data_gdf_2.geometry.buffer(0.004)
        
        # Fetch POIs and buildings
        pois = fetch_pois(data_gdf.iloc[0]['geometry'], {'amenity': True})
        G = ox.graph_from_polygon(data_gdf_2.iloc[0]['geometry'], network_type='all', simplify=True)
        gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
        gdf_edges = gpd.clip(gdf_edges, data_gdf)
        
        if which_buildings == 'OSM':
            buildings = ox.geometries_from_polygon(data_gdf.iloc[0]['geometry'], TAGS)
            buildings = buildings.loc[:, buildings.columns.str.contains('addr:|geometry')]
            buildings = buildings.loc[buildings.geometry.type == 'Polygon']
            buildings_save = buildings.applymap(lambda x: str(x) if isinstance(x, list) else x)
        elif which_buildings == 'Google':
            g = json.loads(data_gdf.to_json())
            coords = np.array(g['features'][0]['geometry']['coordinates'])
            geom = ee.Geometry.Polygon(coords[0].tolist())
            fc = ee.FeatureCollection('GOOGLE/Research/open-buildings/v2/polygons')
            buildings = fc.filter(ee.Filter.intersects('.geo', geom))
            download_url = buildings.getDownloadURL('geojson', None, 'buildings')
            chunk_size = 128
            r = requests.get(download_url, stream=True)
            with open('data/buildings.geojson', 'wb') as fd:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    fd.write(chunk)
            buildings_save = gpd.read_file('data/buildings.geojson')
        elif which_buildings == 'Microsoft':
            st.write('Feature under development')

        # Create map with the gathered data
        create_map(data_gdf.centroid.y, data_gdf.centroid.x, None, data_gdf, gdf_edges, buildings_save, pois, None)

# Sidebar information
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
