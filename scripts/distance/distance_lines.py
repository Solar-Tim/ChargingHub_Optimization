import json
from typing import Any, Dict, List, Optional, Tuple
from math import radians, sin, cos, atan2, sqrt
from shapely.geometry import Point, LineString
import folium
from folium.features import DivIcon
from datetime import datetime
import os

# Earth's radius in kilometers
R = 6371.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth in meters."""
    lat1, lat2, lon1, lon2 = map(radians, [lat1, lat2, lon1, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # Convert km to meters

def load_geojson(filename: str) -> Dict:
    """Load a GeoJSON file and return its contents as a dictionary."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"GeoJSON file not found: {filename}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file: {filename}") from e

def find_nearest_point_on_line(ref_point: Point, line_coords: List[List[float]]) -> Tuple[float, Tuple[float, float]]:
    """Find the nearest point on a line segment to the reference point."""
    try:
        line = LineString(line_coords)
        nearest_point = line.interpolate(line.project(Point(ref_point.x, ref_point.y)))
        distance = haversine_distance(
            ref_point.y, ref_point.x,
            nearest_point.y, nearest_point.x
        )
        return distance, (nearest_point.x, nearest_point.y)
    except Exception as e:
        raise Exception(f"Error in finding nearest point: {str(e)}")

def find_nearest_power_line(ref_point: Point, data: Dict[str, Any]) -> Optional[Tuple[float, Dict[str, Any], Tuple[float, float]]]:
    """Find the nearest power line from the given dataset to the reference point."""
    min_distance = float('inf')
    nearest_line = None
    nearest_point = None

    for feature in data.get('features', []):
        geometry = feature.get('geometry', {})
        geometry_type = geometry.get('type')
        
        if geometry_type == 'LineString':
            coords_list = [geometry.get('coordinates', [])]
        elif geometry_type == 'MultiLineString':
            coords_list = geometry.get('coordinates', [])
        else:
            continue

        for coords in coords_list:
            if not coords:
                continue

            try:
                distance, point = find_nearest_point_on_line(ref_point, coords)
                if distance < min_distance:
                    min_distance = distance
                    nearest_line = feature
                    nearest_point = point
            except Exception:
                continue

    if nearest_line is None or nearest_point is None:
        return None

    return (min_distance, nearest_line, nearest_point)

def generate_line_popup_html(line: Dict, distance: float, nearest_point: Tuple[float, float]) -> str:
    """Generate HTML popup content for a power line."""
    props = line.get('properties', {})
    return f"""
        <b>Power Line</b><br>
        Distance: {distance:.0f}m<br>
        Nearest Point:<br>
        Latitude: {nearest_point[1]:.6f}<br>
        Longitude: {nearest_point[0]:.6f}<br>
        Voltage: {props.get('voltage', 'N/A')}V<br>
        Operator: {props.get('operator', 'N/A')}<br>
        <a href="https://www.openstreetmap.org/?mlat={nearest_point[1]}&mlon={nearest_point[0]}" target="_blank">View on OpenStreetMap</a>
    """

