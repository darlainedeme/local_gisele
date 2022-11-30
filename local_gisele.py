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


st.set_page_config(layout="wide")
extensionsToCheck = ('.shp', '.gpkg', '.geojson')
colours = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']

which_modes = ['By Address', 'By coordinates']
which_mode = st.sidebar.selectbox('Select mode', which_modes, index=1)

def create_map(latitude, longitude, sentence):
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
    
    folium_static(m)
    
if which_mode == 'By Address':  
    geolocator = Nominatim(user_agent="example app")
    
    sentence = st.sidebar.text_input('Scrivi il tuo indirizzo:', value='B12 Bovisa') 

    try:
       location = geolocator.geocode(sentence)
       
       if sentence:
           create_map(location.latitude, location.longitude, sentence)
           
    except:
            st.write('No location found! Please retry')
            
elif which_mode == 'By coordinates':  
    latitude = st.sidebar.text_input('Latitude:', value=15) 
    longitude = st.sidebar.text_input('Longitude:', value=15) 
    
    sentence = (float(latitude), float(longitude))
    if latitude and longitude:
        create_map(latitude, longitude, sentence)
    
    
    
    
