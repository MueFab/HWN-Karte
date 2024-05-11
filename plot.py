"""
This script is designed to create an interactive map using Folium, displaying various points of interest and hiking
trails based on data from a CSV file and GPX files. Specifically, the script was created to visualize data from the
Harzer Wandernadel hiking challenge, which involves collecting stamps at various locations in the Harz mountains in
Germany.
It's particularly useful for visualizing geographical data related to hiking, such as waypoints, trails, and points of
interest like stamp locations for hikers.

Key Features:
- Loads geographic data from a CSV file, which includes latitude, longitude, and other attributes of points of interest.
- Dynamically generates markers on the map with different colors and icons based on specific conditions in the data
(e.g., visited, missing stamps).
- Supports adding different tile layers (e.g., OpenStreetMap, OpenTopoMap) to the map for varied visual presentations.
- Plots hiking trails from GPX files, which are displayed as colored lines on the map.
- Organizes markers and trails into different folium FeatureGroups for easy toggling on the map interface.
- Saves the generated map as an HTML file, which can be viewed in any web browser.

Usage:
- Ensure you have a CSV file with columns for latitude ('Lat'), longitude ('Long'),
stamp/point name ('Name') and ID ('ID').
- The column "Besucht" indicates whether a stamp has already been visited ("1") or not (empty).
- The column "Harzer Wandernadel" refers to the main challenge. All remaining columns refer to theme / bonus challenges.
- A "1" in a column indicates that the stamp must be collected for that challenge.
- Place GPX files for trails in the 'routes' directory. They will be automatically loaded and plotted on the map.
- Place GPX files for finished tours in the 'tours' directory. They will be automatically loaded and plotted on the map.
- Run the script to generate the map. The output will be an HTML file named 'map.html'.
- Open 'map.html' in a web browser to interact with the map.

Dependencies:
- folium: For map creation and manipulation.
- pandas: For data manipulation and reading from CSV.
- gpxpy: For parsing GPX files.
- os, itertools: For file and data manipulation.
- argparse: For command line argument parsing.

Note:
- This script is intended for use with specific data formats. Ensure your CSV and GPX files are compatible with
the script's expectations.
- Modify the script's parameters and functions to suit your specific data and requirements.

Author: Fabian Müntefering
Date: 2024-05-11
Version: 1.3
"""

import argparse
import json
import os
import enum
import gpxpy
import folium  # type: ignore
import pandas
import webbrowser
import itertools


class Translator:
    def __init__(self, localization_json_path: str):
        with open(localization_json_path, 'r', encoding='utf8') as f:
            self.locale = json.load(f)

    def translate(self, key: str) -> str:
        if key not in self.locale:
            return key
        return self.locale[key]


class StampStatus(enum.Enum):
    VISITED: int = 0  # Visited
    MAIN: int = 1  # Unvisited main challenge stamp
    THEME: int = 2  # Unvisited theme-challenges-only stamp
    BONUS: int = 3  # Unvisited stamp without associated challenge


class StampCount:
    def __init__(self, total: int, visited: int):
        self.total = total
        self.visited = visited


def load_csv_data(file_path: str, translator: Translator, delimiter: str = ';') -> pandas.DataFrame:
    """Load data from a CSV file."""
    try:
        return pandas.read_csv(file_path, delimiter=delimiter)
    except FileNotFoundError:
        print(translator.translate("FILE_NOT_FOUND").format(file_path))
        return pandas.DataFrame()  # Return an empty DataFrame if file is not found


def create_folium_map(df: pandas.DataFrame, translator: Translator, zoom_start: int = 11) -> folium.Map:
    """Create a Folium map object centered on the mean of the coordinates."""
    default_tiles = folium.TileLayer('OpenStreetMap', name='OpenStreetMap', attr='OpenStreetMap')
    return folium.Map(location=[df[translator.translate("COL_LAT")].mean(), df[translator.translate("COL_LON")].mean()],
                      zoom_start=zoom_start, tiles=default_tiles)


def add_folium_tile_layers(map_obj: folium.Map, translator: Translator, api_key: str) -> None:
    """Add various tile layers to the map."""
    tile_layers = [
        ('OpenTopoMap', 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
         translator.translate("OPENTOPO_COPYRIGHT"))
    ]

    if api_key != "":
        tile_layers.append(('OpenCycleMap',
                            'https://tile.thunderforest.com/cycle/{z}/{x}/{y}.png?apikey=' + api_key,
                            'OpenCycleMap'))
        tile_layers.append(('Outdoors',
                            'https://tile.thunderforest.com/outdoors/{z}/{x}/{y}.png?apikey=' + api_key,
                            'Outdoors'))
        tile_layers.append(('Transport',
                            'https://tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey=' + api_key,
                            'Transport'))

    tile_layers.append(('Cartodb Positron', 'Cartodb Positron', 'CartoDB'))

    for name, tile, attr in tile_layers:
        folium.TileLayer(tile, name=name, attr=attr).add_to(map_obj)


