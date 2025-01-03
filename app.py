from flask import Flask, render_template, jsonify, request, g
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import gc
from datetime import datetime
import logging
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Mapbox
mapbox_token = os.environ.get('MAPBOX_ACCESS_TOKEN', '')
px.set_mapbox_access_token(mapbox_token)

# Enhanced color scheme with carefully selected colors
COLORS = {
    'L-type': '#FF6B6B',
    'H-type': '#4ECDC4',
    'LL-type': '#45B7D1',
    'Carbonaceous': '#96CEB4',
    'Enstatite': '#FFEEAD',
    'Achondrite': '#D4A5A5',
    'Iron': '#9A8C98',
    'Mesosiderite': '#C9ADA7',
    'Martian': '#F08080',
    'Lunar': '#87CEEB',
    'Pallasite': '#DDA0DD',
    'Unknown': '#808080',
    'Other': '#FFFFFF'
}

# Meteorite descriptions
METEORITE_DESCRIPTIONS = {
'L-type': 'Low iron ordinary chondrites (L) contain approximately 20-25% total iron and 19-22% iron metal, with olivine compositions ranging from Fa23 to Fa25. These meteorites are among the most prevalent types found on Earth and are significant for understanding the early solar system (Gałązka-Friedman et al., 2019).',

'H-type': 'High iron ordinary chondrites (H) have total iron content between 25-31% and iron metal ranging from 15-19%, with olivine compositions from Fa16 to Fa20. They are believed to represent some of the oldest materials in our solar system, providing insights into the conditions of early planetary formation (Woźniak et al., 2019; Gałązka-Friedman et al., 2019).',

'LL-type': 'Low iron, low metal ordinary chondrites (LL) contain 19-22% total iron and about 2% iron metal, with olivine compositions from Fa26 to Fa32. These meteorites are rare and offer critical insights into the formation processes of the solar system (Woźniak et al., 2019; Gałązka-Friedman et al., 2019).',

'Carbonaceous': 'Carbonaceous chondrites are primitive meteorites rich in organic compounds and water-bearing minerals, crucial for understanding the origins of life in our solar system. Their complex chemistry provides a window into the early solar system conditions (Jacquet, 2022).',

'Enstatite': 'Enstatite chondrites are rare meteorites formed under highly reducing conditions, characterized by high enstatite content. They are essential for studying the chemical evolution of the solar system and the formation of terrestrial planets (Paliwal et al., 2000; Gałązka-Friedman et al., 2017).',

'Achondrite': 'Achondrites are igneous rocks formed by melting in their parent bodies, lacking chondrules. They represent processed materials from differentiated bodies, providing insights into planetary differentiation processes (Zurfluh et al., 2011).',

'Iron': 'Iron meteorites are primarily composed of iron-nickel metal, with minor sulfides and carbides. They are believed to represent core materials from differentiated planetesimals, offering clues about the early solar system’s thermal history (Zurfluh et al., 2011).',

'Mesosiderite': 'Mesosiderites are stony-iron meteorites consisting of approximately equal parts metal and silicate. They provide evidence of significant collisions between asteroids, revealing the dynamic processes in the asteroid belt (Soares et al., 2021).',

'Martian': 'Martian meteorites originate from Mars and exhibit characteristic Martian atmospheric gases. These specimens are invaluable as they represent the only physical samples we have from Mars, aiding in our understanding of the planet’s geology and history (Zurfluh et al., 2011).',

'Lunar': 'Lunar meteorites are sourced from the Moon and have compositions that match samples returned by the Apollo missions. They are critical for advancing our knowledge of lunar geology and the Moon’s formation (Zurfluh et al., 2011).',

'Pallasite': 'Pallasites are stony-iron meteorites characterized by olivine crystals embedded in iron-nickel metal. They are among the most aesthetically appealing meteorites and provide insights into the differentiation of planetesimals (Jacquet, 2022).',

'Unknown': 'Meteorites classified as unknown have uncertain or unclassified compositions. Further research is necessary to determine their origins and classifications, highlighting the complexities of meteorite taxonomy (Jacquet, 2022).',

'Other': 'Other meteorite types not classified in the main categories often lead to new discoveries and insights into the diversity of materials in the solar system. These unique specimens can provide critical data for understanding the formation and evolution of planetary bodies (Jacquet, 2022).'
}

# Global variable to store the dataset
df_global = None

