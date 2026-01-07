import unittest
import geopandas as gpd
from shapely.geometry import LineString, Point
import sys
import os
import numpy as np

# Add parent directory to path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import transect_utils as tu

class TestTransectUtils(unittest.TestCase):

    def test_process_user_drawing_valid(self):
        """Test parsing valid GeoJSON from Folium."""
        mock_draw = {
            'type': 'FeatureCollection',
            'features': [{
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[-117.0, 32.0], [-117.0, 32.001]]
                }
            }]
        }
        geom = tu.process_user_drawing(mock_draw)
        self.assertIsInstance(geom, LineString)
        self.assertEqual(len(geom.coords), 2)

    def test_process_user_drawing_invalid(self):
        """Test parsing invalid input returns None."""
        self.assertIsNone(tu.process_user_drawing(None))
        self.assertIsNone(tu.process_user_drawing({}))
        
        # Point instead of LineString
        mock_draw_point = {
            'type': 'FeatureCollection',
            'features': [{
                'geometry': {
                    'type': 'Point',
                    'coordinates': [-117.0, 32.0]
                }
            }]
        }
        self.assertIsNone(tu.process_user_drawing(mock_draw_point))

    def test_generate_transects_basic(self):
        """Test basic transect generation output types and counts."""
        # Create a simple line in WGS84
        # Roughly 111km per degree latitude. 0.001 deg is ~111m.
        line = LineString([[-117.25, 32.87], [-117.25, 32.871]]) # Vertical line
        
        spacing = 10.0
        length = 20.0
        
        # We expect around 11-12 transects for ~111m length with 10m spacing
        
        transects_gdf, points_gdf = tu.generate_transects(line, spacing_m=spacing, length_m=length)
        
        # Check Types
        self.assertIsInstance(transects_gdf, gpd.GeoDataFrame)
        self.assertIsInstance(points_gdf, gpd.GeoDataFrame)
        
        # Check Lengths (should match)
        self.assertEqual(len(transects_gdf), len(points_gdf))
        self.assertTrue(len(transects_gdf) > 5)
        
        # Check Columns
        self.assertIn('transect_id', transects_gdf.columns)
        self.assertIn('dist_along', points_gdf.columns)

    def test_generate_transects_projection(self):
        """Test that the output is projected (not WGS84)."""
        line = LineString([[-117.25, 32.87], [-117.25, 32.871]])
        transects_gdf, _ = tu.generate_transects(line)
        
        # WGS84 uses degrees, so bounds should be small numbers like -117, 32
        # Projected UTM uses meters, so bounds should be large numbers.
        
        # Check CRS
        self.assertFalse(transects_gdf.crs.is_geographic)
        
        # Check coordinate magnitude
        x_coord = transects_gdf.geometry.iloc[0].coords[0][0]
        self.assertTrue(abs(x_coord) > 180, "Coordinates should be projected meters, not degrees")

    def test_smoothing_window_handling(self):
        """Test that smoothing doesn't crash on short lines (fewer points than window)."""
        line = LineString([[-117.25, 32.87], [-117.25, 32.87005]]) # Very short ~5m
        
        # Spacing 1m -> ~5 points. Default window is 9.
        # This checks the "if len(tangents) > smoothing_window" logic.
        transects_gdf, _ = tu.generate_transects(line, spacing_m=1.0)
        
        self.assertGreater(len(transects_gdf), 0)

if __name__ == '__main__':
    unittest.main()
