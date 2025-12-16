import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import transform
import pyproj

def process_user_drawing(draw_data):
    """
    Parses the GeoJSON output from Folium Draw and extracts the first LineString.
    """
    if not draw_data or 'features' not in draw_data:
        return None
    
    # Extract the first feature drawn
    features = draw_data['features']
    if not features:
        return None
        
    # We only care about LineStrings
    geom_type = features[0]['geometry']['type']
    coords = features[0]['geometry']['coordinates']
    
    if geom_type == 'LineString':
        return LineString(coords) # format is (lon, lat)
    else:
        # In case user draws a polygon, just take the boundary as a line
        return None

def generate_transects(line_geom, spacing_m=1, length_m=20):
    """
    1. Projects WGS84 line to local UTM.
    2. Interpolates points at `spacing_m`.
    3. Calculates perpendicular vectors.
    4. Creates transect lines of `length_m`.
    5. Projects back to WGS84.
    """
    # Create a simple GDF to utilize GeoPandas projection tools
    gdf = gpd.GeoDataFrame(geometry=[line_geom], crs="EPSG:4326")
    
    # Automatically estimate the best projected CRS (UTM) for this location
    # accurate_crs is usually a UTM zone based on the geometry centroid
    utm_crs = gdf.estimate_utm_crs()
    
    # Project to Meters
    line_utm = gdf.to_crs(utm_crs).geometry.iloc[0]
    
    # Interpolate points along the line
    total_len = line_utm.length
    distances = np.arange(0, total_len, spacing_m)
    points_utm = [line_utm.interpolate(d) for d in distances]
    
    transect_lines = []
    
    for i, pt in enumerate(points_utm):
        # Determine tangent vector (direction of the line at this point)
        # For the last point, look backward; otherwise look forward
        if i < len(points_utm) - 1:
            p2 = points_utm[i+1]
            dx = p2.x - pt.x
            dy = p2.y - pt.y
        else:
            p_prev = points_utm[i-1]
            dx = pt.x - p_prev.x
            dy = pt.y - p_prev.y
            
        # Normalize vector
        mag = np.sqrt(dx**2 + dy**2)
        if mag == 0: continue
        dx /= mag
        dy /= mag
        
        # Rotate 90 degrees to get Normal vector (-dy, dx)
        nx, ny = -dy, dx
        
        # Create offsets
        half_len = length_m / 2
        p_left = Point(pt.x + nx * half_len, pt.y + ny * half_len)
        p_right = Point(pt.x - nx * half_len, pt.y - ny * half_len)
        
        transect_lines.append(LineString([p_left, p_right]))
        
    # Create GDF in UTM
    transects_utm = gpd.GeoDataFrame(geometry=transect_lines, crs=utm_crs)
    
    # Add ID and Distance metadata
    transects_utm['transect_id'] = range(len(transects_utm))
    transects_utm['dist_along'] = distances[:len(transects_utm)]
    
    # Project back to Lat/Lon for mapping/export
    return transects_utm.to_crs("EPSG:4326")