import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point
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
        return None

def generate_transects(line_geom, spacing_m=1, length_m=20, smoothing_window=9):
    """
    1. Projects WGS84 line to local UTM.
    2. Interpolates points.
    3. Calculates tangents and SMOOTHS them to prevent crossing.
    4. Creates transect lines.
    5. Returns GDF in UTM.
    """
    # Create GDF to utilize GeoPandas projection tools
    gdf = gpd.GeoDataFrame(geometry=[line_geom], crs="EPSG:4326")
    
    # Estimate best UTM zone
    utm_crs = gdf.estimate_utm_crs()
    
    # Project to Meters
    line_utm = gdf.to_crs(utm_crs).geometry.iloc[0]
    
    # Interpolate points along the line
    total_len = line_utm.length
    distances = np.arange(0, total_len, spacing_m)
    points_utm = [line_utm.interpolate(d) for d in distances]
    
    # --- VECTOR CALCULATION ---
    # We collect all raw tangent vectors first
    tangents = []
    
    for i, pt in enumerate(points_utm):
        # Calculate raw tangent (direction)
        if i < len(points_utm) - 1:
            p2 = points_utm[i+1]
            dx = p2.x - pt.x
            dy = p2.y - pt.y
        else:
            p_prev = points_utm[i-1]
            dx = pt.x - p_prev.x
            dy = pt.y - p_prev.y
            
        # Normalize immediately
        mag = np.sqrt(dx**2 + dy**2)
        if mag > 0:
            tangents.append([dx/mag, dy/mag])
        else:
            tangents.append([0, 0])
            
    tangents = np.array(tangents)

    # --- VECTOR SMOOTHING ---
    # Apply a rolling window average to the vectors.
    # This prevents "snapping" at sharp corners.
    # 'mode=edge' repeats the first/last values so the ends don't get wonky.
    if len(tangents) > smoothing_window:
        # Create a window (e.g., [1/5, 1/5, 1/5, 1/5, 1/5])
        window = np.ones(smoothing_window) / smoothing_window
        
        # Smooth X and Y components separately
        smooth_dx = np.convolve(tangents[:, 0], window, mode='same')
        smooth_dy = np.convolve(tangents[:, 1], window, mode='same')
    else:
        smooth_dx = tangents[:, 0]
        smooth_dy = tangents[:, 1]

    transect_lines = []
    
    for i, pt in enumerate(points_utm):
        dx = smooth_dx[i]
        dy = smooth_dy[i]
        
        # Re-normalize after smoothing (averaging vectors shrinks them)
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
    
    # Add metadata
    transects_utm['transect_id'] = range(len(transects_utm))
    transects_utm['dist_along'] = distances[:len(transects_utm)]
    
    return transects_utm