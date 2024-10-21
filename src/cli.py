import argparse
import os
from dotenv import load_dotenv
from runner import BestDestinationFinder, RouteUpdater


def main():
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    parser = argparse.ArgumentParser(description="Meeting Location Finder")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Update routes subcommand
    update_parser = subparsers.add_parser(
        "update-routes", help="Update routes.json file"
    )
    update_parser.add_argument(
        "--config", default="locations_config.json", help="Path to the config file"
    )

    # Find best locations subcommand
    find_parser = subparsers.add_parser(
        "find-locations", help="Find best meeting locations"
    )
    find_parser.add_argument(
        "--config", default="locations_config.json", help="Path to the config file"
    )
    find_parser.add_argument(
        "--top", type=int, default=5, help="Number of top locations to display"
    )

    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        print("Please make sure the config file exists and the path is correct.")
        return

    try:
        if args.command == "update-routes":
            updater = RouteUpdater(api_key, args.config)
            updater.update_routes()
            updater.close()
        elif args.command == "find-locations":
            finder = BestDestinationFinder(api_key, args.config)
            all_destinations = finder.find_best_destinations(
                len(finder.config["destinations"])
            )
            top_destinations = all_destinations[: args.top]

            print(f"Top {args.top} Best Destinations:")
            for i, (location, score) in enumerate(top_destinations, 1):
                print(f"{i}. {location['name']}")
                print(f"   Convenience score: {int(score)}")
                finder.plot_travel_times_histogram(location)
                print()

            finder.plot_destinations(all_destinations)
            finder.close()
        else:
            parser.print_help()
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        print("Please make sure the config file exists and the path is correct.")


if __name__ == "__main__":
    main()
