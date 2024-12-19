from flask import Flask, render_template, jsonify, request
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

# Enhanced descriptions with more detail
METEORITE_DESCRIPTIONS = {
    'L-type': 'Low iron ordinary chondrites (L) contain 20-25% total iron, 19-22% iron metal, and olivine (Fa23-25). These are among the most common meteorites found on Earth.',
    'H-type': 'High iron ordinary chondrites (H) contain 25-31% total iron, 15-19% iron metal, and olivine (Fa16-20). They represent some of the oldest material in our solar system.',
    'LL-type': 'Low iron, low metal ordinary chondrites (LL) contain 19-22% total iron, 2% iron metal, and olivine (Fa26-32). These rare specimens provide insights into early solar system formation.',
    'Carbonaceous': 'Primitive meteorites containing organic compounds, water-bearing minerals and stony materials. They are crucial for understanding the origin of life in our solar system.',
    'Enstatite': 'Rare meteorites formed in very reducing conditions, containing high amounts of enstatite. They provide unique insights into solar system chemistry.',
    'Achondrite': 'Igneous rocks formed by melting in their parent bodies, lacking chondrules. These meteorites represent processed material from differentiated bodies.',
    'Iron': 'Composed mainly of iron-nickel metal with minor amounts of sulfides and carbides. They represent core material from destroyed planetesimals.',
    'Mesosiderite': 'Stony-iron meteorites consisting of approximately equal amounts of metal and silicate. They provide evidence of major collisions between asteroids.',
    'Martian': 'Meteorites originating from Mars, showing characteristic Martian atmospheric gases. These rare specimens are our only physical samples from Mars.',
    'Lunar': 'Meteorites originating from the Moon, matching Apollo mission samples. They help us understand lunar geology and history.',
    'Pallasite': 'Stony-iron meteorites consisting of olivine crystals embedded in iron-nickel metal. They are among the most beautiful meteorites known.',
    'Unknown': 'Meteorites with uncertain or unclassified composition. Further research is needed to determine their origin.',
    'Other': 'Other meteorite types not classified in the main categories. These unique specimens often lead to new discoveries.'
}

# Global variable to store the dataset
df_global = None

# Global cache for visualizations
visualizations_cache = {}

def classify_meteorite(recclass):
    """
    Classify meteorites into broader categories based on their recclass.
    """
    if pd.isna(recclass):
        return 'Unknown'
    recclass = str(recclass).strip()
    # Ensure 'LL' is checked before 'L' to avoid misclassification
    if recclass.startswith('LL'):
        return 'LL-type'
    elif recclass.startswith('L'):
        return 'L-type'
    elif recclass.startswith('H'):
        return 'H-type'
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
    """
    Load and process meteorite data from NASA.
    """
    try:
        if not os.path.exists('meteorite_data.csv'):
            # Fetch data from NASA API
            response = requests.get("https://data.nasa.gov/resource/gh4g-9sfh.json?$limit=50000", timeout=10)
            response.raise_for_status()
            df = pd.DataFrame(response.json())
            df.to_csv('meteorite_data.csv', index=False)
            logger.info("Data fetched from NASA and saved locally.")
        else:
            # Load data from local CSV
            df = pd.read_csv('meteorite_data.csv', on_bad_lines='skip')
            logger.info("Data loaded from local CSV.")

        # Convert columns to appropriate data types
        df['mass'] = pd.to_numeric(df['mass'], errors='coerce')
        df['year'] = pd.to_datetime(df['year'], errors='coerce').dt.year
        df['reclat'] = pd.to_numeric(df['reclat'], errors='coerce')
        df['reclong'] = pd.to_numeric(df['reclong'], errors='coerce')
        df['recclass_clean'] = df['recclass'].apply(classify_meteorite)

        # Remove rows with missing critical data
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=['mass', 'reclat', 'reclong', 'year'])

        # Create mass categories
        mass_bins = [0, 10, 100, 1000, 10000, 1000000, float('inf')]
        mass_labels = ['Microscopic (0-10g)', 'Small (10-100g)', 'Medium (100g-1kg)',
                       'Large (1-10kg)', 'Very Large (10kg-1t)', 'Massive (>1t)']
        df['mass_category'] = pd.cut(df['mass'], bins=mass_bins, labels=mass_labels, right=True)

        # Format mass and year for display
        df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f} g" if pd.notnull(x) else "Unknown")
        df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")

        logger.info(f"Processed data with {len(df)} records.")
        return df

    except Exception as e:
        logger.exception(f"Error processing data: {e}")
        return pd.DataFrame()

