from flask import Flask, render_template_string, Response
from werkzeug.serving import WSGIRequestHandler
from functools import lru_cache
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import gc

WSGIRequestHandler.protocol_version = "HTTP/1.1"

# Initialize Flask app
app = Flask(__name__)

# Color scheme
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

# Scientific descriptions of meteorite classes
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

# Meteorite classification mapping
fusion_map = {
    'L-type': ['L', 'L4', 'L5', 'L6', 'L5/6', 'L4-6', 'L6/7', 'L~5', 'L~6', 'L3.0', 'L3.2', 'L3.4', 'L3.6', 'L3.7', 'L3.8', 'L3.9', 'L3.7-6', 'L3-4', 'L3-5', 'L3-6', 'L3-7', 'L3.9-6', 'L3.7-4', 'L3.0-3.9', 'L3.3-3.7', 'L3.3-3.5', 'L4/5'],
    'H-type': ['H', 'H4', 'H5', 'H6', 'H5/6', 'H4-6', 'H3', 'H3.4', 'H3.5', 'H3.6', 'H3.7', 'H3.8', 'H3.9', 'H3-4', 'H3-5', 'H3-6', 'H3.7-6', 'H3.8-5', 'H3.9-5', 'H3.9/4', 'H4/5', 'H4-5', 'H~4', 'H~5', 'H~6'],
    'LL-type': ['LL', 'LL4', 'LL5', 'LL6', 'LL7', 'LL3', 'LL3.2', 'LL3.4', 'LL3.6', 'LL3.8', 'LL3.9', 'LL4-5', 'LL4-6', 'LL5-6', 'LL5/6', 'LL3-4', 'LL3-5', 'LL3-6', 'LL3.8-6', 'LL3.1-3.5'],
    'Carbonaceous': ['CI1', 'CM1', 'CM2', 'CR2', 'CO3', 'CO3.2', 'CO3.3', 'CO3.4', 'CO3.5', 'CO3.6', 'CV3', 'CK4', 'CK5', 'CK6', 'CK3', 'CM-an', 'CV3-an'],
    'Enstatite': ['EH', 'EH3', 'EH4', 'EH5', 'EH6', 'EH7-an', 'EL3', 'EL4', 'EL5', 'EL6', 'EL7', 'EH3/4-an'],
    'Achondrite': ['Howardite', 'Eucrite', 'Diogenite', 'Angrite', 'Aubrite', 'Acapulcoite', 'Ureilite', 'Winonaite', 'Brachinite', 'Lodranite'],
    'Iron': ['Iron', 'Iron?', 'Iron, IAB', 'Iron, IAB-MG', 'Iron, IAB-ung', 'Iron, IIAB', 'Iron, IIE', 'Iron, IIIAB', 'Iron, IVA', 'Iron, IVB', 'Iron, IID', 'Iron, IIC', 'Iron, IC', 'Iron, IC-an'],
    'Mesosiderite': ['Mesosiderite', 'Mesosiderite-A1', 'Mesosiderite-A3', 'Mesosiderite-B', 'Mesosiderite-C', 'Mesosiderite-an'],
    'Martian': ['Martian (shergottite)', 'Martian (chassignite)', 'Martian (nakhlite)', 'Martian (basaltic breccia)', 'Martian'],
    'Lunar': ['Lunar', 'Lunar (anorth)', 'Lunar (gabbro)', 'Lunar (norite)', 'Lunar (basalt)', 'Lunar (bas. breccia)', 'Lunar (feldsp. breccia)'],
    'Pallasite': ['Pallasite', 'Pallasite, PMG', 'Pallasite, PMG-an', 'Pallasite, ungrouped'],
    'Unknown': ['Unknown', 'Stone-uncl', 'Chondrite-ung']
}

flattened_map = {subtype: group for group, subtypes in fusion_map.items() for subtype in subtypes}

def classify_meteorite(recclass):
    for category, classes in fusion_map.items():
        if recclass in classes:
            return category
    return "Other"