def create_power_line_map(
    ref_point: Point,
    line_result: Optional[Tuple[float, Dict, Tuple[float, float]]],
    power_line_data: Dict,
    max_display_distance: float = 10000  # 10km radius
) -> folium.Map:
    """Create a folium map showing the reference point and nearby power lines."""
    map_obj = folium.Map(location=[ref_point.y, ref_point.x], zoom_start=13)

    # Add reference point
    folium.Marker(
        location=[ref_point.y, ref_point.x],
        popup="Reference Point",
        icon=folium.Icon(color='red')
    ).add_to(map_obj)

    # Draw only nearby power lines
    for feature in power_line_data.get('features', []):
        geometry = feature.get('geometry', {})
        geometry_type = geometry.get('type')
        
        # Handle different geometry types
        if geometry_type == 'LineString':
            coords_list = [geometry.get('coordinates', [])]
        elif geometry_type == 'MultiLineString':
            coords_list = geometry.get('coordinates', [])
        else:
            continue
            
        for coords in coords_list:
            if not coords or len(coords) < 2:  # Skip invalid coordinates
                continue
                
            # Calculate rough distance to line start point
            try:
                dist_to_line = find_nearest_point_on_line(ref_point, coords)[0]
                
                # Skip lines that are too far away
                if dist_to_line > max_display_distance:
                    continue
                    
                # Draw line
                line_coords = [[lat, lon] for lon, lat in coords]
                folium.PolyLine(
                    locations=line_coords,
                    weight=2,
                    color='gray',
                    opacity=0.5
                ).add_to(map_obj)
                    
            except Exception as e:
                continue

    # If we found a nearest point, add it and connection line
    if line_result:
        distance, line, nearest_point = line_result
        
        try:
            # Add marker for nearest point
            popup_html = generate_line_popup_html(line, distance, nearest_point)
            folium.Marker(
                location=[nearest_point[1], nearest_point[0]],  # [lat, lon]
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(map_obj)

            # Add connection line
            connection_coords = [
                [ref_point.y, ref_point.x],      # Starting point [lat, lon]
                [nearest_point[1], nearest_point[0]]  # Ending point [lat, lon]
            ]
            folium.PolyLine(
                locations=connection_coords,
                weight=2,
                color='blue',
                opacity=0.8,
                dash_array='10'
            ).add_to(map_obj)

            # Add distance label at midpoint
            mid_point = [
                (ref_point.y + nearest_point[1]) / 2,  # mid latitude
                (ref_point.x + nearest_point[0]) / 2   # mid longitude
            ]
            folium.Marker(
                location=mid_point,
                icon=DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(75, 18),
                    html=f'<div style="font-size: 14px; color: blue;">{distance:.0f}m</div>'
                )
            ).add_to(map_obj)
            
        except Exception as e:
            print(f"Error adding markers and lines: {str(e)}")

    return map_obj

def calc_power_lines(ref_point: Point, map: bool = False) -> Optional[Tuple[float, Dict[str, Any], Tuple[float, float]]]:
    """
    Calculate the minimum distance to power lines and optionally create a map.
    
    Returns:
        Optional tuple containing (distance, line_data, nearest_point) or None if no lines found
    """
    # Update paths to match project structure
    voltage_files = [
        "data/osm/osm_sub_transmission.geojson",  # Use transmission data for power lines
    ]
    
    overall_min_distance = float('inf')
    overall_nearest_line = None
    overall_nearest_point = None
    combined_power_line_data = {'type': 'FeatureCollection', 'features': []}

    for filename in voltage_files:
        try:
            power_line_data = load_geojson(filename)
            if not power_line_data or 'features' not in power_line_data:
                continue
            
            combined_power_line_data['features'].extend(power_line_data.get('features', []))
            result = find_nearest_power_line(ref_point, power_line_data)
            
            if result:
                distance, line, point = result
                if distance < overall_min_distance:
                    overall_min_distance = distance
                    overall_nearest_line = line
                    overall_nearest_point = point
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
            continue

    if overall_nearest_line is None:
        return None

    result = (overall_min_distance, overall_nearest_line, overall_nearest_point)

    if map:
        try:
            result_map = create_power_line_map(
                ref_point, 
                result, # type: ignore
                combined_power_line_data,
                max_display_distance=10000
            )
            # Create results directory if it doesn't exist
            os.makedirs("results/maps", exist_ok=True)
            map_name = f"results/maps/{datetime.now().strftime('%m%d_%H%M')}_power_line_map.html"
            result_map.save(map_name)
            print(f"Map saved as: {map_name}")
        except Exception as e:
            print(f"Error creating map: {str(e)}")

    return result # type: ignore

#if __name__ == "__main__":
    # Reference point: Example location (longitude, latitude)
    ref_point = Point(6.214618953523452, 50.816300910540406)
    print(f"Processing reference point: Lon {ref_point.x}, Lat {ref_point.y}")
    
    result = calc_power_lines(ref_point, map=True)
    
    if result:
        distance, line, nearest_point = result
        print(f"Nearest power line: {distance:.0f} meters away")
        if nearest_point is not None:
            print(f"Nearest point: Lat {nearest_point[1]:.6f}, Lon {nearest_point[0]:.6f}")
            print(f"Line properties: {line.get('properties', {})}")
    else:
        print("No power lines found in range.")

