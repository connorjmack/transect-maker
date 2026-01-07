# Spatial Transect Generator

## Project Overview

**Spatial Transect Generator** is a Python-based web application built with Streamlit. It allows users to interactively draw a baseline on a map (using satellite imagery) and automatically generate perpendicular transects at specified intervals.

The tool is designed for geospatial workflows in coastal geomorphology and environmental sampling, solving common geometric issues like "corner crossing" through vector smoothing.

### Key Features
*   **Interactive Mapping:** Built on `folium` and `streamlit-folium`.
*   **Automatic Projection:** Dynamically estimates the best local UTM zone using `geopandas` and `pyproj` to ensure metric accuracy.
*   **Vector Smoothing:** Implements a rolling window average on tangent vectors to prevent transect overlap at sharp vertices.
*   **GIS Export:** Outputs results as a zipped ESRI Shapefile bundle (lines and points).

## Tech Stack

*   **Language:** Python 3.10+
*   **Frontend:** Streamlit
*   **Mapping:** Folium, Streamlit-Folium
*   **Geospatial Processing:** Geopandas, Shapely, Pyproj
*   **Numerics:** Numpy

## Architecture

The project consists of two main Python files:

1.  **`app.py` (Frontend & Controller):**
    *   Initializes the Streamlit app and page layout.
    *   Renders the Folium map with OpenStreetMap and Esri Satellite tiles.
    *   Handles user interactions (drawing polylines, setting parameters).
    *   Manages the generation trigger and file download logic.

2.  **`transect_utils.py` (Core Logic):**
    *   **`process_user_drawing`:** Parses GeoJSON from the frontend into Shapely objects.
    *   **`generate_transects`:** The core algorithm:
        1.  Projects input WGS84 geometry to the estimated local UTM CRS.
        2.  Interpolates points along the line at `spacing_m`.
        3.  Calculates tangent vectors and applies a rolling window smoothing to them.
        4.  Constructs perpendicular lines (transects).
        5.  Returns two GeoDataFrames: one for transects and one for baseline points.

## Building and Running

### Prerequisites
*   Python 3.10 or higher
*   Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/connorjmack/transect-maker.git
    cd transect-maker
    ```

2.  **Set up the environment:**
    Using `pip`:
    ```bash
    pip install -r requirements.txt
    ```
    
    Or using `conda`:
    ```bash
    conda env create -f environment.yml
    conda activate transect-env
    ```

### Running the App

Execute the Streamlit application:
```bash
streamlit run app.py
```
The app will open in your default web browser (usually at `http://localhost:8501`).

## Docker Usage

To run the application in a consistent environment without manually installing dependencies:

1.  **Build the Docker image:**
    ```bash
    docker build -t transect-maker .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 8501:8501 transect-maker
    ```

3.  **Access the App:**
    Open your browser and navigate to `http://localhost:8501`.

## Usage Guide

1.  **Draw:** Use the Polyline tool on the map to trace a feature (e.g., coastline). Double-click to finish drawing.
2.  **Configure:** Adjust "Transect Length" and "Interval Spacing" in the sidebar.
3.  **Generate:** Click the "Generate Transects" button.
4.  **Download:** Download the generated ZIP file containing the Shapefiles.

## Development Conventions

*   **Code Style:** Follows standard Python PEP 8 conventions.
*   **Geospatial Data:** All internal calculations should be performed in a projected CRS (meters), not geographic coordinates (degrees), to ensure accuracy.
*   **File Structure:** Keep the root directory flat. Core logic should remain separated in `transect_utils.py` to keep the UI code in `app.py` clean.
