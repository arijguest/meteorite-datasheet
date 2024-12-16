from flask import Flask, render_template_string
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

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
    'Unknown': '#808080'
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
    'Unknown': 'Meteorites with uncertain or unclassified composition.'
}

# Fetch and process data
URL = "https://data.nasa.gov/resource/gh4g-9sfh.json"
response = requests.get(URL)
meteorite_data = response.json()

# Data preprocessing
df = pd.DataFrame(meteorite_data)
df = df.dropna(subset=["mass", "year"])
df["mass"] = pd.to_numeric(df["mass"], errors="coerce")
df["year"] = pd.to_datetime(df["year"], errors="coerce").dt.year
df["reclat"] = pd.to_numeric(df["reclat"], errors="coerce")
df["reclong"] = pd.to_numeric(df["reclong"], errors="coerce")
df["fall"] = df.get("fall", "")
df["nametype"] = df.get("nametype", "")

# Meteorite classification mapping
[Previous fusion_map remains the same]

# Clean classification
df['recclass_clean'] = df['recclass'].map(flattened_map).fillna('Unknown')

# Create mass bins for log scale
df['mass_category'] = pd.qcut(df['mass'], q=5, labels=['Very Small', 'Small', 'Medium', 'Large', 'Very Large'])

# Enhanced visualizations
# Radial plot with log scale and class segments
class_mass = df.groupby(['recclass_clean', 'mass_category']).size().unstack(fill_value=0)
fig_radial = go.Figure()

for mass_cat in class_mass.columns:
    fig_radial.add_trace(go.Barpolar(
        r=class_mass[mass_cat],
        theta=class_mass.index,
        name=mass_cat,
        marker_color=list(COLORS.values())
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

# Enhanced time distribution
fig_time = px.histogram(
    df,
    x="year",
    color="recclass_clean",
    nbins=50,
    title="Temporal Distribution of Meteorite Falls",
    color_discrete_map=COLORS
)

# Enhanced global map
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
    zoom=1,
    title="Global Meteorite Distribution"
)

fig_map.update_layout(
    mapbox_style="carto-darkmatter",
    mapbox=dict(
        center=dict(lat=0, lon=0),
        zoom=1
    ),
    height=800
)

@app.route("/")
def home():
    radial_html = fig_radial.to_html(full_html=False)
    time_html = fig_time.to_html(full_html=False)
    map_html = fig_map.to_html(full_html=False)
    
    # Enhanced datasheet with more columns and formatting
    df['mass_formatted'] = df['mass'].apply(lambda x: f"{x:,.2f}g" if pd.notnull(x) else "Unknown")
    df['year_formatted'] = df['year'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "Unknown")
    
    datasheet_html = df[["name", "recclass", "recclass_clean", "mass_formatted", 
                        "year_formatted", "reclat", "reclong", "fall", "nametype"]].to_html(
        index=False, 
        classes="table table-dark table-hover display",
        table_id="meteoriteTable",
        escape=False
    )
    
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
                    {{radial_html}}
                </div>
                <div class="col-md-6 chart-container">
                    <h3 class="section-title">Historical Timeline</h3>
                    {{time_html}}
                </div>
            </div>
            
            <div class="chart-container map-container">
                <h3 class="section-title">Interactive Global Distribution Map</h3>
                {{map_html}}
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
                {{datasheet_html}}
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
                            
                            // Create input element
                            let input = document.createElement('input');
                            input.placeholder = title;
                            input.className = 'form-control form-control-sm';
                            
                            // Add input to header
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
    """, descriptions=METEORITE_DESCRIPTIONS)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

