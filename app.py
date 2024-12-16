from flask import Flask, render_template_string, request
import requests
import pandas as pd
import plotly.express as px

# Initialize Flask app
app = Flask(__name__)

# Fetch meteorite data
URL = "https://data.nasa.gov/resource/gh4g-9sfh.json"
response = requests.get(URL)
meteorite_data = response.json()

# Preprocess the data
df = pd.DataFrame(meteorite_data)
df = df[["name", "recclass", "mass", "year", "reclat", "reclong"]].dropna(subset=["mass", "year"])
df["mass"] = df["mass"].astype(float)
df["year"] = pd.to_datetime(df["year"], errors="coerce").dt.year
df["reclat"] = pd.to_numeric(df["reclat"], errors="coerce")
df["reclong"] = pd.to_numeric(df["reclong"], errors="coerce")

# Step 3: Clean and Group Similar Types
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
    'Unknown': ['Unknown', 'Stone-uncl', 'Chondrite-ung'],
}
flattened_map = {subtype: group for group, subtypes in fusion_map.items() for subtype in subtypes}
df['recclass_clean'] = df['recclass'].map(flattened_map).fillna('Unknown')
meteorite_counts = df['recclass_clean'].value_counts()

@app.route("/")
def home():
    # Radial chart of cleaned categories
    class_summary = df['recclass_clean'].value_counts().reset_index()
    class_summary.columns = ['Class', 'Count']
    fig_radial = px.pie(class_summary, values='Count', names='Class', title="Meteorite Class Distribution")
    radial_html = fig_radial.to_html(full_html=False)

    # Datasheet with cleaned class
    datasheet_html = df[["name", "recclass", "recclass_clean", "mass", "year", "reclat", "reclong"]].to_html(index=False, classes="table table-hover table-striped")

    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Meteorite Datasheet</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <script src="https://cdn.jsdelivr.net/npm/jquery"></script>
        <script src="https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css">
        <style>
            .container {{ margin: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Meteorite Datasheet</h1>
            <h3>Class Distribution</h3>
            <div>{radial_html}</div>
            <h3>Searchable Datasheet</h3>
            <table id="meteoriteTable" class="table table-hover table-striped">{datasheet_html}</table>
        </div>
        <script>
            $(document).ready(function() {{
                $('#meteoriteTable').DataTable();
            }});
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)