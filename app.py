# Meteorites Datasheet

from flask import Flask, render_template_string
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

# Flask route: Home with datasheet and key stats
@app.route("/")
def home():
    # Summary of meteorite classes
    class_summary = df["recclass"].value_counts().head(10).to_frame().reset_index()
    class_summary.columns = ["Meteorite Class", "Count"]

    # Summary stats
    total_meteorites = len(df)
    avg_mass = df["mass"].mean()
    earliest = int(df["year"].min())
    latest = int(df["year"].max())

    # Datasheet
    datasheet_html = df.to_html(index=False, classes="table table-hover table-striped")

    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Meteorite Datasheet</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
            }}
            h1, h2 {{
                text-align: center;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: auto;
                padding: 20px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            .table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .table th, .table td {{
                border: 1px solid #ddd;
                padding: 8px;
            }}
            .table th {{
                background-color: #4CAF50;
                color: white;
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <h1>Meteorite Datasheet and Statistics</h1>
        <div class="container">
            <h2>Key Statistics</h2>
            <ul>
                <li>Total Meteorites: {total_meteorites}</li>
                <li>Average Mass: {avg_mass:.2f} grams</li>
                <li>Earliest Recorded Fall: {earliest}</li>
                <li>Most Recent Recorded Fall: {latest}</li>
            </ul>
            <h2>Top 10 Meteorite Classes</h2>
            {class_summary.to_html(index=False, classes="table table-hover table-striped")}
            <h2>Datasheet</h2>
            {datasheet_html}
        </div>
    </body>
    </html>
    """)

# Flask route: Interactive plots
@app.route("/graphs")
def graphs():
    # Mass distribution
    fig1 = px.histogram(df, x="mass", log_y=True, nbins=50, title="Mass Distribution of Meteorites", labels={"mass": "Mass (g)"})
    fig1_html = fig1.to_html(full_html=False)

    # Temporal trend
    year_grouped = df.groupby("year").size().reset_index(name="count")
    fig2 = px.line(year_grouped, x="year", y="count", title="Number of Meteorites by Year", labels={"year": "Year", "count": "Meteorite Count"})
    fig2_html = fig2.to_html(full_html=False)

    # Geographic heatmap
    fig3 = px.density_mapbox(df, lat="reclat", lon="reclong", z="mass", radius=10, mapbox_style="stamen-terrain",
                             title="Geographic Distribution of Meteorites", labels={"mass": "Mass (g)"})
    fig3.update_layout(mapbox_center={"lat": 0, "lon": 0}, mapbox_zoom=1)
    fig3_html = fig3.to_html(full_html=False)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Meteorite Interactive Graphs</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <h1>Meteorite Interactive Graphs</h1>
        <div>
            <h2>Mass Distribution</h2>
            {fig1_html}
        </div>
        <div>
            <h2>Temporal Trend</h2>
            {fig2_html}
        </div>
        <div>
            <h2>Geographic Heatmap</h2>
            {fig3_html}
        </div>
    </body>
    </html>
    """

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)