# Define meteorite categories
def classify_meteorite(recclass):
    if pd.isna(recclass):
        return 'Unknown'
    
    recclass = str(recclass).strip()
    
    if recclass.startswith('L'):
        return 'L-type'
    elif recclass.startswith('H'):
        return 'H-type'
    elif recclass.startswith('LL'):
        return 'LL-type'
    elif recclass.startswith(('CI', 'CM', 'CR', 'CO', 'CV', 'CK')):
        return 'Carbonaceous'
    elif recclass.startswith(('EH', 'EL')):
        return 'Enstatite'
    elif recclass.startswith(('Iron', 'IAB', 'IC', 'IID', 'IIE', 'IIF', 'IIG', 'IIIAB', 'IVA', 'IVB')):
        return 'Iron'
    elif recclass.startswith('Mesosiderite'):
        return 'Mesosiderite'
    elif recclass.startswith('Martian'):
        return 'Martian'
    elif recclass.startswith('Lunar'):
        return 'Lunar'
    elif recclass.startswith('Pallasite'):
        return 'Pallasite'
    elif recclass.startswith(('Howardite', 'Eucrite', 'Diogenite', 'Angrite', 'Aubrite', 'Ureilite')):
        return 'Achondrite'
    elif recclass in ('Unknown', 'Stone-uncl', 'Chondrite-ung'):
        return 'Unknown'
    else:
        return 'Other'

def process_data():
    try:
        # Centralized data import
        data_file = 'meteorite_data.csv'

        # Fetch the count from the NASA API
        count_url = "https://data.nasa.gov/resource/gh4g-9sfh.json?$select=count(*)"
        response = requests.get(count_url)
        response.raise_for_status()
        count_data = response.json()
        api_count = int(count_data[0]['count'])

        # Check if the local data file exists
        if os.path.exists(data_file):
            # Load data from the local CSV file
            df = pd.read_csv(data_file, on_bad_lines='skip')
            local_count = len(df)
            logger.info(f"Local data has {local_count} records. API data has {api_count} records.")

            # Compare counts
            if local_count != api_count:
                logger.info("Local data is outdated. Fetching updated data from API.")
                # Fetch data from the NASA API endpoint (CSV format for efficiency)
                data_url = "https://data.nasa.gov/resource/y77d-th95.csv?$limit=50000"
                df = pd.read_csv(data_url)
                # Save a local copy for future use
                df.to_csv(data_file, index=False)
            else:
                logger.info("Local data is up to date.")
        else:
            logger.info("Local data file not found. Fetching data from API.")
            # Fetch data from the NASA API endpoint (CSV format for efficiency)
            data_url = "https://data.nasa.gov/resource/y77d-th95.csv?$limit=50000"
            df = pd.read_csv(data_url)
            df.to_csv(data_file, index=False)

        # Required columns
        required_columns = ['name', 'mass', 'year', 'reclat', 'reclong', 'recclass']

        # Check if required columns are present
        missing_columns = [col for col in required_columns if col not in df.columns]
        if (missing_columns):
            error_msg = f"Missing columns in data: {missing_columns}"
            logger.error(error_msg)
            raise KeyError(error_msg)

        # Process data
        df['mass'] = pd.to_numeric(df['mass'], errors='coerce')
        df['year'] = pd.to_datetime(df['year'], errors='coerce').dt.year
        df['reclat'] = pd.to_numeric(df['reclat'], errors='coerce')
        df['reclong'] = pd.to_numeric(df['reclong'], errors='coerce')
        df['recclass_clean'] = df['recclass'].apply(classify_meteorite)

        # Remove rows with NaN values in critical columns
        df = df.dropna(subset=['mass', 'reclat', 'reclong'])

        # Create mass categories with specific boundaries (in grams)
        mass_bins = [0, 10, 100, 1000, 10000, 1000000, float('inf')]  # 1 million grams = 1 tonne
        mass_labels = ['Microscopic (0-10g)', 'Small (10-100g)', 'Medium (100g-1kg)',
                       'Large (1-10kg)', 'Very Large (10kg-1t)', 'Massive (>1t)']
        df['mass_category'] = pd.cut(df['mass'], bins=mass_bins, labels=mass_labels, right=True)

        # Add century classification
        df['century'] = df['year'].apply(
            lambda x: f"{int(x // 100 + 1)}th Century" if pd.notnull(x) else "Unknown"
        )

        # Enhanced data formatting
        df['mass_formatted'] = df['mass'].apply(
            lambda x: f"{x:,.2f} g" if pd.notnull(x) else "Unknown"
        )
        df['year_formatted'] = df['year'].apply(
            lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown"
        )

        return df

    except Exception as e:
        logger.error(f"Error processing data: {e}")
        raise  # Re-raise the exception to be handled by the caller


# Load and process data when the app starts
def load_data():
    global df_global
    df_global = process_data()
    if df_global.empty:
        logger.error("Failed to load meteorite data during app initialization.")

# Call load_data() when the app starts
load_data()

