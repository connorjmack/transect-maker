# Spatial Transect Generator

A Streamlit-based geospatial tool designed to automatically generate perpendicular transects along a user-defined baseline.

This application was built to streamline workflows in coastal geomorphology, environmental sampling, and hazard monitoring. It solves common geometric issues (such as corner crossing) by employing vector smoothing and ensures metric accuracy by automatically projecting inputs to the appropriate local UTM zone.

## 🚀 Features

  * **Interactive Mapping:** Draw baselines directly on an interactive map featuring high-resolution Esri Satellite imagery or OpenStreetMap.
  * **Visual Feedback:** Instantly view generated transects (red) and baseline points (blue) directly on the map.
  * **Search & Geocoding:** built-in location search to quickly navigate to your area of interest.
  * **Automatic Projection:** Automatically detects the correct UTM zone for your area of interest and projects data to meters for accurate distance calculations.
  * **Smart Geometry:**
      * **Adjustable Vector Smoothing:** Applies a user-configurable rolling average to the baseline's tangent vectors to prevent transects from crossing or "snapping" at sharp corners.
      * **Metric Accuracy:** Generates transects at precise intervals (e.g., every 1.0m) with defined lengths.
  * **Flexible Export:** Download results in multiple formats:
      * **ESRI Shapefile** (.shp)
      * **GeoJSON** (.geojson)
      * **KML** (.kml) for Google Earth
      * **GeoPackage** (.gpkg)

## 🛠️ Installation & Usage

### Option 1: Docker (Recommended)
Run the application in a consistent environment without manual dependency management.

1.  **Build the image:**
    ```bash
    docker build -t transect-maker .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 8501:8501 transect-maker
    ```

3.  **Access:** Open `http://localhost:8501` in your browser.

### Option 2: Local Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/connorjmack/transect-maker.git
    cd transect-maker
    ```

2.  **Install dependencies:**
    (Recommended: use a virtual environment like conda or venv)
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

## 💻 How to Use

1.  **Locate Area:** Use the **Search button** (magnifying glass) or pan/zoom to find your site.
2.  **Draw Baseline:** Use the **Polyline tool** (top-left of the map) to draw your reference line (e.g., a cliff edge, shoreline, or road).
3.  **Configure Settings:**
    *   **Transect Length:** Total length of the perpendicular line.
    *   **Interval Spacing:** Distance between each transect.
    *   **Smoothing Window:** Adjust the slider to smooth out jagged corners.
4.  **Generate:** Click **Generate Transects**. The results will appear on the map.
5.  **Download:** Select your preferred **File Format** and click the download button.

## 🧪 Development

### Running Tests
This project includes a unit test suite to ensure geometric accuracy and logic stability.
```bash
python -m unittest discover tests
```

## 📐 Algorithm Details

To ensure scientific accuracy, the tool performs the following steps:

1.  **Input Parsing:** Takes the WGS84 (Lat/Lon) geometry from the web map interface.
2.  **Reprojection:** Estimates the local UTM CRS based on the geometry's centroid and projects the line into meters.
3.  **Validation:** Checks if the drawn line is valid and longer than the requested interval.
4.  **Interpolation:** Points are interpolated along the line at the user-defined interval.
5.  **Vector Smoothing:** To prevent "corner crossing," tangent vectors are smoothed using a rolling window average (configurable size).
6.  **Generation:** Perpendicular lines are constructed using the smoothed normal vectors.
7.  **Export:** The final GeoDataFrame is exported to the user's chosen format.

## 📦 Dependencies

  * `streamlit`: Web GUI framework.
  * `folium` / `streamlit-folium`: Interactive mapping.
  * `geopandas`: Spatial data handling.
  * `shapely`: Geometric operations.
  * `pyproj`: Coordinate reference system management.
  * `numpy`: Vector mathematics.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 👤 Author

**Connor J. Mack** GitHub: [@connorjmack](https://www.google.com/search?q=https://github.com/connorjmack)
