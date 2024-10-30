import argparse
import os
from dotenv import load_dotenv
from runner import (
    BestDestinationFinder,
    RouteUpdater,
    interpolate_staff_locations,
    build_embedded_html,
)


def main():
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    parser = argparse.ArgumentParser(description="Meeting Location Finder")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Update locations command
    update_locations_parser = subparsers.add_parser(
        "update-locations", help="Update locations from file"
    )
    update_locations_parser.add_argument(
        "--source-file",
        default="people.js",
        help="Path to the source json for people locations",
    )

    # Update routes subcommand
    update_routes_parser = subparsers.add_parser(
        "update-routes", help="Update routes.json file"
    )
    update_routes_parser.add_argument(
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

    # Build embedded HTML subcommand
    build_html_parser = subparsers.add_parser(
        "build-html", help="Build self-contained HTML file"
    )
    build_html_parser.add_argument(
        "--config", default="locations_config.json", help="Path to the config file"
    )
    build_html_parser.add_argument(
        "--routes", default="routes.json", help="Path to the routes file"
    )
    build_html_parser.add_argument(
        "--output", default="location_finder.html", help="Path to the output HTML file"
    )

    args = parser.parse_args()

    if not api_key:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set.")
        return

    if (
        args.command != "build-html"
        and args.command != "update-locations"
        and not os.path.exists(args.config)
    ):
        print(f"Error: Config file not found: {args.config}")
        print("Please make sure the config file exists and the path is correct.")
        return

    try:
        if args.command == "update-locations":
            interpolate_staff_locations(args.source_file)
        elif args.command == "update-routes":
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
        elif args.command == "build-html":
            if not os.path.exists(args.config):
                print(f"Warning: Config file not found: {args.config}")
                print("Using default config if available.")
            if not os.path.exists(args.routes):
                print(f"Warning: Routes file not found: {args.routes}")
                print("Using default routes if available.")
            build_embedded_html(args.config, args.routes, args.output)
            print(f"Self-contained HTML file created: {args.output}")
        else:
            parser.print_help()
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        print("Please make sure the required files exist and the paths are correct.")


if __name__ == "__main__":
    main()
