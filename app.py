import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
import json
import transect_utils as tu # Import our utils file
import tempfile
import shutil
import os

st.set_page_config(layout="wide", page_title="Transect Generator")

st.title("📍 Spatial Transect Generator")
st.markdown("Draw a baseline on the map. The app will generate perpendicular transects at **1m intervals**.")

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Settings")
    transect_len = st.number_input("Transect Length (m)", min_value=5, max_value=500, value=20)
    transect_interval = st.number_input("Interval Spacing (m)", min_value=0.5, max_value=100.0, value=1.0)
    
    st.info("Instructions:\n1. Use the Polyline tool (top left on map) to draw your baseline.\n2. Click 'Generate Transects'.")

# --- MAP SETUP ---
# Enable scrollWheelZoom explicitly. 
# We disable doubleClickZoom because double-clicking is used to 'finish' a line in drawing mode.
m = folium.Map(
    location=[32.87, -117.25], 
    zoom_start=15, 
    tiles=None,
    scrollWheelZoom=True,
    doubleClickZoom=False  
)

# 1. Add Street Map FIRST (so it sits in the background list)
folium.TileLayer(
    'OpenStreetMap',
    name='Street Map',
    control=True
).add_to(m)

# 2. Add Satellite Imagery SECOND (so it becomes the active default)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Satellite',
    overlay=False,
    control=True
).add_to(m)

# Add Layer Control to switch between them
folium.LayerControl().add_to(m)

# Setup the Draw Tool
# We add a 'draw' configuration to allow some geometry editing
draw = Draw(
    draw_options={
        'polyline': {
            'allowIntersection': False,  # Optional: prevents drawing self-intersecting loops
            'showLength': True
        },
        'polygon': False,
        'rectangle': False,
        'circle': False,
        'marker': False,
        'circlemarker': False
    },
    edit_options={'edit': True}
)
draw.add_to(m)

# --- MAP DISPLAY & DRAW CAPTURE ---
# This variable captures the user interaction
output = st_folium(m, width=None, height=500)

# --- PROCESS LOGIC ---
if output and "all_drawings" in output and output["all_drawings"]:
    # Get the latest drawing
    drawings = output["all_drawings"]
    
    # Check if we have features
    if len(drawings) > 0:
        # We take the last drawn feature
        last_drawing = {'features': [drawings[-1]], 'type': 'FeatureCollection'}
        
        # Convert to Shapely Geometry
        line_geom = tu.process_user_drawing(last_drawing)
        
        if line_geom:
            if st.button("⚡ Generate Transects", type="primary"):
                with st.spinner("Calculating geometry..."):
                    try:
                        # 1. Run the math (Now returns UTM)
                        result_gdf = tu.generate_transects(
                            line_geom, 
                            spacing_m=transect_interval, 
                            length_m=transect_len
                        )
                        
                        st.success(f"Generated {len(result_gdf)} transects!")
                        
                        # Show which CRS was used (e.g., EPSG:32611 for UTM Zone 11N)
                        st.info(f"Export Projection: {result_gdf.crs.name} ({result_gdf.crs.to_string()})")

                        # Display the data - coordinates will now look like "328000, 4800000" (Meters)
                        st.dataframe(result_gdf.drop(columns='geometry').head())

                        # --- SHAPEFILE EXPORT LOGIC ---
                        with tempfile.TemporaryDirectory() as tmp_dir:
                            shp_path = os.path.join(tmp_dir, "transects.shp")
                            
                            # This now saves the .prj file with the UTM definition
                            result_gdf.to_file(shp_path)
                            
                            zip_path = shutil.make_archive(os.path.join(tmp_dir, "transects"), 'zip', tmp_dir)
                            
                            with open(zip_path, "rb") as f:
                                zip_data = f.read()

                            st.download_button(
                                label="📥 Download Shapefile (UTM)",
                                data=zip_data,
                                file_name="transects_utm.zip",
                                mime="application/zip"
                            )
                        
                        # OPTIONAL: If you ever want to map these results back onto Folium,
                        # you would need to create a temporary copy projected to WGS84:
                        # map_gdf = result_gdf.to_crs("EPSG:4326")
                        # folium.GeoJson(map_gdf).add_to(m)

                    except Exception as e:
                        st.error(f"Error calculating transects: {e}")
        else:
            st.warning("Please draw a Polyline, not a polygon or marker.")