@app.route('/data')
def data():
    global df_global
    df = df_global  # Use the pre-loaded dataset

    # Parameters sent by DataTables
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    search_value = request.args.get('search[value]', '')

    # Filtering
    if search_value:
        df_filtered = df[df['name'].str.contains(search_value, case=False, na=False)]
    else:
        df_filtered = df

    records_total = len(df)
    records_filtered = len(df_filtered)

    # Pagination
    df_page = df_filtered.iloc[start:start+length]

    # Select only the columns needed
    df_page = df_page[['name', 'recclass', 'recclass_clean', 'mass_formatted', 'year_formatted', 'reclat', 'reclong', 'fall']]

    # Prepare data for JSON response
    data = df_page.to_dict('records')

    # Return response in the format DataTables expects
    return jsonify({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data
    })

@app.before_request
def before_request():
    gc.collect()

def create_visualizations(df):
    try:
        def format_mass(x):
            if x >= 1e6:
                return f"{x / 1e6:.2f} tonnes"
            elif x >= 1e3:
                return f"{x / 1e3:.2f} kg"
            else:
                return f"{x:.2f} g"

        df['mass_with_units'] = df['mass'].apply(format_mass)
        df['size'] = df['mass'].apply(lambda x: np.log10(x + 1) * 2)

        class_mass = df.groupby(['recclass_clean', 'mass_category']).size().unstack(fill_value=0)
        fig_radial = go.Figure()

        for mass_cat in class_mass.columns:
            fig_radial.add_trace(go.Barpolar(
                r=class_mass[mass_cat],
                theta=class_mass.index,
                name=mass_cat,
                marker_color=[COLORS.get(cls, '#FFFFFF') for cls in class_mass.index],
                opacity=0.8,
                hovertemplate='Class: %{theta}<br>Mass Category: ' + mass_cat + '<br>Count: %{r}<extra></extra>'
            ))

        fig_radial.update_layout(
            template="plotly_dark",
            showlegend=False,
            margin=dict(l=0, r=0, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            polar=dict(
                radialaxis=dict(
                    type="log",
                    gridcolor="#444",
                    linecolor="#444",
                    showticklabels=False
                ),
                angularaxis=dict(
                    gridcolor="#444",
                    linecolor="#444"
                )
            )
        )

        fig_time = px.histogram(
            df,
            x="year",
            color="recclass_clean",
            color_discrete_map=COLORS,
            labels={"year": "Discovery", "count": "Count"},
            opacity=0.8
        )

        fig_time.update_layout(
            template="plotly_dark",
            yaxis_type="log",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Discovered",
            yaxis_title="Total",
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(range=[1700, 2013])
        )

        fig_time.update_traces(
            hovertemplate='Discovery: %{x}<br>Class: %{customdata}<br>Count: %{y}<extra></extra>',
            customdata=df['recclass_clean']
        )

        fig_map = px.scatter_mapbox(
            df,
            lat='reclat',
            lon='reclong',
            color='recclass',
            size='size',
            hover_name='name',
            hover_data={
                'Lat': df['reclat'],
                'Long': df['reclong'],
                'Class': df['recclass'],
                'Mass': df['mass_with_units'],
                'Year': df['year_formatted'],
                'Fall': df['fall'],
                'reclat': False,
                'reclong': False,
                'recclass': False,
                'size': False
            },
            color_discrete_map=COLORS
        )

        fig_map.update_layout(
            mapbox=dict(
                style="carto-darkmatter",
                center=dict(lat=30, lon=0),
                zoom=0
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=800,
            width=1000,
            showlegend=False
        )

        df_sorted = df.sort_values('year')
        df_sorted['year_bin'] = (df_sorted['year'] // 5) * 5
        year_bins = sorted(df_sorted['year_bin'].unique())

        fig_heatmap = go.Figure()

        frames = []
        for year_bin in year_bins:
            cumulative_df = df_sorted[df_sorted['year_bin'] <= year_bin]
            frames.append(
                go.Frame(
                    data=[go.Densitymapbox(
                        lat=cumulative_df['reclat'],
                        lon=cumulative_df['reclong'],
                        radius=10,
                        colorscale='Plasma',
                        showscale=False
                    )],
                    name=str(year_bin)
                )
            )

        fig_heatmap.frames = frames

        fig_heatmap.add_trace(go.Densitymapbox(
            lat=df_sorted[df_sorted['year_bin'] == year_bins[0]]['reclat'],
            lon=df_sorted[df_sorted['year_bin'] == year_bins[0]]['reclong'],
            radius=10,
            colorscale='Plasma',
            showscale=False
        ))

        fig_heatmap.update_layout(
            mapbox=dict(
                style="carto-darkmatter",
                center=dict(lat=30, lon=0),
                zoom=0
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=800,
            width=1000,
            showlegend=False,
            updatemenus=[{
                'buttons': [{
                    'args': [None, {
                        'frame': {'duration': 500, 'redraw': True},
                        'fromcurrent': True,
                        'transition': {'duration': 0},
                        'mode': 'immediate'
                    }],
                    'label': 'Play',
                    'method': 'animate'
                }],
                'direction': 'left',
                'pad': {'r': 10, 't': 87},
                'showactive': False,
                'type': 'buttons',
                'visible': False
            }]
        )

        animation_script = """
        <script>
        function animate() {
            Plotly.animate('heatmap', null, {
                frame: {duration: 500, redraw: true},
                transition: {duration: 10},
                mode: 'immediate',
                fromcurrent: true
            }).then(function() {
                requestAnimationFrame(animate);
            });
        }
        document.addEventListener('DOMContentLoaded', animate);
        </script>
        """

        radial_html = fig_radial.to_html(full_html=False, include_plotlyjs='cdn', div_id='radial')
        time_html = fig_time.to_html(full_html=False, include_plotlyjs='cdn', div_id='time')
        map_html = fig_map.to_html(full_html=False, include_plotlyjs='cdn', div_id='map')
        heatmap_html = fig_heatmap.to_html(full_html=False, include_plotlyjs='cdn', div_id='heatmap') + animation_script

        return radial_html, time_html, map_html, heatmap_html

    except Exception as e:
        logger.error(f"Error creating visualizations: {e}")
        return '', '', '', ''
        
@app.route("/")
def home():
    try:
        global df_global
        df = df_global
        if df.empty:
            return "Unable to fetch meteorite data", 503

        visualizations = create_visualizations(df)
        radial_html, time_html, map_html, heatmap_html = visualizations

        # Enhanced data formatting
        df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f}g" if pd.notnull(x) else "Unknown")
        df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")
        
        # Rename columns for display
        display_columns = {
            "name": "Meteorite Name",
            "recclass": "Classification",
            "recclass_clean": "Group Class",
            "mass_formatted": "Mass",
            "year_formatted": "Discovered",
            "reclat": "Latitude",
            "reclong": "Longitude",
            "fall": "Find/Fall",
        }
        
        df_display = df[list(display_columns.keys())].copy()
        df_display.columns = list(display_columns.values())

        return render_template('layout.html',
                             descriptions=METEORITE_DESCRIPTIONS,
                             radial_html=radial_html,
                             time_html=time_html,
                             map_html=map_html,
                             heatmap_html=heatmap_html,
                             last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return "An error occurred while processing the request", 500

def fetch_antarctic_meteorite_data():
    try:
        api_url = "https://astromaterials.jsc.nasa.gov/rest/antmetapi/samples"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df.to_csv('antarctic_meteorites.csv', index=False)
    except Exception as e:
        logger.error(f"Error fetching Antarctic meteorite data: {e}")
        raise

def check_and_update_antarctic_data():
    try:
        data_file = 'antarctic_meteorites.csv'
        if not os.path.exists(data_file):
            fetch_antarctic_meteorite_data()
        else:
            df = pd.read_csv(data_file)
            last_updated = datetime.fromtimestamp(os.path.getmtime(data_file))
            if (datetime.now() - last_updated).days > 1:
                fetch_antarctic_meteorite_data()
    except Exception as e:
        logger.error(f"Error checking/updating Antarctic data: {e}")
        raise

@app.route('/antarctic')
def antarctic():
    try:
        check_and_update_antarctic_data()
        df = pd.read_csv('antarctic_meteorites.csv')

        df['year'] = pd.to_datetime(df['year'], errors='coerce').dt.year

        COLORS = {
            "Iron, ungrouped": "red",
            "L-chondrite": "blue",
        }

        fig_time = px.histogram(
            df,
            x="year",
            color="recclass",
            color_discrete_map=COLORS,
            labels={"year": "Discovery", "count": "No. of Meteorites"},
            opacity=0.8
        )

        fig_time.update_layout(
            template="plotly_dark",
            yaxis_type="log",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Discovered",
            yaxis_title="No. of Meteorites",
            xaxis=dict(
                range=[1700, datetime.now().year]
            )
        )

        time_html = fig_time.to_html(full_html=False, include_plotlyjs='cdn', div_id='time')

        radial_html, map_html, heatmap_html = create_visualizations(df)[0], create_visualizations(df)[2], create_visualizations(df)[3]

        return render_template('antarctic.html', time_html=time_html, radial_html=radial_html, map_html=map_html, heatmap_html=heatmap_html)
    except Exception as e:
        logger.error(f"Error in antarctic route: {e}")
        return "An error occurred while processing the request", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
