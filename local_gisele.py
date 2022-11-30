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



st.set_page_config(layout="wide")
extensionsToCheck = ('.shp', '.gpkg', '.geojson')
colours = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']

st.write("Ciao")
