from flask import Flask, render_template
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

# Initialize Flask app
app = Flask(__name__)

# Set up Mapbox
mapbox_token = os.environ.get('MAPBOX_ACCESS_TOKEN', '')
px.set_mapbox_access_token(mapbox_token)

# Color scheme
COLORS = {
    'L-type': '#FF6B6B', 'H-type': '#4ECDC4', 'LL-type': '#45B7D1',
    'Carbonaceous': '#96CEB4', 'Enstatite': '#FFEEAD', 'Achondrite': '#D4A5A5',
    'Iron': '#9A8C98', 'Mesosiderite': '#C9ADA7', 'Martian': '#F08080',
    'Lunar': '#87CEEB', 'Pallasite': '#DDA0DD', 'Unknown': '#808080',
    'Other': '#FFFFFF'
}

METEORITE_DESCRIPTIONS = {
    'L-type': 'Low iron ordinary chondrites (L) contain 20-25% total iron, 19-22% iron metal, and olivine (Fa23-25).',
    'H-type': 'High iron ordinary chondrites (H) contain 25-31% total iron, 15-19% iron metal, and olivine (Fa16-20).',
    'LL-type': 'Low iron, low metal ordinary chondrites (LL) contain 19-22% total iron, 2% iron metal, and olivine (Fa26-32).',
    'Carbonaceous': 'Primitive meteorites containing organic compounds, water-bearing minerals and stony materials.',
    'Enstatite': 'Rare meteorites formed in very reducing conditions, containing high amounts of enstatite.',
    'Achondrite': 'Igneous rocks formed by melting in their parent bodies, lacking chondrules.',
    'Iron': 'Composed mainly of iron-nickel metal with minor amounts of sulfides and carbides.',
    'Mesosiderite': 'Stony-iron meteorites consisting of approximately equal amounts of metal and silicate.',
    'Martian': 'Meteorites originating from Mars, showing characteristic Martian atmospheric gases.',
    'Lunar': 'Meteorites originating from the Moon, matching Apollo mission samples.',
    'Pallasite': 'Stony-iron meteorites consisting of olivine crystals embedded in iron-nickel metal.',
    'Unknown': 'Meteorites with uncertain or unclassified composition.',
    'Other': 'Other meteorite types not classified in the main categories.'
}

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
        response = requests.get("https://data.nasa.gov/resource/gh4g-9sfh.json", timeout=10)
        df = pd.DataFrame(response.json())
        
        # Clean and process data
        df['mass'] = pd.to_numeric(df['mass'], errors='coerce')
        df['year'] = pd.to_datetime(df['year'], errors='coerce').dt.year
        df['reclat'] = pd.to_numeric(df['reclat'], errors='coerce')
        df['reclong'] = pd.to_numeric(df['reclong'], errors='coerce')
        df['recclass_clean'] = df['recclass'].apply(classify_meteorite)
        
        # Remove rows with NaN values in critical columns
        df = df.dropna(subset=['mass', 'reclat', 'reclong'])
        
        # Create mass categories after removing NaN values
        df['mass_category'] = pd.qcut(df['mass'], q=5, labels=['Very Small', 'Small', 'Medium', 'Large', 'Very Large'])
        
        return df
    except Exception as e:
        print(f"Error processing data: {e}")
        return pd.DataFrame()

def create_visualizations(df):
    # Radial plot
    class_mass = df.groupby(['recclass_clean', 'mass_category']).size().unstack(fill_value=0)
    fig_radial = go.Figure()
    for mass_cat in class_mass.columns:
        fig_radial.add_trace(go.Barpolar(
            r=class_mass[mass_cat],
            theta=class_mass.index,
            name=mass_cat,
            marker_color=[COLORS.get(cls, '#FFFFFF') for cls in class_mass.index]
        ))
    fig_radial.update_layout(
        title="Meteorite Distribution by Class and Mass",
        template="plotly_dark",
        polar=dict(radialaxis=dict(type="log", title="Count"))
    )

    # Time distribution
    fig_time = px.histogram(df, x="year", color="recclass_clean",
                           title="Temporal Distribution of Meteorite Falls",
                           color_discrete_map=COLORS)

    # Global map with size scaling
    size_scale = df['mass'].apply(lambda x: np.log10(x + 1) * 2)  # Log scale for better visualization
    fig_map = px.scatter_mapbox(df, 
                               lat='reclat', 
                               lon='reclong',
                               color='recclass_clean',
                               size=size_scale,
                               hover_name='name',
                               hover_data={
                                   'mass': True,
                                   'year': True,
                                   'recclass': True
                               },
                               color_discrete_map=COLORS,
                               zoom=1)
    fig_map.update_layout(
        mapbox_style="carto-darkmatter",
        height=800,
        margin={"r":0,"t":50,"l":0,"b":0}
    )

    # Heatmap
    fig_heatmap = go.Figure(data=go.Densitymapbox(
        lat=df['reclat'],
        lon=df['reclong'],
        radius=5,
        colorscale='Viridis'
    ))
    fig_heatmap.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox=dict(center=dict(lat=0, lon=0), zoom=1),
        height=600,
        margin={"r":0,"t":50,"l":0,"b":0},
        title="Heatmap of Meteorite Landings"
    )

    return map(lambda fig: fig.to_html(full_html=False),
              [fig_radial, fig_time, fig_map, fig_heatmap])

@app.route("/")
def home():
    df = process_data()
    if df.empty:
        return "Unable to fetch meteorite data", 503

    visualizations = create_visualizations(df)
    radial_html, time_html, map_html, heatmap_html = visualizations

    df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f}g" if pd.notnull(x) else "Unknown")
    df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")
    
    datasheet_html = df[["name", "recclass", "recclass_clean", "mass_formatted", 
                        "year_formatted", "reclat", "reclong", "fall", "nametype"]].to_html(
        index=False,
        classes="table table-dark table-hover display",
        table_id="meteoriteTable",
        escape=False
    )

    return render_template('layout.html',
                         descriptions=METEORITE_DESCRIPTIONS,
                         radial_html=radial_html,
                         time_html=time_html,
                         map_html=map_html,
                         heatmap_html=heatmap_html,
                         datasheet_html=datasheet_html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