def load_data():
    """
    Load the dataset into the global variable when the app starts.
    """
    global df_global
    df_global = process_data()
    if df_global.empty:
        logger.error("Failed to load meteorite data during app initialization.")

# Load data at startup
load_data()

@app.route('/data')
def data():
    """
    Endpoint to provide data to DataTables via AJAX.
    """
    global df_global
    df = df_global

    if df.empty:
        logger.error("Dataframe is empty.")
        return jsonify({'data': [], 'recordsTotal': 0, 'recordsFiltered': 0}), 500

    # Parameters from DataTables
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

    # Prepare data for response
    data_records = df_page[['name', 'recclass', 'recclass_clean', 'mass_formatted',
                            'year_formatted', 'reclat', 'reclong', 'fall']].to_dict('records')

    # Return response in the format DataTables expects
    return jsonify({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data_records
    })

@app.before_request
def before_request():
    """
    Clean up memory before each request.
    """
    gc.collect()

def create_visualizations(df):
    """
    Create Plotly visualizations: radial plot, time distribution, global map, and heatmap.
    """
    global visualizations_cache
    if visualizations_cache:
        logger.info("Using cached visualizations.")
        return (visualizations_cache['radial_html'],
                visualizations_cache['time_html'],
                visualizations_cache['map_html'],
                visualizations_cache['heatmap_html'])

    logger.info("Generating new visualizations.")
    try:
        # Format mass for display and size for plotting
        def format_mass(x):
            if x >= 1e6:
                return f"{x / 1e6:.2f} tonnes"
            elif x >= 1e3:
                return f"{x / 1e3:.2f} kg"
            else:
                return f"{x:.2f} g"

        df['mass_with_units'] = df['mass'].apply(format_mass)
        df['size'] = df['mass'].apply(lambda x: np.log10(x + 1) * 2)

        # Radial Plot
        logger.info("Creating radial plot.")
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
            polar=dict(
                radialaxis=dict(type="log", showticklabels=False),
                angularaxis=dict()
            )
        )
        radial_html = fig_radial.to_html(full_html=False, include_plotlyjs='cdn', div_id='radial')
        logger.info("Radial plot created.")

        # Prepare data for animations
        df_animation = df[(df['year'] >= 1700) & (df['year'] <= 2013)].copy()
        df_animation['year'] = df_animation['year'].astype(int)
        df_animation['year_block'] = (df_animation['year'] // 3) * 3
        year_blocks = sorted(df_animation['year_block'].unique())
        logger.debug(f"Dataset for animations contains {len(df_animation)} records.")

        # Create frames with decreasing opacities
        frames = []
        for current_block in year_blocks:
            blocks_to_include = [current_block, current_block - 3, current_block - 6]
            opacities = [0.8, 0.4, 0.2]
            
            mask = df_animation['year_block'].isin(blocks_to_include)
            df_frame = df_animation[mask].copy()
            df_frame['opacity'] = df_frame['year_block'].apply(
                lambda x: opacities[blocks_to_include.index(x)] if x in blocks_to_include else 0
            )

            frame = go.Frame(
                data=[go.Scattermapbox(
                    lat=df_frame['reclat'],
                    lon=df_frame['reclong'],
                    mode='markers',
                    marker=dict(
                        size=df_frame['size'],
                        color=df_frame['recclass_clean'].map(COLORS),
                        opacity=df_frame['opacity']
                    ),
                    customdata=np.stack((
                        df_frame['name'],
                        df_frame['recclass'],
                        df_frame['mass_with_units'],
                        df_frame['year_formatted'],
                        df_frame['fall'],
                        df_frame['reclat'],
                        df_frame['reclong']
                    ), axis=-1),
                    hovertemplate=(
                        'Name: %{customdata[0]}<br>' +
                        'Class: %{customdata[1]}<br>' +
                        'Mass: %{customdata[2]}<br>' +
                        'Year: %{customdata[3]}<br>' +
                        'Fall: %{customdata[4]}<br>' +
                        'Lat: %{customdata[5]}<br>' +
                        'Long: %{customdata[6]}<extra></extra>'
                    )
                )],
                name=str(current_block)
            )
            frames.append(frame)

        # Create the map figure
        fig_map = go.Figure(data=frames[0].data, frames=frames)
        fig_map.update_layout(
            mapbox=dict(style="carto-darkmatter", center=dict(lat=0, lon=0), zoom=0.3),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            updatemenus=[{
                'type': 'buttons',
                'buttons': [{
                    'label': 'Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 500, 'redraw': True},
                        'fromcurrent': True,
                        'transition': {'duration': 0}
                    }]
                }],
                'showactive': False,
                'x': 0.1,
                'y': 0,
            }],
            sliders=[{
                'active': 0,
                'currentvalue': {'prefix': 'Year Block: '},
                'pad': {'t': 50},
                'steps': [{
                    'method': 'animate',
                    'label': str(block),
                    'args': [[str(block)], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate',
                        'transition': {'duration': 0}
                    }]
                } for block in year_blocks]
            }]
        )
        map_html = fig_map.to_html(full_html=False, include_plotlyjs='cdn', div_id='map')
        logger.info("Global map visualization created.")

        # Time Distribution Plot
        logger.info("Creating time distribution plot.")
        fig_time = px.histogram(
            df_animation,
            x="year",
            color="recclass_clean",
            color_discrete_map=COLORS,
            labels={"year": "Year", "count": "Count"},
            opacity=0.8,
            nbins=len(year_blocks)
        )
        fig_time.update_layout(
            template="plotly_dark",
            yaxis_type="log",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Year",
            yaxis_title="Total",
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(range=[1700, 2013]),
        )
        time_html = fig_time.to_html(full_html=False, include_plotlyjs='cdn', div_id='time')
        logger.info("Time distribution plot created.")

        # Store visualizations in cache
        visualizations_cache['radial_html'] = radial_html
        visualizations_cache['time_html'] = time_html
        visualizations_cache['map_html'] = map_html
        visualizations_cache['heatmap_html'] = ''

        return radial_html, time_html, map_html, ''

    except Exception as e:
        logger.exception(f"Error creating visualizations: {e}")
        return '', '', '', ''

@app.route("/")
def home():
    """
    Render the main dashboard page.
    """
    try:
        global df_global
        df = df_global
        if df.empty:
            logger.error("Empty dataframe in home route")
            return "Unable to fetch meteorite data", 503

        visualizations = create_visualizations(df)
        radial_html, time_html, map_html, heatmap_html = visualizations

        if not all([radial_html, time_html, map_html, heatmap_html]):
            logger.error("One or more visualizations failed to generate")
            return "Error generating visualizations", 500

        return render_template('layout.html',
                             descriptions=METEORITE_DESCRIPTIONS,
                             radial_html=radial_html,
                             time_html=time_html,
                             map_html=map_html,
                             heatmap_html=heatmap_html,
                             last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    except Exception as e:
        logger.exception(f"Error in home route: {e}")
        return "An error occurred while processing the request", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
