import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Geocoder
import geopandas as gpd
import json
import transect_utils as tu # Import our utils file
import tempfile
import shutil
import os

st.set_page_config(layout="wide", page_title="Transect Generator")

st.title("📍 Spatial Transect Generator")
st.markdown("Draw a baseline on the map. The app will generate perpendicular transects at **1m intervals**.")

# --- SESSION STATE INITIALIZATION ---
if 'transect_gdf' not in st.session_state:
    st.session_state.transect_gdf = None
if 'points_gdf' not in st.session_state:
    st.session_state.points_gdf = None

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Geometry Settings")
    transect_len = st.number_input("Transect Length (m)", min_value=5, max_value=500, value=20)
    transect_interval = st.number_input("Interval Spacing (m)", min_value=0.5, max_value=100.0, value=1.0)
    
    st.divider()
    st.header("Advanced Smoothing")
    smoothing_window = st.slider(
        "Smoothing Window", 
        min_value=1, 
        max_value=25, 
        value=9, 
        step=2,
        help="Size of the rolling window for vector smoothing. Higher values = smoother turns but less precision at corners."
    )
    
    st.divider()
    st.header("Export Options")
    export_format = st.selectbox(
        "File Format",
        options=["ESRI Shapefile (.shp)", "GeoJSON (.geojson)", "KML (.kml)", "GeoPackage (.gpkg)"]
    )
    
    st.info("Instructions:\n1. Use the Search button (magnifying glass) to find your location.\n2. Use the Polyline tool to draw your baseline.\n3. Click 'Generate Transects'.")

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
    control=True,
    maxNativeZoom=19,
    maxZoom=22
).add_to(m)

# --- ADD GEOCODER ---
Geocoder().add_to(m)

# --- LOAD AND DISPLAY MOP LINES FROM KML ---
try:
    # Enable KML driver support - try multiple methods for compatibility
    try:
        import fiona
        fiona.drvsupport.supported_drivers['KML'] = 'rw'
    except:
        try:
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
        except:
            pass

    # Load the MOP lines KML file
    mop_lines = gpd.read_file('MOPs-SD.kml')

    # Make sure it's in WGS84 for display
    if mop_lines.crs is None:
        mop_lines.set_crs(epsg=4326, inplace=True)
    else:
        mop_lines = mop_lines.to_crs(epsg=4326)

    # Add MOP lines to map
    folium.GeoJson(
        mop_lines,
        name="MOP Survey Lines",
        style_function=lambda x: {'color': '#1FF4FB', 'weight': 3, 'opacity': 0.7},
        tooltip=folium.GeoJsonTooltip(fields=['Name'], aliases=['Line:'])
    ).add_to(m)
except Exception as e:
    st.warning(f"Could not load MOP lines: {e}")

# --- ADD GENERATED LAYERS IF EXIST ---
if st.session_state.transect_gdf is not None:
    try:
        # Reproject to WGS84 for display
        t_disp = st.session_state.transect_gdf.to_crs(epsg=4326)
        folium.GeoJson(
            t_disp,
            name="Generated Transects",
            style_function=lambda x: {'color': '#FF4B4B', 'weight': 2},
            tooltip="Transect Line"
        ).add_to(m)
    except Exception as e:
        st.error(f"Error displaying transects: {e}")

if st.session_state.points_gdf is not None:
    try:
        p_disp = st.session_state.points_gdf.to_crs(epsg=4326)
        folium.GeoJson(
            p_disp,
            name="Baseline Points",
            marker=folium.CircleMarker(radius=2, color='blue', fill=True, fill_opacity=0.8),
            tooltip="Baseline Point"
        ).add_to(m)
    except Exception as e:
        st.error(f"Error displaying points: {e}")

# Add Layer Control to switch between them
folium.LayerControl().add_to(m)

# Setup the Draw Tool
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
output = st_folium(m, width=None, height=500)