def get_stamp_type(row: pandas.Series, translator: Translator) -> StampStatus:
    """Determine the color of the marker based on conditions."""
    if row[translator.translate("COL_VISITED")] == 1:
        return StampStatus.VISITED
    elif row[translator.translate("COL_MAIN_CHALLENGE")] == 1:
        return StampStatus.MAIN
    elif 1 in row.values:
        return StampStatus.THEME
    else:
        return StampStatus.BONUS


def calculate_stamp_counts(df: pandas.DataFrame, translator: Translator) \
        -> tuple[dict[str, StampCount], dict[StampStatus, int]]:
    """Calculate the total and visited counts of stamps for each category."""
    categories = [col for col in df.columns if not is_special_col(col, translator)]
    counts = {}
    for category in categories:
        total = df[category].sum()
        visited = df[df[translator.translate("COL_VISITED")] == 1][category].sum()
        counts[category] = StampCount(total, visited)

    general_counts = {StampStatus.VISITED: 0, StampStatus.MAIN: 0, StampStatus.THEME: 0, StampStatus.BONUS: 0}
    for _, row in df.iterrows():
        general_counts[get_stamp_type(row, translator)] += 1

    return counts, general_counts


def is_special_col(col: str, translator: Translator) -> bool:
    """Check if a column is a special column that should not be considered for challenges."""
    return col in [translator.translate("COL_LAT"), translator.translate("COL_LON"),
                   translator.translate("COL_NAME"), translator.translate("COL_ID"),
                   translator.translate("COL_VISITED")]


def build_challenge_groups(df: pandas.DataFrame, counts: dict[str, StampCount], translator: Translator) \
        -> dict[str, folium.FeatureGroup]:
    """Build feature groups for each challenge category."""
    feature_groups = {}
    for col in df.columns:
        if is_special_col(col, translator):
            continue
        visited_count = int(counts[col].visited)
        total_count = int(counts[col].total)
        name = translator.translate("CHALLENGE_TITLE").format(col, visited_count, total_count)
        feature_groups[col] = folium.FeatureGroup(name=name, show=False)
    return feature_groups


def build_status_groups(general_counts: dict[StampStatus, int], translator: Translator) \
        -> dict[StampStatus, folium.FeatureGroup]:
    """Build feature groups for each stamp status category."""
    stamp_categories = [(StampStatus.VISITED, translator.translate("STAMP_STATUS_VISITED")),
                        (StampStatus.MAIN, translator.translate("STAMP_STATUS_MAIN")),
                        (StampStatus.THEME, translator.translate("STAMP_STATUS_THEME")),
                        (StampStatus.BONUS, translator.translate("STAMP_STATUS_BONUS"))]

    feature_groups = {
        stamp_type: folium.FeatureGroup(
            name=translator.translate("STAMP_STATUS").format(name.format(general_counts[stamp_type])),
            show=stamp_type == StampStatus.VISITED)
        for stamp_type, name in stamp_categories
    }
    return feature_groups


def build_marker_popup(row: pandas.Series, translator: Translator) -> str:
    """Build the popup content for a stamp marker based on the row data."""
    active_challenges = '</br>- '.join(
        col for col in row.index if row[col] == 1 and col != translator.translate("COL_VISITED"))
    marker_popup_header = "<b><u>Nr. {}</u></br>{}</b>".format(row[translator.translate("COL_ID")],
                                                               row[translator.translate("COL_NAME")])
    marker_popup = f"{marker_popup_header}</br>- {active_challenges}" \
        if active_challenges \
        else marker_popup_header
    return marker_popup.replace(' ', '&nbsp;').replace('-', "&#8209;")


def build_markers(df: pandas.DataFrame, feature_groups: dict[StampStatus, folium.FeatureGroup],
                  column_feature_groups: dict[str, folium.FeatureGroup], translator: Translator) -> None:
    """Build a marker for each stamp in the DataFrame and add it to the corresponding feature groups."""
    marker_colors = ['green', 'red', 'orange', 'gray']
    for _, row in df.iterrows():
        marker_type = get_stamp_type(row, translator)
        marker_color = marker_colors[marker_type.value]
        marker_popup = build_marker_popup(row, translator)
        marker = folium.Marker(
            location=[float(row[translator.translate("COL_LAT")]), float(row[translator.translate("COL_LON")])],
            popup=marker_popup,
            icon=folium.Icon(color=marker_color, icon="stamp", prefix="fa")
        )
        feature_groups[marker_type].add_child(marker)

        for col in row.index[row == 1].tolist():
            if not is_special_col(col, translator):
                marker = folium.Marker(
                    location=[float(row[translator.translate("COL_LAT")]), float(row[translator.translate("COL_LON")])],
                    popup=marker_popup,
                    icon=folium.Icon(color=marker_color, icon="stamp", prefix="fa")
                )
                column_feature_groups[col].add_child(marker)