@lru_cache(maxsize=1)
def fetch_and_process_data():
    try:
        response = requests.get("https://data.nasa.gov/resource/gh4g-9sfh.json", timeout=10)
        response.raise_for_status()
        meteorite_data = response.json()
    except Exception:
        return pd.DataFrame()
    
    df = pd.DataFrame(meteorite_data)
    df = df.dropna(subset=["mass", "year"])
    
    # Process in chunks for better memory management
    chunk_size = 1000
    df_chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]
    
    for chunk in df_chunks:
        chunk["mass"] = pd.to_numeric(chunk["mass"], errors="coerce")
        chunk["year"] = pd.to_datetime(chunk["year"], errors="coerce").dt.year
        chunk["reclat"] = pd.to_numeric(chunk["reclat"], errors="coerce")
        chunk["reclong"] = pd.to_numeric(chunk["reclong"], errors="coerce")
        chunk["fall"] = chunk.get("fall", "")
        chunk["nametype"] = chunk.get("nametype", "")
        chunk['recclass_clean'] = chunk['recclass'].apply(classify_meteorite)
    
    df = pd.concat(df_chunks)
    
    # Create mass categories
    df = df.dropna(subset=['mass'])
    df['mass_category'] = pd.qcut(df['mass'], q=5, labels=['Very Small', 'Small', 'Medium', 'Large', 'Very Large'])
    
    return df

@lru_cache(maxsize=1)
def generate_visualizations(df):
    # Radial plot
    class_mass = df.groupby(['recclass_clean', 'mass_category']).size().unstack(fill_value=0)
    fig_radial = go.Figure()
    
    for i, mass_cat in enumerate(class_mass.columns):
        fig_radial.add_trace(go.Barpolar(
            r=class_mass[mass_cat],
            theta=class_mass.index,
            name=mass_cat,
            marker_color=[COLORS.get(cls, '#FFFFFF') for cls in class_mass.index]
        ))
    
    fig_radial.update_layout(
        title="Meteorite Distribution by Class and Mass",
        template="plotly_dark",
        showlegend=True,
        polar=dict(
            radialaxis=dict(type="log", title="Count"),
            angularaxis=dict(direction="clockwise")
        )
    )
    
    # Time distribution
    fig_time = px.histogram(
        df,
        x="year",
        color="recclass_clean",
        nbins=50,
        title="Temporal Distribution of Meteorite Falls",
        color_discrete_map=COLORS
    )
    
    # Global map
    fig_map = px.scatter_mapbox(
        df,
        lat='reclat',
        lon='reclong',
        color='recclass_clean',
        size='mass',
        hover_name='name',
        hover_data={
            'mass': True,
            'year': True,
            'fall': True,
            'recclass': True,
            'nametype': True
        },
        color_discrete_map=COLORS,
        zoom=1
    )
    
    fig_map.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox=dict(
            center=dict(lat=0, lon=0),
            zoom=1
        ),
        height=800,
        margin={"r":0,"t":50,"l":0,"b":0}
    )
    
    # Heatmap of meteorite landings
    fig_heatmap = go.Figure(data=go.Densitymapbox(
        lat=df['reclat'],
        lon=df['reclong'],
        radius=5,
        colorscale='Viridis',
        showscale=True,
        zauto=True
    ))
    
    fig_heatmap.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox=dict(center=dict(lat=0, lon=0), zoom=1),
        height=600,
        margin={"r":0,"t":50,"l":0,"b":0},
        title="Heatmap of Meteorite Landings"
    )
    
    return fig_radial, fig_time, fig_map, fig_heatmap

