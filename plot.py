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
Date: 2023-12-03
Version: 1.0
"""

import argparse
import os
import gpxpy
import folium
import pandas as pd
import webbrowser
from itertools import cycle


def load_data(file_path, delimiter=';'):
    """Load data from a CSV file."""
    try:
        return pd.read_csv(file_path, delimiter=delimiter)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return pd.DataFrame()  # Return an empty DataFrame if file is not found


def create_map(df, zoom_start=11):
    """Create a Folium map object centered on the mean of the coordinates."""
    default_tiles = folium.TileLayer('OpenStreetMap', name='OpenStreetMap', attr='OpenStreetMap')
    return folium.Map(location=[df['Lat'].mean(), df['Long'].mean()], zoom_start=zoom_start, tiles=default_tiles)


def add_tile_layers(map_obj):
    """Add various tile layers to the map."""
    tile_layers = [
        ('OpenTopoMap', 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
         'Map data © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)'),
        ('Cartodb Positron', 'Cartodb Positron', 'CartoDB')
    ]
    for name, tile, attr in tile_layers:
        folium.TileLayer(tile, name=name, attr=attr).add_to(map_obj)


def get_marker_color(row):
    """Determine the color of the marker based on conditions."""
    if row['Besucht'] == 1:
        return 'green'
    elif row['Harzer Wandernadel'] == 1:
        return 'red'
    elif 1 in row.values:
        return 'orange'
    else:
        return 'gray'


def plot_markers(map_obj, df):
    """Plot each point from the DataFrame as a marker on the map."""
    feature_groups = {
        color: folium.FeatureGroup(name=f'Stempel: {name}', show=color == 'green')
        for color, name in zip(['green', 'red', 'orange', 'gray'],
                               ['Bereits besucht', 'Fehlende Hauptstempel', 'Fehlende Themenstempel',
                                'Fehlende reine Bonusstempel'])
    }
    special_cols = ['Lat', 'Long', "Name", "ID", "Besucht"]
    column_feature_groups = {col: folium.FeatureGroup(name=f'Heft: {col}', show=False) for col in df.columns if
                             col not in special_cols}

    for _, row in df.iterrows():
        marker_color = get_marker_color(row)
        active_challenges = '</br>- '.join(col for col in row.index if row[col] == 1 and col != 'Besucht')
        marker_popup_header = f"<b><u>Nr. {row['ID']}</u></br>{row['Name']}</b>"
        marker_popup = f"{marker_popup_header}</br>- {active_challenges}" \
            if active_challenges \
            else marker_popup_header
        marker_popup = marker_popup.replace(' ', '&nbsp;').replace('-', "&#8209;")
        marker = folium.Marker(
            location=[row['Lat'], row['Long']],
            popup=marker_popup,
            icon=folium.Icon(color=marker_color, icon="stamp", prefix="fa")
        )
        feature_groups[marker_color].add_child(marker)

        for col in row.index[row == 1].tolist():
            if col not in special_cols:
                marker = folium.Marker(
                    location=[row['Lat'], row['Long']],
                    popup=marker_popup,
                    icon=folium.Icon(color=marker_color, icon="stamp", prefix="fa")
                )
                column_feature_groups[col].add_child(marker)

    for group in feature_groups.values():
        map_obj.add_child(group)
    for group in column_feature_groups.values():
        map_obj.add_child(group)


def plot_gpx_tracks(map_obj, directory='./routes', colors=cycle(['blue', 'green', 'red', 'purple'])):
    """Load and plot each GPX file's track."""
    for file in sorted(os.listdir(directory)):
        if file.endswith('.gpx'):
            try:
                with open(os.path.join(directory, file), 'r') as gpx_file:
                    gpx = gpxpy.parse(gpx_file)
                track_color = next(colors)
                for track in gpx.tracks:
                    plot_track(map_obj, track, track_color)
            except Exception as e:
                print(f"Error processing {file}: {e}")


def plot_track(map_obj, track, track_color):
    """Plot a single track on the map."""
    track_name = track.name or 'Unnamed Track'
    track_feature_group = folium.FeatureGroup(name="Wanderweg: " + track_name, show=False)
    for segment in track.segments:
        points = [(point.latitude, point.longitude) for point in segment.points]
        folium.PolyLine(points, color=track_color, weight=2.5, opacity=1, popup=track_name).add_to(track_feature_group)
    map_obj.add_child(track_feature_group)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Generate an interactive map from CSV and GPX data.")
    parser.add_argument("csv_file", help="Path to the CSV file containing data points.")
    parser.add_argument("--gpx_dir", default="./routes", help="Directory containing GPX files. Default is './routes'.")
    parser.add_argument("--output", default="map.html", help="Name of the output HTML file. Default is 'map.html'.")
    parser.add_argument("--no_browser", action="store_true",
                        help="Do not automatically open the browser after generating the map.")

    # Parse arguments
    args = parser.parse_args()

    # Load data from CSV file
    df = load_data(args.csv_file)
    if df.empty:
        print("No data to plot.")
        return

    # Create and populate the map
    map_osm = create_map(df)
    add_tile_layers(map_osm)
    plot_markers(map_osm, df)
    plot_gpx_tracks(map_osm, directory=args.gpx_dir)
    folium.LayerControl().add_to(map_osm)

    # Save the map
    map_osm.save(args.output)
    print(f"Map successfully saved as '{args.output}'.")

    if not args.no_browser:
        # Open the map in the browser
        webbrowser.open('file://' + os.path.realpath(args.output))


if __name__ == "__main__":
    main()