def plot_markers(map_obj: folium.Map, df: pandas.DataFrame, translator: Translator) -> None:
    """Plot markers for each stamp in the DataFrame."""
    counts, general_counts = calculate_stamp_counts(df, translator)

    challenge_layers = build_challenge_groups(df, counts, translator)
    status_layers = build_status_groups(general_counts, translator)

    build_markers(df, status_layers, challenge_layers, translator)

    for group in status_layers.values():
        map_obj.add_child(group)
    for group in challenge_layers.values():
        map_obj.add_child(group)


def plot_gpx_tracks(map_obj: folium.Map, colors: list[str], translator: Translator,
                    directory: str = './routes', track_feature_group: folium.FeatureGroup = None) -> None:
    """Load and plot each GPX file's track."""
    color_cycle = itertools.cycle(colors)
    for file in sorted(os.listdir(directory)):
        if file.endswith('.gpx'):
            try:
                with open(os.path.join(directory, file), 'r') as gpx_file:
                    gpx = gpxpy.parse(gpx_file)
                track_color = next(color_cycle)
                for track in gpx.tracks:
                    plot_track(map_obj, track, track_color, translator, track_feature_group)
            except Exception as e:
                print(translator.translate("PROCESSING_ERROR").format(file, e))


def plot_track(map_obj: folium.Map, track, track_color: str,
               translator: Translator, tfg: folium.FeatureGroup = None) -> None:
    """Plot a single track on the map."""
    track_name = track.name or translator.translate("UNNAMED_TRACK")
    if tfg is None:
        track_feature_group = folium.FeatureGroup(name=translator.translate("TRAIL") + track_name, show=False)
    else:
        track_feature_group = tfg
    for segment in track.segments:
        points = [(point.latitude, point.longitude) for point in segment.points]
        folium.PolyLine(points, color=track_color, weight=2.5, opacity=1, popup=track_name).add_to(track_feature_group)
    map_obj.add_child(track_feature_group)


def parse_cli() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate an interactive map from CSV and GPX data.")
    parser.add_argument("csv_file", help="Path to the CSV file containing data points.")
    parser.add_argument("--routes_dir", default="./routes",
                        help="Directory containing GPX routes. Default is './routes'.")
    parser.add_argument("--tours_dir", default="./tours", help="Directory containing GPX tours. Default is './tours'.")
    parser.add_argument("--language_file", default="./localization/de.json",
                        help="Language file for localization. Default is './localization/de.json'.")
    parser.add_argument("--output", default="map.html", help="Name of the output HTML file. Default is 'map.html'.")
    parser.add_argument("--no_browser", action="store_true",
                        help="Do not automatically open the browser after generating the map.")
    parser.add_argument("--api_key", default="",
                        help="Thunderforest API key for additional tile layers.")

    # Parse arguments
    return parser.parse_args()


def plot_map(df: pandas.DataFrame, routes_dir: str, tours_dir: str, translator: Translator, api_key: str) -> folium.Map:
    """Create and plot the map with markers and GPX tracks."""
    map_osm = create_folium_map(df, translator)
    add_folium_tile_layers(map_osm, translator, api_key)
    plot_markers(map_osm, df, translator)
    trail_colors = ['blue', 'green', 'red', 'purple']
    plot_gpx_tracks(map_osm, trail_colors, translator, directory=routes_dir)

    tours_group = folium.FeatureGroup(name=translator.translate("FINISHED_TOURS"), show=True)
    finished_tour_colors = ['black']
    plot_gpx_tracks(map_osm, finished_tour_colors, translator, directory=tours_dir, track_feature_group=tours_group)
    map_osm.add_child(tours_group)
    folium.LayerControl().add_to(map_osm)
    return map_osm


def main() -> None:
    """Main function to generate the map."""
    args = parse_cli()

    # Load localization JSON
    translator = Translator(args.language_file)

    # Load data from CSV file
    df = load_csv_data(args.csv_file, translator)
    if df.empty:
        print(translator.translate("NO_DATA_TO_PLOT"))
        return

    # Create and populate the map
    map_osm = plot_map(df, args.routes_dir, args.tours_dir, translator, args.api_key)

    # Save the map
    map_osm.save(args.output)
    print(translator.translate("MAP_SAVED_SUCCESSFULLY").format(args.output))

    if not args.no_browser:
        # Open the map in the browser
        protocol = "file://"
        webbrowser.open(protocol + os.path.realpath(args.output))


if __name__ == "__main__":
    main()
