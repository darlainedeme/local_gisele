# -*- coding: utf-8 -*-
"""
Created on Wed Nov 30 14:18:38 2022

@author: EDEME_D
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from streamlit_folium import folium_static
import folium
import geopandas as gpd
from shapely import wkt
import xarray as xr
import pydeck as pdk
import ast
import numpy as np 
from matplotlib import cm
import random
import time
from folium import Circle
from geopandas.tools import sjoin
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
import fiona
import warnings
import osmnx as ox
import geemap.foliumap as geemap
import ee

warnings.filterwarnings("ignore")
st.set_page_config(layout="wide")

extensionsToCheck = ('.shp', '.gpkg', '.geojson')
colours = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']

which_modes = ['By address', 'By coordinates', 'Upload file']
which_mode = st.sidebar.selectbox('Select mode', which_modes, index=2)

st.title("Local GISEle")


@st.cache(persist=True)
def ee_authenticate(token_name="EARTHENGINE_TOKEN"):
    geemap.ee_initialize(token_name=token_name)

def create_map(latitude, longitude, sentence, area_gdf, gdf_edges):
    m = folium.Map(location=[latitude, longitude], zoom_start=25)
    tile = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
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
        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=False,
        control=True
    ).add_to(m)
    
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
        
    
    # add marker
    tooltip = sentence
    folium.Marker(
        [new_lat, new_long], popup=sentence, tooltip=tooltip
    ).add_to(feature_group_3)
    
    if area_gdf is not None:
        feature_group_1.add_to(m)
    
    if gdf_edges is not None:
        feature_group_2.add_to(m)
        
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
    


@st.cache
def uploaded_file_to_gdf(data):
    import tempfile
    import os
    import uuid

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

    data = st.sidebar.file_uploader("Draw the interest area directly on the chart or upload a GIS file.",
                                    type=["geojson", "kml", "zip", "gpkg"])
    if sentence:
        
        if data:
            data_gdf = uploaded_file_to_gdf(data)            
            G = ox.graph_from_polygon(data_gdf.iloc[0]['geometry'], network_type='all', simplify=True)
            gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
            create_map(location.latitude, location.longitude, sentence, data_gdf, gdf_edges)
        
        else:
            create_map(location.latitude, location.longitude, sentence, None, None)
    
             
               
    #except:
            #st.write('No location found! Please retry')
    
    
            
elif which_mode == 'By coordinates':  
    latitude = st.sidebar.text_input('Latitude:', value=45.5065) 
    longitude = st.sidebar.text_input('Longitude:', value=9.1598) 
    
    sentence = str((float(latitude), float(longitude)))
    if latitude and longitude:
        data = st.sidebar.file_uploader("Draw the interest area directly on the chart or upload a GIS file.",
                                        type=["geojson", "kml", "zip", "gpkg"])

        if data:
            data_gdf = uploaded_file_to_gdf(data)
            G = ox.graph_from_polygon(data_gdf.iloc[0]['geometry'], network_type='all', simplify=True)
            gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
            create_map(data_gdf.centroid.y, data_gdf.centroid.x, sentence, data_gdf, gdf_edges)
            
        else:
            create_map(latitude, longitude, sentence, None, None)

        
    
  
elif which_mode == 'Upload file':
    data = st.sidebar.file_uploader("Draw the interest area directly on the chart or upload a GIS file.",
                                    type=["geojson", "kml", "zip", "gpkg"])

    if data:
        data_gdf = uploaded_file_to_gdf(data)
        G = ox.graph_from_polygon(data_gdf.iloc[0]['geometry'], network_type='all', simplify=True)
        gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
        
        # use microsoft buildings
        country = 'USA'
        state = 'Florida'
        layer_name = state

        fc = ee.FeatureCollection(f'projects/sat-io/open-datasets/MSBuildings/US/{state}')
        st.write(type(fc))
# =============================================================================
#         except:
#             st.error('No data available for the selected state.')
#             
# =============================================================================
        create_map(data_gdf.centroid.y, data_gdf.centroid.x, False, data_gdf, gdf_edges)


















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

    
