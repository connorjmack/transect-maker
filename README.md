# Spatial Transect Generator

A Streamlit-based geospatial tool designed to automatically generate perpendicular transects along a user-defined baseline.

This application was built to streamline workflows in coastal geomorphology, environmental sampling, and hazard monitoring. It solves common geometric issues (such as corner crossing) by employing vector smoothing and ensures metric accuracy by automatically projecting inputs to the appropriate local UTM zone.

## 🚀 Features

  * **Interactive Mapping:** Draw baselines directly on an interactive map featuring high-resolution Esri Satellite imagery or OpenStreetMap.
  * **Automatic Projection:** Automatically detects the correct UTM zone for your area of interest and projects data to meters for accurate distance calculations.
  * **Smart Geometry:**
      * **Vector Smoothing:** Applies a rolling average to the baseline's tangent vectors to prevent transects from crossing or "snapping" at sharp corners.
      * **Metric Accuracy:** Generates transects at precise intervals (e.g., every 1.0m) with defined lengths.
  * **GIS Ready:** Exports results as a zipped **ESRI Shapefile** containing the projection file (`.prj`), making it immediately usable in ArcGIS Pro, QGIS, or Python workflows.

## 🛠️ Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/connorjmack/transect-maker.git
    cd transect-maker
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.

    ```bash
    pip install -r requirements.txt
    ```

## 💻 Usage

1.  **Run the application:**

    ```bash
    streamlit run app.py
    ```

2.  **Draw a Baseline:**

      * Use the **Polyline tool** (top-left of the map) to draw your reference line (e.g., a cliff edge, shoreline, or road).
      * *Tip:* You can use your mouse wheel to zoom in/out while drawing for higher precision.

3.  **Configure Settings:**

      * **Transect Length:** Total length of the perpendicular line (centered on the baseline).
      * **Interval Spacing:** Distance between each transect along the baseline (e.g., 1 meter).

4.  **Generate & Download:**

      * Click **Generate Transects**.
      * Download the resulting ZIP file.
      * Unzip and drag the `.shp` file into your preferred GIS software.

## 📐 Algorithm Details

To ensure scientific accuracy, the tool performs the following steps:

1.  **Input Parsing:** Takes the WGS84 (Lat/Lon) geometry from the web map interface.
2.  **Reprojection:** Estimates the local UTM CRS (Coordinate Reference System) based on the geometry's centroid and projects the line into meters.
3.  **Interpolation:** Points are interpolated along the line at the user-defined interval.
4.  **Vector Smoothing:** To prevent transect overlap at sharp angles ("corner crossing"), the tangent vectors are calculated using a forward-difference method and smoothed using a rolling window average.
5.  **Generation:** Perpendicular lines are constructed using the smoothed normal vectors.
6.  **Export:** The final GeoDataFrame is written to a shapefile, preserving the projected UTM coordinate system.

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