"""
Coordinate translation utilities for screenshot markings.

Handles conversion between:
- Geographical coordinates (lat/lng)
- Canvas coordinates (integer x, y)
- Screenshot pixel coordinates

MANUAL-INTERVENTION [MARK-SCREENSHOT]: Install Pillow: pip install pillow>=10.0.0
"""

import math
from typing import Tuple, Dict, Any, Optional


class CoordinateTranslator:
    """
    Translates between coordinate systems for screenshot marking.

    LIMITATION [MARK-SCREENSHOT]: Simplified implementation assumes:
    - Web Mercator projection (standard for web maps like Mapbox)
    - Map is centered in screenshot without rotation
    - Canvas viewport transformations are linear (zoom/pan only)
    - No complex map distortions or custom projections

    LIMITATION [MARK-SCREENSHOT]: Does not handle:
    - Map rotation
    - Non-Web Mercator projections
    - Non-linear canvas transformations
    - UI overlays that obscure the map
    """

    # Earth's radius in meters (Web Mercator)
    EARTH_RADIUS = 6378137

    def __init__(self, viewport_info: Dict[str, Any], canvas_state: Dict[str, Any]):
        """
        Initialize coordinate translator.

        Args:
            viewport_info: Map viewport information from screenshot
            canvas_state: Canvas state with viewport zoom/pan

        LIMITATION [MARK-SCREENSHOT]: Assumes viewport_info and canvas_state
        have the expected structure. No validation performed for performance.
        """
        self.viewport_info = viewport_info
        self.canvas_state = canvas_state

        # Extract key values
        self.map_center = viewport_info["mapCenter"]  # [lat, lng]
        self.map_zoom = viewport_info["mapZoom"]
        self.map_bounds = viewport_info.get("mapBounds")

        self.canvas_viewport = canvas_state["viewport"]
        self.canvas_zoom = self.canvas_viewport["zoom"]
        self.canvas_pan = self.canvas_viewport["pan"]

        # Screenshot dimensions
        self.screen_width = viewport_info["width"]
        self.screen_height = viewport_info["height"]

        # Precalculate pixels per meter for this zoom level
        # LIMITATION [MARK-SCREENSHOT]: This calculation assumes 256x256 tiles at zoom 0
        # which is standard but may vary for some map providers
        self.pixels_per_meter = (256 * math.pow(2, self.map_zoom)) / (2 * math.pi * self.EARTH_RADIUS)

    def latlng_to_web_mercator(self, lat: float, lng: float) -> Tuple[float, float]:
        """
        Convert lat/lng to Web Mercator coordinates (meters from equator/prime meridian).

        LIMITATION [MARK-SCREENSHOT]: Web Mercator is undefined at poles (±85.05° latitude).
        Coordinates near poles will have extreme distortion.

        Args:
            lat: Latitude in degrees (-90 to 90)
            lng: Longitude in degrees (-180 to 180)

        Returns:
            (x, y): Web Mercator coordinates in meters
        """
        # Clamp latitude to valid Web Mercator range
        lat = max(-85.05112878, min(85.05112878, lat))

        # Convert to radians
        lat_rad = math.radians(lat)
        lng_rad = math.radians(lng)

        # Web Mercator formulas
        x = self.EARTH_RADIUS * lng_rad
        y = self.EARTH_RADIUS * math.log(math.tan(math.pi / 4 + lat_rad / 2))

        return (x, y)

    def web_mercator_to_latlng(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert Web Mercator coordinates back to lat/lng.

        Args:
            x: Web Mercator x in meters
            y: Web Mercator y in meters

        Returns:
            (lat, lng): Geographical coordinates in degrees
        """
        lng = math.degrees(x / self.EARTH_RADIUS)
        lat = math.degrees(2 * math.atan(math.exp(y / self.EARTH_RADIUS)) - math.pi / 2)

        return (lat, lng)

    def latlng_to_screenshot_pixel(self, lat: float, lng: float) -> Tuple[int, int]:
        """
        Convert lat/lng to screenshot pixel coordinates.

        LIMITATION [MARK-SCREENSHOT]: Assumes:
        - Map center aligns with screenshot center
        - No map rotation
        - Uniform scaling across the image
        - Map fills entire screenshot (no UI overlays accounted for)

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            (screen_x, screen_y): Screenshot pixel coordinates
        """
        map_center_lat, map_center_lng = self.map_center

        # Convert both points to Web Mercator
        center_x, center_y = self.latlng_to_web_mercator(map_center_lat, map_center_lng)
        point_x, point_y = self.latlng_to_web_mercator(lat, lng)

        # Calculate offset from center in meters
        offset_x = point_x - center_x
        offset_y = point_y - center_y

        # Convert meter offset to pixel offset
        pixel_offset_x = offset_x * self.pixels_per_meter
        # Y is inverted in screen coordinates (down is positive)
        pixel_offset_y = -offset_y * self.pixels_per_meter

        # Add to screen center
        screen_x = int((self.screen_width / 2) + pixel_offset_x)
        screen_y = int((self.screen_height / 2) + pixel_offset_y)

        return (screen_x, screen_y)

    def screenshot_pixel_to_latlng(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """
        Convert screenshot pixel to lat/lng coordinates.

        Args:
            screen_x: Screenshot pixel x
            screen_y: Screenshot pixel y

        Returns:
            (lat, lng): Geographical coordinates
        """
        map_center_lat, map_center_lng = self.map_center

        # Get map center in Web Mercator
        center_x, center_y = self.latlng_to_web_mercator(map_center_lat, map_center_lng)

        # Calculate pixel offset from center
        pixel_offset_x = screen_x - (self.screen_width / 2)
        pixel_offset_y = screen_y - (self.screen_height / 2)

        # Convert to meter offset (invert Y)
        meter_offset_x = pixel_offset_x / self.pixels_per_meter
        meter_offset_y = -pixel_offset_y / self.pixels_per_meter

        # Add to center coordinates
        point_x = center_x + meter_offset_x
        point_y = center_y + meter_offset_y

        # Convert back to lat/lng
        return self.web_mercator_to_latlng(point_x, point_y)

    def screenshot_pixel_to_canvas(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screenshot pixel coordinates to canvas coordinates.

        LIMITATION [MARK-SCREENSHOT]: Assumes simple linear transformation.
        Does not account for:
        - Canvas transformations beyond zoom/pan
        - Aspect ratio differences
        - Non-uniform scaling

        Args:
            screen_x: Screenshot pixel x
            screen_y: Screenshot pixel y

        Returns:
            (canvas_x, canvas_y): Canvas integer coordinates
        """
        # LIMITATION [MARK-SCREENSHOT]: This is a simplified calculation
        # Real-world canvas transformations may be more complex
        # For now, we assume screenshot space ≈ canvas space adjusted by viewport

        # Account for canvas zoom and pan
        # Reverse the viewport transformation
        canvas_x = int((screen_x / self.canvas_zoom) - self.canvas_pan["x"])
        canvas_y = int((screen_y / self.canvas_zoom) - self.canvas_pan["y"])

        return (canvas_x, canvas_y)

    def canvas_to_screenshot_pixel(self, canvas_x: int, canvas_y: int) -> Tuple[int, int]:
        """
        Convert canvas coordinates to screenshot pixel coordinates.

        Args:
            canvas_x: Canvas x coordinate
            canvas_y: Canvas y coordinate

        Returns:
            (screen_x, screen_y): Screenshot pixel coordinates
        """
        # Apply canvas viewport transformation
        screen_x = int((canvas_x + self.canvas_pan["x"]) * self.canvas_zoom)
        screen_y = int((canvas_y + self.canvas_pan["y"]) * self.canvas_zoom)

        return (screen_x, screen_y)

    def latlng_to_canvas(self, lat: float, lng: float) -> Tuple[int, int]:
        """
        Convert lat/lng directly to canvas coordinates.

        LIMITATION [MARK-SCREENSHOT]: Combines two transformations, accumulating
        potential errors from both latlng→screen and screen→canvas conversions.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            (canvas_x, canvas_y): Canvas integer coordinates
        """
        screen_x, screen_y = self.latlng_to_screenshot_pixel(lat, lng)
        return self.screenshot_pixel_to_canvas(screen_x, screen_y)

    def canvas_to_latlng(self, canvas_x: int, canvas_y: int) -> Tuple[float, float]:
        """
        Convert canvas coordinates to lat/lng.

        Args:
            canvas_x: Canvas x coordinate
            canvas_y: Canvas y coordinate

        Returns:
            (lat, lng): Geographical coordinates
        """
        screen_x, screen_y = self.canvas_to_screenshot_pixel(canvas_x, canvas_y)
        return self.screenshot_pixel_to_latlng(screen_x, screen_y)

    def get_visible_canvas_bounds(self) -> Tuple[int, int, int, int]:
        """
        Calculate which canvas coordinates are visible in the screenshot.

        LIMITATION [MARK-SCREENSHOT]: Assumes entire screenshot shows canvas.
        Does not account for UI elements that may obscure parts of the canvas.

        Returns:
            (min_x, min_y, max_x, max_y): Canvas coordinate bounds visible in screenshot
        """
        # Top-left corner of screenshot
        min_x, min_y = self.screenshot_pixel_to_canvas(0, 0)

        # Bottom-right corner of screenshot
        max_x, max_y = self.screenshot_pixel_to_canvas(self.screen_width, self.screen_height)

        return (min_x, min_y, max_x, max_y)

    def get_map_bounds_in_screen_coords(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the screenshot pixel coordinates of the map bounds rectangle.

        LIMITATION [MARK-SCREENSHOT]: Returns None if map bounds not provided
        in viewport info.

        Returns:
            (x_min, y_min, x_max, y_max): Screenshot pixel coordinates of bounds,
            or None if bounds not available
        """
        if not self.map_bounds:
            return None

        # Get corners of bounds
        north = self.map_bounds.get("north", 0)
        south = self.map_bounds.get("south", 0)
        east = self.map_bounds.get("east", 0)
        west = self.map_bounds.get("west", 0)

        # Convert corners to screen coordinates
        nw_x, nw_y = self.latlng_to_screenshot_pixel(north, west)  # Top-left
        se_x, se_y = self.latlng_to_screenshot_pixel(south, east)  # Bottom-right

        # Return as (x_min, y_min, x_max, y_max)
        return (nw_x, nw_y, se_x, se_y)

    def get_map_center_in_screen_coords(self) -> Tuple[int, int]:
        """
        Get the screenshot pixel coordinates of the map center.

        Returns:
            (screen_x, screen_y): Screenshot coordinates of map center
        """
        lat, lng = self.map_center
        return self.latlng_to_screenshot_pixel(lat, lng)