@app.route("/")
def home():
    df = fetch_and_process_data()
    if df.empty:
        return "Unable to fetch meteorite data", 503
    
    fig_radial, fig_time, fig_map, fig_heatmap = generate_visualizations(df)
    
    # Convert visualizations to HTML
    radial_html = fig_radial.to_html(full_html=False)
    time_html = fig_time.to_html(full_html=False)
    map_html = fig_map.to_html(full_html=False)
    heatmap_html = fig_heatmap.to_html(full_html=False)
    
    # Format data for display
    df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f}g" if pd.notnull(x) else "Unknown")
    df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")
    
    datasheet_html = df[["name", "recclass", "recclass_clean", "mass_formatted", 
                         "year_formatted", "reclat", "reclong", "fall", "nametype"]].to_html(
        index=False,
        classes="table table-dark table-hover display",
        table_id="meteoriteTable",
        escape=False
    )
    
    gc.collect()  # Clean up memory
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Advanced Meteorite Analysis Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/1.13.5/css/dataTables.bootstrap5.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/searchpanes/2.2.0/css/searchPanes.dataTables.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/select/1.7.0/css/select.dataTables.min.css" rel="stylesheet">
        
        <style>
            body { 
                background-color: #1a1a1a; 
                color: #ffffff; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .container-fluid { padding: 20px; }
            .chart-container { 
                margin-bottom: 30px; 
                background-color: #2d2d2d; 
                padding: 20px; 
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .description-table { 
                background-color: #2d2d2d; 
                border-radius: 10px; 
                padding: 20px;
                margin-bottom: 30px;
            }
            .map-container { height: 800px; }
            .dataTables_wrapper {
                padding: 20px;
                background-color: #2d2d2d;
                border-radius: 10px;
                margin-top: 20px;
            }
            .dataTables_filter input {
                background-color: #404040 !important;
                color: white !important;
                border: 1px solid #666 !important;
                border-radius: 4px;
                padding: 5px 10px;
            }
            .page-item.active .page-link {
                background-color: #666;
                border-color: #666;
            }
            .page-link {
                background-color: #404040;
                color: white;
            }
            .dt-button {
                background-color: #404040 !important;
                color: white !important;
                border: 1px solid #666 !important;
                border-radius: 4px !important;
                padding: 5px 15px !important;
                margin: 5px !important;
            }
            .dt-button:hover {
                background-color: #666 !important;
            }
            table.dataTable tbody tr {
                background-color: #2d2d2d;
                color: white;
            }
            table.dataTable tbody tr:hover {
                background-color: #404040;
            }
            .dataTables_info, .dataTables_length select, .dataTables_length label {
                color: white !important;
            }
            .dataTables_length select {
                background-color: #404040 !important;
                color: white !important;
                border: 1px solid #666 !important;
            }
            .dashboard-title {
                text-align: center;
                padding: 20px;
                background: linear-gradient(45deg, #2d2d2d, #404040);
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .section-title {
                color: #4ecdc4;
                margin-bottom: 20px;
                font-weight: 600;
            }
            .plotly-graph-div {
                margin: auto;
            }
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="dashboard-title">
                <h1>🌠 Global Meteorite Analysis Dashboard</h1>
                <p class="lead">Comprehensive analysis of meteorite landings across Earth</p>
            </div>
            
            <div class="row">
                <div class="col-md-6 chart-container">
                    <h3 class="section-title">Class Distribution & Mass Analysis</h3>
                    {{radial_html|safe}}
                </div>
                <div class="col-md-6 chart-container">
                    <h3 class="section-title">Historical Timeline</h3>
                    {{time_html|safe}}
                </div>
            </div>
            
            <div class="chart-container map-container">
                <h3 class="section-title">Interactive Global Distribution Map</h3>
                {{map_html|safe}}
            </div>

            <div class="chart-container">
                <h3 class="section-title">Global Heatmap of Meteorite Landings</h3>
                {{heatmap_html|safe}}
            </div>
            
            <div class="description-table">
                <h3 class="section-title">Meteorite Classification Guide</h3>
                <table class="table table-dark table-hover">
                    <thead>
                        <tr>
                            <th>Class</th>
                            <th>Scientific Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for class, description in descriptions.items() %}
                        <tr>
                            <td>{{class}}</td>
                            <td>{{description}}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <div class="chart-container">
                <h3 class="section-title">Comprehensive Meteorite Database</h3>
                {{datasheet_html|safe}}
            </div>
        </div>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.5/js/dataTables.bootstrap5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/searchpanes/2.2.0/js/dataTables.searchPanes.min.js"></script>
        <script src="https://cdn.datatables.net/select/1.7.0/js/dataTables.select.min.js"></script>
        
        <script>
            $(document).ready(function() {
                $('#meteoriteTable').DataTable({
                    dom: 'Bfrtip',
                    pageLength: 25,
                    buttons: [
                        'copy', 'csv', 'excel', 'pdf', 'print'
                    ],
                    order: [[3, 'desc']],
                    searchPanes: {
                        viewTotal: true
                    },
                    columnDefs: [
                        {
                            targets: [2, 6, 7],
                            searchable: true,
                            visible: true
                        }
                    ],
                    initComplete: function () {
                        this.api().columns().every(function () {
                            let column = this;
                            let title = column.header().textContent;
                            
                            let input = document.createElement('input');
                            input.placeholder = title;
                            input.className = 'form-control form-control-sm';
                            
                            $(input)
                                .appendTo($(column.header()))
                                .on('keyup change', function () {
                                    if (column.search() !== this.value) {
                                        column
                                            .search(this.value)
                                            .draw();
                                    }
                                });
                        });
                    }
                });
            });
        </script>
    </body>
    </html>
    """, descriptions=METEORITE_DESCRIPTIONS,
         radial_html=radial_html,
         time_html=time_html,
         map_html=map_html,
         heatmap_html=heatmap_html,
         datasheet_html=datasheet_html)

if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.run(host="0.0.0.0", port=8080, threaded=True)