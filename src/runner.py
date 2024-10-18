import googlemaps
from datetime import datetime
from typing import List, Tuple, Dict
import json


class BestDestinationFinder:
    def __init__(self, api_key: str, config_file: str):
        self.gmaps = googlemaps.Client(key=api_key)
        self.config = self.load_config(config_file)

    def load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_file}")

    def get_coordinates(self, locations: List[Dict]) -> List[Tuple[float, float]]:
        return [(loc["lat"], loc["lon"]) for loc in locations]

    def calculate_travel_times(
        self, origins: List[Tuple[float, float]], destination: Tuple[float, float]
    ) -> List[int]:
        matrix = self.gmaps.distance_matrix(
            origins,
            destination,
            mode="transit",
            transit_mode="bus|subway|train",
            arrival_time=datetime.now(),
        )
        return [row["elements"][0]["duration"]["value"] for row in matrix["rows"]]

    def calculate_convenience_score(self, travel_times: List[int]) -> float:
        avg_time = sum(travel_times) / len(travel_times)
        max_time = max(travel_times)
        return avg_time * 0.7 + max_time * 0.3

    def find_best_destination(self) -> Tuple[Dict, float]:
        origins = self.get_coordinates(self.config["origins"])
        destinations = self.get_coordinates(self.config["destinations"])

        best_destination = None
        best_score = float("inf")

        for i, dest in enumerate(destinations):
            travel_times = self.calculate_travel_times(origins, dest)
            score = self.calculate_convenience_score(travel_times)
            if score < best_score:
                best_score = score
                best_destination = self.config["destinations"][i]

        return best_destination, best_score

    def get_address(self, lat_lng: Tuple[float, float]) -> str:
        result = self.gmaps.reverse_geocode(lat_lng)
        if result:
            return result[0]["formatted_address"]
        return "Address not found"


# Usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    finder = BestDestinationFinder(api_key, "locations_config.json")

    best_location, best_score = finder.find_best_destination()
    print(
        f"Best location: {best_location['name']} ({best_location['lat']}, {best_location['lon']})"
    )
    print(f"Convenience score: {best_score}")
    address = finder.get_address((best_location["lat"], best_location["lon"]))
    print(f"Address: {address}")
