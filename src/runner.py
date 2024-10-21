import googlemaps
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import json
import json
import matplotlib.pyplot as plt
from collections import Counter


class BestDestinationFinder:
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
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_file}")

    def get_coordinates(self, locations: List[Dict]) -> List[Tuple[float, float]]:
        return [(round(loc["lat"], 2), round(loc["lon"], 2)) for loc in locations]

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
                        print(f"No transit route found from {origin} to {destination}")
                        duration = float("inf")  # Use infinity for no route
                    travel_times.append(duration)
                    self.routes[route_key] = duration
                    self.save_routes()
                except Exception as e:
                    print(
                        f"Error calculating travel time from {origin} to {destination}: {e}"
                    )
                    travel_times.append(float("inf"))  # Use infinity for errors
        return travel_times

    def save_routes(self):
        with open(self.routes_file, "w") as f:
            json.dump(self.routes, f)

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

    def close(self):
        self.save_routes()

    def plot_travel_times_histogram(self, location: Dict):
        """
        Plot travel times for a given location as a horizontal histogram using Unicode characters.

        :param location: Dictionary containing location information (lat, lon, name)
        """
        origins = self.get_coordinates(self.config["origins"])
        destination = (location["lat"], location["lon"])
        travel_times = self.calculate_travel_times(origins, destination)

        # Convert travel times from seconds to minutes
        travel_times_minutes = [t // 60 for t in travel_times]

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
        print(f"Total trips: {len(travel_times)}")

    def plot_destinations(self, destinations: List[Tuple[Dict, float]]):
        """
        Plot all possible destinations as a bar chart with convenience scores on the y-axis.

        :param destinations: List of tuples containing destination info and convenience scores
        """
        names = [dest["name"] for dest, _ in destinations]
        scores = [score for _, score in destinations]

        plt.figure(figsize=(12, 6))
        plt.bar(names, scores)
        plt.title("Destination Convenience Scores")
        plt.xlabel("Destinations")
        plt.ylabel("Convenience Score (lower is better)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig("destination_scores.png")
        plt.close()


# Usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    finder = BestDestinationFinder(api_key, "locations_config.json")

    all_destinations = finder.find_best_destinations(len(finder.config["destinations"]))
    top_destinations = all_destinations[:5]

    print("Top 5 Best Destinations:")
    for i, (location, score) in enumerate(top_destinations, 1):
        print(f"{i}. {location['name']}")
        print(f"   Convenience score: {int(score)}")
        finder.plot_travel_times_histogram(location)
        print()

    finder.plot_destinations(all_destinations)

    finder.close()
