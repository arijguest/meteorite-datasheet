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

def classify_meteorite(recclass):
    """
    Classify meteorites into broader categories based on their recclass.
    """
    if pd.isna(recclass):
        return 'Unknown'
    recclass = str(recclass).strip()
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
        df = df.dropna(subset=['mass', 'reclat', 'reclong', 'year'])

        # Create mass categories
        mass_bins = [0, 10, 100, 1000, 10000, 1000000, float('inf')]
        mass_labels = ['Microscopic (0-10g)', 'Small (10-100g)', 'Medium (100g-1kg)',
                       'Large (1-10kg)', 'Very Large (10kg-1t)', 'Massive (>1t)']
        df['mass_category'] = pd.cut(df['mass'], bins=mass_bins, labels=mass_labels, right=True)

        # Format mass and year for display
        df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f} g" if pd.notnull(x) else "Unknown")
        df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")

        return df

    except Exception as e:
        logger.error(f"Error processing data: {e}")
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
    Create Plotly visualizations: radial plot, time distribution with animation, animated map, and heatmap.
    """
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

        # Ensure 'year' is integer
        df['year'] = df['year'].astype(int)

        # Animated Global Map
        fig_map = px.scatter_mapbox(
            df,
            lat='reclat',
            lon='reclong',
            color='recclass_clean',
            size='size',
            animation_frame='year',
            animation_group='name',
            hover_name='name',
            hover_data={
                'Lat': df['reclat'],
                'Long': df['reclong'],
                'Class': df['recclass'],
                'Mass': df['mass_with_units'],
                'Year': df['year_formatted'],
                'Fall': df['fall'],
            },
            color_discrete_map=COLORS,
            opacity=0.8,
            height=800,
        )
        fig_map.update_layout(
            mapbox=dict(style="carto-darkmatter", center=dict(lat=0, lon=0), zoom=0.3),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            updatemenus=[{
                'buttons': [{
                    'args': [None, {'frame': {'duration': 100, 'redraw': True}, 'fromcurrent': True, 'transition': {'duration': 0}}],
                    'label': 'Play',
                    'method': 'animate'
                }],
                'type': 'buttons',
                'showactive': False,
                'x': 0.05,
                'y': 0.05
            }],
        )
        map_html = fig_map.to_html(full_html=False, include_plotlyjs='cdn', div_id='map')

        # Cumulative Animated Heatmap
        df_sorted = df.sort_values('year')
        years = df_sorted['year'].unique()
        frames_heatmap = []
        for year in years:
            df_cumulative = df_sorted[df_sorted['year'] <= year]
            frame = go.Frame(
                data=go.Densitymapbox(
                    lat=df_cumulative['reclat'],
                    lon=df_cumulative['reclong'],
                    radius=10,
                    colorscale='Viridis',
                    showscale=False,
                ),
                name=str(year)
            )
            frames_heatmap.append(frame)

        fig_heatmap = go.Figure(
            data=go.Densitymapbox(
                lat=[],
                lon=[],
                radius=10,
                colorscale='Viridis',
                showscale=False,
            ),
            frames=frames_heatmap
        )
        fig_heatmap.update_layout(
            mapbox=dict(style="carto-darkmatter", center=dict(lat=0, lon=0), zoom=0.3),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            updatemenus=[{
                'buttons': [{
                    'args': [None, {'frame': {'duration': 100, 'redraw': True}, 'fromcurrent': True, 'transition': {'duration': 0}}],
                    'label': 'Play',
                    'method': 'animate'
                }],
                'type': 'buttons',
                'showactive': False,
                'x': 0.05,
                'y': 0.05
            }],
        )
        heatmap_html = fig_heatmap.to_html(full_html=False, include_plotlyjs='cdn', div_id='heatmap')

        # Time Distribution Plot with Moving Vertical Bar
        fig_time = px.histogram(
            df,
            x="year",
            color="recclass_clean",
            color_discrete_map=COLORS,
            labels={"year": "Discovery", "count": "Count"},
            opacity=0.8,
            nbins=100
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
            xaxis=dict(range=[df['year'].min(), df['year'].max()]),
        )

        # Add vertical line for current year
        fig_time.add_shape(
            type='line',
            x0=df['year'].min(),
            y0=0,
            x1=df['year'].min(),
            y1=df['year'].value_counts().max(),
            line=dict(color='red', width=2, dash='dot'),
            xref='x',
            yref='y',
            name='Current Year',
        )

        # Create frames for the time histogram
        frames_time = []
        for year in sorted(df['year'].unique()):
            # Update vertical line position
            frame = go.Frame(
                data=[go.Bar(
                    x=fig_time.data[0].x,
                    y=fig_time.data[0].y,
                    marker_color=fig_time.data[0].marker.color
                )],
                layout=go.Layout(
                    shapes=[dict(
                        type='line',
                        x0=year,
                        y0=0,
                        x1=year,
                        y1=df['year'].value_counts().max(),
                        line=dict(color='red', width=2, dash='dot'),
                        xref='x',
                        yref='y'
                    )]
                ),
                name=str(year)
            )
            frames_time.append(frame)

        fig_time.frames = frames_time
        fig_time.update_layout(
            updatemenus=[{
                'buttons': [{
                    'args': [None, {'frame': {'duration': 100, 'redraw': True}, 'fromcurrent': True, 'transition': {'duration': 0}}],
                    'label': 'Play',
                    'method': 'animate'
                }],
                'type': 'buttons',
                'showactive': False,
                'x': 0.05,
                'y': 0.95
            }]
        )
        time_html = fig_time.to_html(full_html=False, include_plotlyjs='cdn', div_id='time')

        return radial_html, time_html, map_html, heatmap_html

    except Exception as e:
        logger.error(f"Error creating visualizations: {e}")
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
