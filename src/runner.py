import googlemaps
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import json
import os
import json
import base64
import json
import ast

def convert_staff_locations(input_file):
    """Convert data as stored in our current team manual page into a format
    that can be used by this software"""
    # Read the input file
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Remove the 'export default' part and semicolon at the end
    data_string = content.replace('export default', '').strip()[:-1]

    # Replace JavaScript-style property names with Python-style
    data_string = data_string.replace('name:', '"name":')
    data_string = data_string.replace('location:', '"location":')
    data_string = data_string.replace('github:', '"github":')

    # Use ast.literal_eval to safely evaluate the string as a Python expression
    data_list = ast.literal_eval(data_string)
    
    # Transform the data
    origins = []
    for item in data_list:
        origins.append({
            "name": item["name"],
            "lat": item["location"][0],
            "lon": item["location"][1]
        })
    
    output_data = {"origins": origins}
    
    return output_data

def interpolate_staff_locations(input_file):
    output_data = convert_staff_locations(input_file=input_file)
    with open("locations_config.json", 'r') as f:
        content = json.load(f)
        content.update(output_data)
    with open("locations_config.json", 'w') as f:
        json.dump(content, f, indent=2)


class RouteUpdater:
    def __init__(
        self, api_key: str, config_file: str, routes_file: str = "routes.json"
    ):
        self.gmaps = googlemaps.Client(key=api_key)
        self.config = self.load_config(config_file)
        self.routes_file = routes_file
        self.routes = self.load_routes()

    def load_routes(self):
        try:
            with open(self.routes_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_config(self, config_file: str) -> Dict:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file: {config_file}")

    def get_coordinates(self, locations: List[Dict]) -> List[Tuple[float, float]]:
        return [(round(loc["lat"], 4), round(loc["lon"], 4)) for loc in locations]

    def update_routes(self):
        origins = self.get_coordinates(self.config["origins"])
        destinations = self.get_coordinates(self.config["destinations"])

        for origin in origins:
            for destination in destinations:
                origin_str = f"{origin[0]:.2f},{origin[1]:.2f}"
                dest_str = f"{destination[0]:.2f},{destination[1]:.2f}"
                route_key = f"{origin_str}->{dest_str}"


                if route_key not in self.routes:
                    if origin == dest_str:
                        self.routes[route_key] = 0
                    else:
                        try:
                            next_thursday = datetime.now() + timedelta(
                                days=(3 - datetime.now().weekday() + 7) % 7
                            )
                            next_thursday = next_thursday.replace(
                                hour=14, minute=0, second=0, microsecond=0
                            )
                            matrix = self.gmaps.distance_matrix(
                                [origin],
                                destination,
                                mode="transit",
                                transit_mode="bus|subway|train",
                                arrival_time=next_thursday,
                            )
                            element = matrix["rows"][0]["elements"][0]
                            if "duration" in element:
                                duration = element["duration"]["value"]
                                print(
                                    f"Transit route found from {origin} to {destination}: {duration}"
                                )
                            else:
                                print(
                                    f"No transit route found from {origin} to {destination}"
                                )
                                duration = float("inf")  # Use infinity for no route
                            self.routes[route_key] = duration
                        except Exception as e:
                            print(
                                f"Error calculating travel time from {origin} to {destination}: {e}"
                            )
                            self.routes[route_key] = float("inf")  # Use infinity for errors

        self.save_routes()

    def save_routes(self):
        with open(self.routes_file, "w") as f:
            json.dump(self.routes, f)

    def close(self):
        self.save_routes()


class BestDestinationFinder:
    def __init__(
        self,
        api_key: str,
        config_file: str,
        routes_file: str = "routes.json",
        db_file: str = None,
    ):
        self.gmaps = googlemaps.Client(key=api_key)
        self.config = self.load_config(config_file)
        self.routes_file = routes_file
        self.routes = self.load_routes()
        self.db_file = db_file

    def load_routes(self):
        try:
            with open(self.routes_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_file}")

    def get_coordinates(self, locations: List[Dict]) -> List[Tuple[float, float]]:
        return [(round(loc["lat"], 4), round(loc["lon"], 4)) for loc in locations]

    def calculate_travel_times(
        self, origins: List[Tuple[float, float]], destination: Tuple[float, float]
    ) -> List[int]:
        travel_times = []
        for origin in origins:
            origin_str = f"{origin[0]:.2f},{origin[1]:.2f}"
            dest_str = f"{destination[0]:.2f},{destination[1]:.2f}"
            route_key = f"{origin_str}->{dest_str}"
            if route_key in self.routes:
                travel_times.append(self.routes[route_key])
            else:
                travel_times.append(
                    1800
                )  # Use 30 minutes (1800 seconds) as default for missing routes
        return travel_times

    def calculate_convenience_score(self, travel_times: List[int]) -> float:
        """
        Calculate a convenience score based on travel times.

        This score is a weighted combination of the average travel time (70% weight)
        and the maximum travel time (30% weight). This approach balances overall
        convenience for the group with fairness to the person with the longest journey.

        A lower score indicates a more convenient location.

        :param travel_times: List of travel times in seconds
        :return: Convenience score (lower is better)
        """
        avg_time = sum(travel_times) / len(travel_times)
        max_time = max(travel_times)
        return avg_time * 0.7 + max_time * 0.3

    def find_best_destinations(self, top_n: int = 5) -> List[Tuple[Dict, float]]:
        origins = self.get_coordinates(self.config["origins"])
        destinations = self.get_coordinates(self.config["destinations"])

        all_destinations = []

        for i, dest in enumerate(destinations):
            travel_times = self.calculate_travel_times(origins, dest)
            score = self.calculate_convenience_score(travel_times)
            all_destinations.append((self.config["destinations"][i], score))

        # Sort destinations by score (lower is better) and return top N
        return sorted(all_destinations, key=lambda x: x[1])[:top_n]

    def get_address(self, lat_lng: Tuple[float, float]) -> str:
        rounded_lat_lng = (round(lat_lng[0], 2), round(lat_lng[1], 2))
        result = self.gmaps.reverse_geocode(rounded_lat_lng)
        if result:
            return result[0]["formatted_address"]
        return "Address not found"

    def plot_travel_times_histogram(self, location: Dict):
        """
        Plot travel times for a given location as a horizontal histogram using Unicode characters.

        :param location: Dictionary containing location information (lat, lon, name)
        """
        origins = self.get_coordinates(self.config["origins"])
        destination = (location["lat"], location["lon"])
        travel_times = self.calculate_travel_times(origins, destination)

        # Convert travel times from seconds to minutes
        travel_times_minutes = [t // 60 for t in travel_times if t != float("inf")]

        if not travel_times_minutes:
            print(f"No valid travel times for {location['name']}")
            return

        # Calculate bucket size to aim for approximately 10 buckets
        bucket_size = max(
            1, (max(travel_times_minutes) - min(travel_times_minutes)) // 10
        )

        # Create buckets
        buckets = {}
        for time in travel_times_minutes:
            bucket = (time // bucket_size) * bucket_size
            buckets[bucket] = buckets.get(bucket, 0) + 1

        # Find the maximum count for scaling
        max_count = max(buckets.values())

        # Define Unicode characters for the bars
        bar_char = "█"

        print(f"Travel Times to {location['name']} (minutes):")

        # Print the histogram
        for bucket in sorted(buckets.keys()):
            count = buckets[bucket]
            bar_length = int(
                (count / max_count) * 20
            )  # Scale to max width of 20 characters
            print(
                f"{bucket:3d}-{bucket+bucket_size-1:<3d} | {bar_char * bar_length} {count}"
            )

        print(f"Each row represents a {bucket_size}-minute range")
        print(f"Total trips: {len(travel_times_minutes)}")
        if len(travel_times_minutes) < len(travel_times):
            print(
                f"Note: {len(travel_times) - len(travel_times_minutes)} routes were not found"
            )

    def close(self):
        pass  # No need to save routes in this class

def build_embedded_html(config_file: str, routes_file: str, output_file: str = "index_embedded.html"):
    """
    Build a self-contained HTML file with embedded JSON data.
    
    :param config_file: Path to the locations config JSON file
    :param routes_file: Path to the routes JSON file
    :param output_file: Path to the output HTML file
    """
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    with open(routes_file, 'r') as f:
        routes_data = json.load(f)
    
    with open('index.html', 'r') as f:
        html_template = f.read()
    
    # Encode JSON data as base64
    config_base64 = base64.b64encode(json.dumps(config_data).encode()).decode()
    routes_base64 = base64.b64encode(json.dumps(routes_data).encode()).decode()
    
    # Replace the loadData function in the HTML template
    embedded_html = html_template.replace(
        'async function loadData() {',
        f'''async function loadData() {{
            const configBase64 = "{config_base64}";
            const routesBase64 = "{routes_base64}";
            config = JSON.parse(atob(configBase64));
            routes = JSON.parse(atob(routesBase64));
            populateOriginSelect();
        '''
    )
    
    # Remove fetch calls
    embedded_html = embedded_html.replace(
        'const configResponse = await fetch(\'locations_config.json\');',
        '// Fetch calls removed in embedded version'
    )
    embedded_html = embedded_html.replace(
        'const routesResponse = await fetch(\'routes.json\');',
        '// Fetch calls removed in embedded version'
    )
    
    with open(output_file, 'w') as f:
        f.write(embedded_html)
    return output_file    
