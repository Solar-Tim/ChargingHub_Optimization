import json
from typing import Any, Dict, List, Optional, Tuple
from math import radians, sin, cos, atan2, sqrt
from shapely.geometry import Point
import folium
from folium.features import DivIcon
from datetime import datetime
from scripts.charginghub_optimization.distance.distance_lines import calc_power_lines

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth in meters."""
    R = 6371000  # Earth's radius in meters
    lat1, lat2, lon1, lon2 = map(radians, [lat1, lat2, lon1, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def load_geojson(filename: str) -> Dict:
    """Load a GeoJSON file and return its contents as a dictionary.
    Raises FileNotFoundError if the file does not exist.
    Raises json.JSONDecodeError if the file is not valid JSON.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"GeoJSON file not found: {filename}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file: {filename}") from e

def find_nearest(ref_point: Point, data: Dict[str, Any]) -> Optional[Tuple[float, Dict[str, Any], Tuple[float, float]]]:
    """Find the nearest substation from the given dataset to the reference point.
    Returns a tuple of (distance_in_meters, feature_properties, (longitude, latitude)) or None.
    """
    min_distance = float('inf')
    nearest_station: Optional[Dict[str, Any]] = None
    nearest_coords: Optional[Tuple[float, float]] = None

    for feature in data.get('features', []):
        geometry = feature.get('geometry', {})
        if geometry.get('type') != 'Point':
            continue  # Skip non-Point features

        coords = geometry.get('coordinates', None)
        # Ensure coords is a list/tuple of length >= 2
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue

        # coords is [longitude, latitude]
        lon, lat = coords[0], coords[1]

        # Make sure we can convert them to float (in case they're not strictly float)
        try:
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            continue  # If parsing fails, skip this feature

        distance = haversine_distance(
            lat1=ref_point.y, lon1=ref_point.x,
            lat2=lat,        lon2=lon
        )

        if distance < min_distance:
            min_distance = distance
            nearest_station = feature
            nearest_coords = (lon, lat)

    if nearest_station is None or nearest_coords is None:
        return None

    return (min_distance, nearest_station, nearest_coords)

def find_closest_substations(
    ref_point: Point,
    distribution_data: Dict,
    transmission_data: Dict
) -> Tuple[Optional[Tuple[float, Dict, Tuple[float, float]]], Optional[Tuple[float, Dict, Tuple[float, float]]]]:
    """Find the closest distribution and transmission substations to a reference point."""
    return (
        find_nearest(ref_point, distribution_data),
        find_nearest(ref_point, transmission_data)
    )

def add_marker(
    map_obj: folium.Map,
    coords: Tuple[float, float],
    color: str,
    popup_html: str
) -> None:
    """Add a marker to the folium map.
    coords: (longitude, latitude) tuple
    """
    folium.Marker(
        location=[coords[1], coords[0]],  # Folium uses [lat, lon]
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=color)
    ).add_to(map_obj)

def generate_popup_html(station: Dict, distance: float) -> str:
    """Generate HTML popup content for a substation."""
    props = station.get('properties', {})
    coords = station['geometry']['coordinates']  # [lon, lat]
    return f"""
        <b>{props.get('substation', 'Unknown')} Substation</b><br>
        Distance: {distance:.0f}m<br>
        Latitude: {coords[1]:.6f}<br>
        Longitude: {coords[0]:.6f}<br>
        Name: {props.get('name', 'N/A')}<br>
        Operator: {props.get('operator', 'N/A')}<br>
        Voltage: {props.get('voltage', 'N/A')}<br>
        Power: {props.get('power', 'N/A')}<br>
        <a href="https://www.openstreetmap.org/?mlat={coords[1]}&mlon={coords[0]}" target="_blank">View on OpenStreetMap</a>
    """

def create_map(
    ref_point: Point,
    distribution_result: Optional[Tuple[float, Dict, Tuple[float, float]]],
    transmission_result: Optional[Tuple[float, Dict, Tuple[float, float]]]
) -> folium.Map:
    """Create a folium map showing the reference point and nearest substations."""
    # Initialize map centered on reference point (lat, lon)
    map_obj = folium.Map(location=[ref_point.y, ref_point.x], zoom_start=11)

    # Add reference point marker
    ref_popup = f"""
        <b>Reference Point</b><br>
        Latitude: {ref_point.y:.6f}<br>
        Longitude: {ref_point.x:.6f}<br>
        <a href="https://www.openstreetmap.org/?mlat={ref_point.y}&mlon={ref_point.x}" target="_blank">View on OpenStreetMap</a>
    """
    add_marker(map_obj, (ref_point.x, ref_point.y), 'red', ref_popup)

    # Add substations and connections
    for result, color in [(distribution_result, 'green'), (transmission_result, 'blue')]:
        if not result:
            continue
        distance, station, coords = result
        popup_html = generate_popup_html(station, distance)
        add_marker(map_obj, coords, color, popup_html)

        # Add connection line
        folium.PolyLine(
            locations=[
                [ref_point.y, ref_point.x],  # Reference point (lat, lon)
                [coords[1], coords[0]]       # Substation (lat, lon)
            ],
            weight=2,
            color=color,
            opacity=0.8
        ).add_to(map_obj)

        # Add distance label at midpoint
        mid_point = [
            (ref_point.y + coords[1]) / 2,
            (ref_point.x + coords[0]) / 2
        ]
        folium.Marker(
            mid_point,
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 18),
                html=f'<div style="font-size: 14px; color: {color};">{distance:.0f}m</div>',
            )
        ).add_to(map_obj)

    return map_obj