# --- PROCESS LOGIC ---
if output and "all_drawings" in output and output["all_drawings"]:
    drawings = output["all_drawings"]
    
    if len(drawings) > 0:
        last_drawing = {'features': [drawings[-1]], 'type': 'FeatureCollection'}
        line_geom = tu.process_user_drawing(last_drawing)
        
        if line_geom:
            if st.button("⚡ Generate Transects", type="primary"):
                with st.spinner("Calculating geometry..."):
                    try:
                        # 1. Run the math
                        transect_gdf, points_gdf = tu.generate_transects(
                            line_geom, 
                            spacing_m=transect_interval, 
                            length_m=transect_len,
                            smoothing_window=smoothing_window
                        )
                        
                        # 2. Update Session State
                        st.session_state.transect_gdf = transect_gdf
                        st.session_state.points_gdf = points_gdf
                        
                        # 3. Rerun to update map
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error calculating transects: {e}")
        else:
            st.warning("Please draw a Polyline, not a polygon or marker.")

# --- RESULTS DISPLAY (PERSISTENT) ---
if st.session_state.transect_gdf is not None:
    st.divider()
    st.subheader("Results")
    
    st.success(f"Generated {len(st.session_state.transect_gdf)} transects and points!")
    st.info(f"Export Projection: {st.session_state.transect_gdf.crs.name}")

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Transect Lines")
        st.dataframe(st.session_state.transect_gdf.drop(columns='geometry').head())
    with col2:
        st.caption("Baseline Points")
        st.dataframe(st.session_state.points_gdf.drop(columns='geometry').head())

    # --- EXPORT LOGIC ---
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Prepare filenames
        base_name = "transects_bundle"
        
        if "Shapefile" in export_format:
            # SHAPEFILE: Requires a folder structure and zipping
            st.session_state.transect_gdf.to_file(os.path.join(tmp_dir, "transect_lines.shp"))
            st.session_state.points_gdf.to_file(os.path.join(tmp_dir, "baseline_points.shp"))
            zip_path = shutil.make_archive(os.path.join(tmp_dir, base_name), 'zip', tmp_dir)
            mime_type = "application/zip"
            file_ext = ".zip"
            with open(zip_path, "rb") as f:
                data = f.read()

        elif "GeoJSON" in export_format:
            # GeoJSON: Single file per layer, we zip them together for convenience
            st.session_state.transect_gdf.to_file(os.path.join(tmp_dir, "transect_lines.geojson"), driver='GeoJSON')
            st.session_state.points_gdf.to_file(os.path.join(tmp_dir, "baseline_points.geojson"), driver='GeoJSON')
            zip_path = shutil.make_archive(os.path.join(tmp_dir, base_name), 'zip', tmp_dir)
            mime_type = "application/zip"
            file_ext = ".zip"
            with open(zip_path, "rb") as f:
                data = f.read()

        elif "KML" in export_format:
            # KML: Requires reprojecting to WGS84 first
            # Driver support for KML in geopandas/fiona can be tricky, often requiring 'fiona.drvsupport'. 
            # We will use a safe fallback or enable it if needed. 
            # Note: GeoPandas > 0.9 usually handles this if correct driver is specified.
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
            
            t_kml = st.session_state.transect_gdf.to_crs(epsg=4326)
            p_kml = st.session_state.points_gdf.to_crs(epsg=4326)
            
            t_kml.to_file(os.path.join(tmp_dir, "transect_lines.kml"), driver='KML')
            p_kml.to_file(os.path.join(tmp_dir, "baseline_points.kml"), driver='KML')
            
            zip_path = shutil.make_archive(os.path.join(tmp_dir, base_name), 'zip', tmp_dir)
            mime_type = "application/zip"
            file_ext = ".zip"
            with open(zip_path, "rb") as f:
                data = f.read()
                
        elif "GeoPackage" in export_format:
            # GEOPACKAGE: Single file, multiple layers possible
            gpkg_path = os.path.join(tmp_dir, "transects.gpkg")
            st.session_state.transect_gdf.to_file(gpkg_path, layer='transect_lines', driver="GPKG")
            st.session_state.points_gdf.to_file(gpkg_path, layer='baseline_points', driver="GPKG")
            
            with open(gpkg_path, "rb") as f:
                data = f.read()
            mime_type = "application/x-sqlite3" # Standard mime for gpkg
            file_ext = ".gpkg"

        st.download_button(
            label=f"📥 Download Results ({export_format})",
            data=data,
            file_name=f"transects{file_ext}",
            mime=mime_type
        )