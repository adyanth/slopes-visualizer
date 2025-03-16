import folium
import folium.map
import folium.plugins
import folium.utilities
import gpxpy
import gpxpy.gpx

def point_speed(pt: gpxpy.gpx.GPXTrackPoint):
    return float(pt.extensions[0].attrib["speed"])

def create_folium_map(g: gpxpy.gpx.GPX) -> folium.Map:
    assert len(g.tracks) == 1, "Need only one track"
    track = g.tracks[0]
    # Title: track.name

    tracksegs = track.segments if len(track.segments) % 2 == 0 else track.segments[1:]
    runs = [(lift, ski) for lift, ski in zip(*[iter(tracksegs)]*2)]
    start_run = runs[0][0]
    if len(track.segments) % 2 != 0:
        runs = [(None, track.segments[0])] + runs
        start_run = runs[0][1]
    # Number of runs: len(runs)

    start_x, start_y = start_run.points[0].latitude, start_run.points[0].longitude

    m = folium.Map((start_x, start_y), tiles='USGS.USImageryTopo', attr='Tiles courtesy of the <a href="https://usgs.gov/">U.S. Geological Survey</a>', max_zoom=20, control_scale=True, zoom_start=15)
    folium.TileLayer(overlay=True, tiles='OpenSnowMap.pistes', attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors & ODbL, &copy; <a href="https://www.opensnowmap.org/iframes/data.html">www.opensnowmap.org</a> <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>', min_zoom=9, max_zoom=18).add_to(m)
    folium.TileLayer(show=False, overlay=True, tiles='WaymarkedTrails.slopes', attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Map style: &copy; <a href="https://waymarkedtrails.org">waymarkedtrails.org</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)', max_zoom=18).add_to(m)
    
    poly_line_style = {"opacity": 1.0, "weight": 6}
    for i, (lift, ski) in enumerate(runs):
        # fg = folium.FeatureGroup(name=f"Run {i+1}", control=True, show=False if i else True).add_to(m)
        fg = folium.FeatureGroup(name=f"Run {i+1}", control=True, show=True).add_to(m)
        start, end = ski.points[0], ski.points[-1]
        ele = ski.get_elevation_extremes()
        folium.CircleMarker(
            location=(start.latitude,start.longitude),
            color="black",
            tooltip=f"Starting Elevation: {ele.maximum}m",
        ).add_to(fg)
        max_speed = point_speed(max(ski.points, key=point_speed))
        text = f"Ending Elevation: {ele.minimum:.2f}m\n Drop: {ele.maximum - ele.minimum:.2f}m\nDuration: {ski.get_duration() / 60:.2f}min\nMax Speed: {max_speed:.2f}kmph"
        folium.CircleMarker(
            location=(end.latitude,end.longitude),
            color="red",
            tooltip=text,
        ).add_to(fg)
        if lift:
            coords = map(lambda x: (x.latitude, x.longitude),  lift.points)
            folium.PolyLine(coords, tooltip="Lift", color="black", **poly_line_style).add_to(fg)
        coords = map(lambda x: (x.latitude, x.longitude),  ski.points)
        text = f"Max Speed: {max_speed:.2f}kmph"
        folium.PolyLine(coords, tooltip="Ski", popup=text, color="red", **poly_line_style).add_to(fg)

    geojson_datapoints = [pt for seg in track.segments for pt in seg.points]
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "elevation": pt.elevation,
                    "speed": point_speed(pt),
                    "azimuth": float(pt.extensions[0].attrib["azimuth"]),
                    "text": f"Elevation: {pt.elevation:.2f}m\nSpeed: {point_speed(pt):.2f}kmph",
                    "start": str(pt.time),
                    "end": str(
                        geojson_datapoints[i+1].time
                        if i < len(geojson_datapoints) - 1 
                        else pt.time
                    ),
                    "endExclusive": i < len(geojson_datapoints) - 1
                },
                "id": i,
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pt.longitude, pt.latitude]
                }
            }
            for i, pt in enumerate(geojson_datapoints)
        ]
    }
    timeline = folium.plugins.timeline.Timeline(
        geojson_data,
        pointToLayer=folium.utilities.JsCode("""
            function (geoJsonPoint, latlng) {
                console.log(geoJsonPoint, latlng);
                let azimuth = geoJsonPoint.properties.azimuth;
                var corrected_icon_azimuth = 334; // To make the icon horizontal
                corrected_icon_azimuth += -90; // To make the icon point north
                corrected_icon_azimuth += azimuth;
                corrected_icon_azimuth = parseInt(corrected_icon_azimuth % 360);
                return L.marker(latlng, {
                    icon: L.AwesomeMarkers.icon({
                        prefix: "fa",
                        icon: "person-skiing",
                        extraClasses: `fa-rotate-${corrected_icon_azimuth}`
                    }),
                    title: geoJsonPoint.properties.text,
                    alt: "Skiier",
                });
            }
        """)
    ).add_to(m)
    folium.plugins.timeline.TimelineSlider(
        auto_play=True,
        show_ticks=True,
        enable_keyboard_controls=True,
        steps=len(geojson_datapoints),
        # playback_duration=(geojson_datapoints[-1].time - geojson_datapoints[0].time).total_seconds() * 1000, # Realtime
        playback_duration=(geojson_datapoints[-1].time - geojson_datapoints[0].time).total_seconds() * 50, # 20x
    ).add_timelines(timeline).add_to(m)

    folium.LayerControl().add_to(m)
    folium.plugins.Fullscreen(
        position="topright",
        title="Expand",
        title_cancel="Exit",
        force_separate_button=True,
    ).add_to(m)
    folium.FitOverlays().add_to(m)

    return m

def generate_html(m: folium.Map):
    return m.get_root().render()

def process_gpx(gpx_xml: str):
    g = gpxpy.parse(gpx_xml)
    m = create_folium_map(g)
    return generate_html(m)

def local(filename: str):
    gpx_xml = ""
    with open("sample.gpx") as f:
        gpx_xml = f.read()
    print(process_gpx(gpx_xml))

def server():
    from flask import Flask, request, render_template, redirect, url_for
    from flask_caching import Cache
    import hashlib

    app = Flask(__name__)
    cache = Cache(app, config={"CACHE_TYPE": "SimpleCache"})

    @app.route("/", methods=["GET", "POST"])
    def entry():
        if request.method == "GET":
            return render_template("index.html")

        gpx_file = request.files["gpx"]
        gpx_xml = gpx_file.read()
        key = hashlib.sha256(gpx_xml).hexdigest()
        if not cache.has(key):
            print("Generating Map")
            html = process_gpx(gpx_xml)
            cache.add(key, html)
        return redirect(url_for("processed", key=key))

    @app.route("/processed/<key>", methods=["GET"])
    def processed(key: str):
        if not cache.has(key):
            return redirect(url_for("entry"))
        return cache.get(key)

    app.run(debug=False)

if __name__ == "__main__":
    # local()
    server()
