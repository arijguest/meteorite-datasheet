from flask import Flask, render_template
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import gc
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

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
        
        df['mass'] = pd.to_numeric(df['mass'], errors='coerce')
        df['year'] = pd.to_datetime(df['year'], errors='coerce').dt.year
        df['reclat'] = pd.to_numeric(df['reclat'], errors='coerce')
        df['reclong'] = pd.to_numeric(df['reclong'], errors='coerce')
        df['recclass_clean'] = df['recclass'].apply(classify_meteorite)
        
        df = df.dropna(subset=['mass', 'reclat', 'reclong'])
        
        mass_labels = ['Microscopic (0-10g)', 'Small (10-100g)', 'Medium (100g-1kg)', 
                      'Large (1-10kg)', 'Massive (>10kg)']
        df['mass_category'] = pd.qcut(df['mass'], q=5, labels=mass_labels)
        
        return df
    except Exception as e:
        print(f"Error processing data: {e}")
        return pd.DataFrame()

def create_visualizations(df):
    # Common layout settings for consistent styling
    common_layout = {
        'template': 'plotly_dark',
        'showlegend': False,
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'margin': dict(t=30, b=0, l=0, r=0)
    }

    # Enhanced Radial plot
    class_mass = df.groupby(['recclass_clean', 'mass_category']).size().unstack(fill_value=0)
    fig_radial = go.Figure()
    for mass_cat in class_mass.columns:
        fig_radial.add_trace(go.Barpolar(
            r=class_mass[mass_cat],
            theta=class_mass.index,
            name=mass_cat,
            marker_color=[COLORS.get(cls, '#FFFFFF') for cls in class_mass.index],
            opacity=0.8,
            hovertemplate="Class: %{theta}<br>Count: %{r}<br>Mass Category: %{customdata}<extra></extra>",
            customdata=[mass_cat] * len(class_mass.index)
        ))
    fig_radial.update_layout(
        **common_layout,
        polar=dict(
            radialaxis=dict(
                type="log",
                title="Number of Specimens",
                gridcolor="#444",
                linecolor="#444"
            ),
            angularaxis=dict(
                gridcolor="#444",
                linecolor="#444"
            )
        )
    )

    # Enhanced Time distribution
    fig_time = px.histogram(
        df,
        x="year",
        color="recclass_clean",
        color_discrete_map=COLORS,
        labels={
            "year": "Year of Discovery",
            "count": "Number of Meteorites",
            "recclass_clean": "Classification"
        },
        opacity=0.8
    )
    fig_time.update_layout(
        **common_layout,
        xaxis_title="Year of Discovery",
        yaxis_title="Number of Meteorites"
    )

    # Enhanced Global map with complete world view
    size_scale = df['mass'].apply(lambda x: np.log10(x + 1) * 2)
    fig_map = px.scatter_mapbox(
        df,
        lat='reclat',
        lon='reclong',
        color='recclass_clean',
        size=size_scale,
        hover_name='name',
        hover_data={
            'mass': ':,.2f g | Mass',
            'year': '| Discovery Year',
            'recclass_clean': False,
            'fall': '| Fall Type'
        },
        color_discrete_map=COLORS,
        zoom=0,
        center=dict(lat=0, lon=0),
        opacity=0.7
    )
    fig_map.update_layout(
        **common_layout,
        mapbox=dict(
            style="carto-darkmatter",
            zoom=0,
            center=dict(lat=0, lon=0)
        ),
        height=600,
        margin=dict(t=0, b=0, l=0, r=0)
    )

    # Enhanced Heatmap with complete world view
    fig_heatmap = go.Figure(data=go.Densitymapbox(
        lat=df['reclat'],
        lon=df['reclong'],
        radius=20,
        colorscale='Viridis',
        showscale=True,
        hovertemplate="Latitude: %{lat:.2f}°<br>Longitude: %{lon:.2f}°<br>Density: %{z}<extra></extra>"
    ))
    fig_heatmap.update_layout(
        **common_layout,
        mapbox=dict(
            style="carto-darkmatter",
            zoom=0,
            center=dict(lat=0, lon=0)
        ),
        height=600,
        margin=dict(t=0, b=0, l=0, r=0)
    )

    # Generate common legend data
    legend_data = {
        'classes': list(COLORS.keys()),
        'colors': list(COLORS.values())
    }

    # Convert figures to HTML and return as a list
    html_figures = [fig.to_html(full_html=False, include_plotlyjs=True) for fig in [fig_radial, fig_time, fig_map, fig_heatmap]]

    return html_figures, legend_data

@app.route("/")
def home():
    df = process_data()
    if df.empty:
        return "Unable to fetch meteorite data", 503

    # Get the list of HTML figures and the legend data
    visualizations, legend_data = create_visualizations(df)
    radial_html, time_html, map_html, heatmap_html = visualizations

    df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f}g" if pd.notnull(x) else "Unknown")
    df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")
    
    display_columns = {
        "name": "Name",
        "recclass": "Scientific Classification",
        "recclass_clean": "Class",
        "mass_formatted": "Mass",
        "year_formatted": "Year",
        "reclat": "Latitude",
        "reclong": "Longitude",
        "fall": "Fall Type"
    }
    
    df_display = df[list(display_columns.keys())].copy()
    df_display.columns = list(display_columns.values())
    
    datasheet_html = df_display.to_html(
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
                         datasheet_html=datasheet_html,
                         legend_data=legend_data,
                         last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
