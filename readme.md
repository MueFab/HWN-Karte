# Harzer Wandernadel Interactive Map Script

This Python script is designed to create an interactive map using Folium, specifically tailored for visualizing data from the Harzer Wandernadel hiking challenge in the Harz mountains, Germany. It displays various points of interest and hiking trails, making it a valuable tool for hikers and enthusiasts alike.

<p float="left" align="middle">
  <img src="https://raw.githubusercontent.com/MueFab/HWN-Karte/main/img/map1.png" width="400" />
  <img src="https://raw.githubusercontent.com/MueFab/HWN-Karte/main/img/map2.png" width="400" /> 
</p>

## Key Features

- **Geographic Data Loading**: Processes data from a CSV file, including latitude, longitude, and additional attributes of points of interest.
- **Dynamic Marker Generation**: Creates map markers with varied colors and icons, reflecting conditions like visited locations or missing stamps.
- **Tile Layer Support**: Incorporates different map tile layers (e.g., OpenStreetMap, OpenTopoMap) for enhanced visual representation.
- **Trail Plotting**: Visualizes hiking trails from GPX files as colored lines on the map.
- **Organized Display**: Utilizes folium FeatureGroups for a clean, toggle-friendly interface on the map.
- **HTML Output**: Exports the interactive map as an HTML file, easily viewable in any web browser.

## Usage

1. **Prepare Your Data**:
   - Ensure your CSV file contains columns for latitude ('Lat'), longitude ('Long'), stamp/point name ('Name'), and ID ('ID').
   - The 'Besucht' column indicates visited stamps (marked as "1").
   - The 'Harzer Wandernadel' column and other columns represent main and theme/bonus challenges, respectively.

2. **Trail Files**:
   - Place your GPX files for trails in the 'routes' directory.

3. **Run the Script**:
   - Execute the script to generate the map.
   - The default output is 'map.html'.

4. **View the Map**:
   - Open 'map.html' in a web browser to interact with your personalized hiking map. Except if `--no_browser` is passed, this will happen automatically. Use the menu in the top right corner to toggle the visibility of layers. 

## Dependencies

- **folium**: For map creation and manipulation.
- **pandas**: For data manipulation and reading from CSV files.
- **gpxpy**: For parsing GPX files.
- **os**, **itertools**: For file and data manipulation.
- **argparse**: For command line argument parsing.

## Installation

Ensure you have Python installed, and then install the required packages:

```bash
pip install folium pandas gpxpy
```

## Running the Script

Run the script from the command line, providing the necessary file names:

```bash
python script_name.py your_data.csv --gpx_dir your_gpx_directory --output your_output_map.html
```

Replace `script_name.py` with the actual script name, `your_data.csv` with your CSV file, `your_gpx_directory` with the path to your GPX files, and `your_output_map.html` with your desired output file name.

## Note

This script is specifically designed for certain data formats. Ensure compatibility of your CSV and GPX files with the script. Modify the script's parameters and functions to fit your unique data and requirements.
