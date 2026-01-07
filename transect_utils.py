import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import nearest_points
import pyproj
from typing import Tuple, Optional, Any

def process_user_drawing(draw_data: dict[str, Any]) -> Optional[LineString]:
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

def generate_transects(
    line_geom: LineString,
    spacing_m: float = 1.0,
    length_m: float = 20.0,
    smoothing_window: int = 9,
    mop_lines_gdf: Optional[gpd.GeoDataFrame] = None
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    1. Projects WGS84 line to local UTM.
    2. Interpolates points.
    3. Calculates tangents and SMOOTHS them to prevent crossing.
    4. Creates transect lines.
    5. Optionally snaps to MOP lines and labels accordingly.
    6. Returns GDF in UTM.
    """
    # Create GDF to utilize GeoPandas projection tools
    gdf = gpd.GeoDataFrame(geometry=[line_geom], crs="EPSG:4326")

    # Estimate best UTM zone
    utm_crs = gdf.estimate_utm_crs()

    # Project to Meters
    line_utm = gdf.to_crs(utm_crs).geometry.iloc[0]

    # --- INPUT VALIDATION ---
    total_len = line_utm.length
    if total_len <= spacing_m:
        raise ValueError(
            f"Drawn line length ({total_len:.2f}m) is shorter than the interval spacing ({spacing_m}m). "
            "Please draw a longer line or reduce the interval."
        )

    # --- DETECT MOP LINE INTERSECTIONS ---
    mop_intersections = []  # List of (distance, mop_name, intersection_point)

    if mop_lines_gdf is not None and not mop_lines_gdf.empty:
        # Project MOP lines to same UTM CRS
        mop_utm = mop_lines_gdf.to_crs(utm_crs)

        # Find intersections with each MOP line
        for idx, mop_row in mop_utm.iterrows():
            mop_geom = mop_row.geometry

            # Extend the MOP line in both directions to catch "near misses"
            # This handles cases where the baseline is drawn offshore from where MOP lines end
            extension_distance = 5000  # Extend 5000m (5km) in each direction

            # Get the line's start and end points
            coords = list(mop_geom.coords)
            start_pt = Point(coords[0])
            end_pt = Point(coords[-1])

            # Calculate direction vectors and extend the line
            # Extend at the start
            dx_start = coords[1][0] - coords[0][0]
            dy_start = coords[1][1] - coords[0][1]
            mag_start = np.sqrt(dx_start**2 + dy_start**2)
            if mag_start > 0:
                dx_start /= mag_start
                dy_start /= mag_start
                extended_start = Point(
                    coords[0][0] - dx_start * extension_distance,
                    coords[0][1] - dy_start * extension_distance
                )
            else:
                extended_start = start_pt

            # Extend at the end
            dx_end = coords[-1][0] - coords[-2][0]
            dy_end = coords[-1][1] - coords[-2][1]
            mag_end = np.sqrt(dx_end**2 + dy_end**2)
            if mag_end > 0:
                dx_end /= mag_end
                dy_end /= mag_end
                extended_end = Point(
                    coords[-1][0] + dx_end * extension_distance,
                    coords[-1][1] + dy_end * extension_distance
                )
            else:
                extended_end = end_pt

            # Create extended MOP line
            extended_mop = LineString([(extended_start.x, extended_start.y)] + coords + [(extended_end.x, extended_end.y)])

            if line_utm.intersects(extended_mop):
                # Get intersection point(s)
                intersection = line_utm.intersection(extended_mop)

                # Handle different intersection types
                if isinstance(intersection, Point):
                    points = [intersection]
                elif isinstance(intersection, MultiPoint):
                    points = list(intersection.geoms)
                else:
                    # Skip if intersection is not a point (e.g., overlapping lines)
                    continue

                # For each intersection point, calculate distance along baseline
                for point in points:
                    dist_along = line_utm.project(point)
                    mop_name = mop_row.get('Name', f'MOP_{idx}')
                    mop_intersections.append((dist_along, mop_name, point))

    # Sort MOP intersections by distance
    mop_intersections.sort(key=lambda x: x[0])

    # Create list of all distances (regular intervals + MOP intersections)
    regular_distances = np.arange(0, total_len, spacing_m)
    mop_distances = [x[0] for x in mop_intersections]

    # Combine and deduplicate (remove regular points too close to MOP intersections)
    snap_threshold = spacing_m * 0.3  # If regular point within 30% of spacing from MOP, remove it
    all_distances = []

    for dist in regular_distances:
        # Check if this regular distance is too close to any MOP intersection
        too_close = any(abs(dist - mop_dist) < snap_threshold for mop_dist in mop_distances)
        if not too_close:
            all_distances.append(dist)

    # Add MOP distances
    all_distances.extend(mop_distances)
    all_distances.sort()

    # Convert to numpy array
    distances = np.array(all_distances)
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
        
# --- LABEL TRANSECTS ---
    # Create a mapping of distance to MOP name
    mop_dist_to_name = {dist: name for dist, name, _ in mop_intersections}

    labels = []
    for i, dist in enumerate(distances[:len(transect_lines)]):
        # Check if this distance corresponds to a MOP intersection
        is_mop = False
        mop_name = None

        for mop_dist, name, _ in mop_intersections:
            if abs(dist - mop_dist) < 0.01:  # Within 1cm tolerance
                is_mop = True
                mop_name = name
                break

        if is_mop:
            # This is a MOP line transect - use the MOP name directly
            labels.append(mop_name)
        else:
            # This is a regular transect - find nearest MOP lines for sub-numbering
            # Find the MOP line immediately before this transect
            mop_before = None
            mop_before_dist = None
            for mop_dist, name, _ in mop_intersections:
                if mop_dist < dist:
                    mop_before = name
                    mop_before_dist = mop_dist
                else:
                    break

            # Calculate sub-number based on transects since last MOP
            if mop_before is not None:
                # Count how many non-MOP transects between this and the last MOP
                sub_num = 0
                for j in range(len(distances[:i])):
                    check_dist = distances[j]
                    if check_dist > mop_before_dist and check_dist < dist:
                        # Check if this is NOT a MOP transect
                        is_check_mop = any(abs(check_dist - md) < 0.01 for md, _, _ in mop_intersections)
                        if not is_check_mop:
                            sub_num += 1

                sub_num += 1  # Add 1 for current transect
                labels.append(f"{mop_before}_{sub_num:03d}")
            else:
                # Before first MOP line
                labels.append(f"start_{i+1:03d}")

    # 1. Create GDF for Transect Lines (The "Crossbars")
    transects_utm = gpd.GeoDataFrame(geometry=transect_lines, crs=utm_crs)
    transects_utm['transect_id'] = range(len(transects_utm))
    transects_utm['dist_along'] = distances[:len(transects_utm)]
    transects_utm['label'] = labels

    # 2. Create GDF for Baseline Points (The "Centers")
    # points_utm was already calculated earlier in the function
    points_gdf = gpd.GeoDataFrame(geometry=points_utm, crs=utm_crs)
    points_gdf['point_id'] = range(len(points_gdf))
    points_gdf['dist_along'] = distances[:len(points_gdf)]

    # Add labels to points as well (same as transects)
    if len(labels) == len(points_gdf):
        points_gdf['label'] = labels

    # Return BOTH GeoDataFrames
    return transects_utm, points_gdf