def calc_substations(ref_point: Point, map: bool = False):
    """
    Load distribution and transmission data,
    find the closest substations to the given reference point,
    and optionally create and save a map.

    :param ref_point: A shapely.geometry.Point specifying the location to check.
    :param create_map: Boolean indicating whether to generate a map HTML file.
    :return: (distribution_result, transmission_result) 
             The closest distribution and transmission substations.
    """
    # Load GeoJSON data
    distribution_data = load_geojson("01_Distance-Calc/osm_sub_distribution_V2.geojson")
    transmission_data = load_geojson("01_Distance-Calc/osm_sub_transmission.geojson")

    # Find closest substations
    distribution_result, transmission_result = find_closest_substations(
        ref_point, distribution_data, transmission_data
    )

    # Create and save map if requested
    if map:
        result_map = create_map(ref_point, distribution_result, transmission_result)
        map_name = f"10_Maps/{datetime.now().strftime('%m%d_%H%M')}_substation_map.html"
        result_map.save(map_name)
        print(f"Map saved as: {map_name}")

    return distribution_result, transmission_result

def create_combined_map(ref_point: Point, 
                       substation_results: tuple, 
                       powerline_distance: float,
                       powerline_point: tuple) -> folium.Map:
    """Create map showing reference point, substations and nearest powerline point."""
    dist_result, trans_result = substation_results
    
    # Create base map with substations
    map_obj = create_map(ref_point, dist_result, trans_result)
    
    # Add powerline nearest point and connection
    if powerline_point:
        # Add powerline marker
        power_popup = f"""
            <b>Nearest Point on Powerline</b><br>
            Distance: {powerline_distance:.0f}m<br>
            Latitude: {powerline_point[1]:.6f}<br>
            Longitude: {powerline_point[0]:.6f}
        """
        add_marker(map_obj, powerline_point, 'purple', power_popup)
        
        # Add connection line
        folium.PolyLine(
            locations=[
                [ref_point.y, ref_point.x],
                [powerline_point[1], powerline_point[0]]
            ],
            weight=2,
            color='purple',
            opacity=0.8
        ).add_to(map_obj)
        
        # Add distance label
        mid_point = [
            (ref_point.y + powerline_point[1]) / 2,
            (ref_point.x + powerline_point[0]) / 2
        ]
        folium.Marker(
            mid_point,
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 18),
                html=f'<div style="font-size: 14px; color: purple;">{powerline_distance:.0f}m</div>',
            )
        ).add_to(map_obj)
    
    return map_obj

def calculate_all_distances(ref_point: Point, create_map: bool) -> Dict[str, Any]:
    """Calculate distances to substations and power lines."""
    # Get substation results
    substation_results = calc_substations(ref_point, map=create_map)
    dist_result, trans_result = substation_results
    
    # Calculate powerline distance
    powerline_result = calc_power_lines(ref_point, create_map)
    powerline_distance = None
    nearest_point = None
    
    if powerline_result:
        powerline_distance, _, nearest_point = powerline_result
    
    # Create combined map if requested
    if create_map and powerline_result:
        map_obj = create_combined_map(
            ref_point, 
            substation_results, 
            powerline_distance or 0, 
            nearest_point # type: ignore
        )
        map_name = f"10_Maps/{datetime.now().strftime('%m%d_%H%M')}_combined_distance_map.html"
        map_obj.save(map_name)
        print(f"Map saved as: {map_name}")
    
    return {
        'distribution_distance': dist_result[0] if dist_result else None,
        'transmission_distance': trans_result[0] if trans_result else None,
        'powerline_distance': powerline_distance,
        'nearest_powerline_point': nearest_point
    }

# Example usage:
if __name__ == "__main__":
    # Reference point: Berlin, Germany (longitude, latitude)
    reference_point = Point(6.214699333123033, 50.81648528837548)
    if False: #only Substations calculation 
        # Call the function, specifying whether a map is needed
        dist_result, trans_result = calc_substations(berlin, map=True)
    if True: # all distances calculation
        # Example usage
        results = calculate_all_distances(reference_point, create_map=True)

        print(f"Distribution substation distance: {results['distribution_distance']:.0f}m")
        print(f"Transmission substation distance: {results['transmission_distance']:.0f}m")
        print(f"Powerline distance: {results['powerline_distance']:.0f}m")
