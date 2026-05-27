import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "datasets.db")
OUTPUT_HTML = os.path.join(os.path.dirname(__file__), "..", "data", "dataset_connections.html")

def fetch_data():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return None, None, None, None, None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Fetch searches
    cur.execute("SELECT id, query FROM searches")
    searches = [dict(row) for row in cur.fetchall()]

    # Fetch sources
    cur.execute("""
SELECT id, search_id, url, webdomain, crawl_status,
       title, description, tavily_score, rank_position,
       processed, timestamp
FROM sources
""")
    sources = [dict(row) for row in cur.fetchall()]

    # Fetch observations
    cur.execute("""
SELECT id, source_id, matched_dataset, title, description,
    entity_type, confidence, status, doi, license_,
    publisher, created_at
FROM observations
""")

    observations = [dict(row) for row in cur.fetchall()]

    # Fetch datasets
    cur.execute("""
SELECT id,
       title,
       description,
       doi,
       license_,
       publisher,
       access_level,
       keywords,
       paper_url,
       code_url,
       dataset_url,
       date_created,
       last_updated
FROM datasets;
""")
    datasets = [dict(row) for row in cur.fetchall()]

    # Top domains
    cur.execute("SELECT webdomain, COUNT(*) as cnt FROM sources WHERE webdomain IS NOT NULL GROUP BY webdomain ORDER BY cnt DESC LIMIT 5")
    top_domains = [{"domain": row["webdomain"], "count": row["cnt"]} for row in cur.fetchall()]

    stats = {
        "total_searches": len(searches),
        "total_sources": len(sources),
        "total_observations": len(observations),
        "total_datasets": len(datasets),
        "top_domains": top_domains,
        "scraped_sources": sum(1 for s in sources if s['crawl_status'] == 'scraped'),
        "high_conf_observations": sum(1 for o in observations if (o['confidence'] or 0.0) > 0.8)
    }

    conn.close()
    return searches, sources, observations, datasets, stats

def generate_html(searches, sources, observations, datasets, stats):
    nodes = []
    edges = []

    def get_node_id(entity_type, db_id):
        return f"{entity_type}_{db_id}"

    # -------------------------
    # SEARCHES
    # -------------------------
    import urllib.parse
    for s in searches:
        nodes.append({
            "id": get_node_id("search", s["id"]),
            "label": f"Search: {str(s['query'])[:30]}...",
            "group": "searches",
            "url": "https://www.google.com/search?q=" + urllib.parse.quote_plus(str(s["query"])),
            "meta": {
                "Type": "Search",
                "ID": s["id"],
                "Query": s["query"],
                "Topic": s.get("topic"),
                "Created": s.get("created_at")
            }
        })

    # -------------------------
    # SOURCES
    # -------------------------
    for s in sources:
        nodes.append({
            "id": get_node_id("source", s["id"]),
            "label": f"Source: {str(s['url'])[:30]}...",
            "group": "sources",
            "url": s["url"],
            "meta": {
                "Type": "Source",
                "ID": s["id"],
                "URL": s["url"],
                "Domain": s.get("webdomain"),
                "Title": s.get("title"),
                "Description": s.get("description"),
                "Score": s.get("tavily_score"),
                "Rank": s.get("rank_position"),
                "Status": s.get("crawl_status"),
                "Processed": s.get("processed"),
                "Timestamp": s.get("timestamp")
            }
        })

        if s["search_id"]:
            edges.append({
                "from": get_node_id("search", s["search_id"]),
                "to": get_node_id("source", s["id"])
            })

    # -------------------------
    # OBSERVATIONS
    # -------------------------
    for o in observations:
        nodes.append({
            "id": get_node_id("obs", o["id"]),
            "label": f"Obs: {str(o['title'] or 'Unknown')[:30]}...",
            "group": "observations",
            "meta": {
                "Type": "Observation",
                "ID": o["id"],
                "Title": o.get("title"),
                "Description": o.get("description"),
                "Entity Type": o.get("entity_type"),
                "Confidence": o.get("confidence"),
                "Status": o.get("status"),
                "DOI": o.get("doi"),
                "License": o.get("license_"),
                "Publisher": o.get("publisher"),
                "Created": o.get("created_at")
            }
        })

        if o["source_id"]:
            edges.append({
                "from": get_node_id("source", o["source_id"]),
                "to": get_node_id("obs", o["id"])
            })

        if o["matched_dataset"]:
            edges.append({
                "from": get_node_id("obs", o["id"]),
                "to": get_node_id("dataset", o["matched_dataset"])
            })

    # -------------------------
    # DATASETS
    # -------------------------
    for d in datasets:
        nodes.append({
            "id": get_node_id("dataset", d["id"]),
            "label": f"Dataset: {str(d['title'])[:30]}...",
            "group": "datasets",
            "meta": {
                "Type": "Dataset",
                "ID": d["id"],
                "Title": d.get("title"),
                "Description": d.get("description"),
                "DOI": d.get("doi"),
                "License": d.get("license_"),
                "Publisher": d.get("publisher"),
                "Access": d.get("access_level"),
                "Keywords": d.get("keywords"),
                "Paper URL": d.get("paper_url"),
                "Code URL": d.get("code_url"),
                "Dataset URL": d.get("dataset_url"),
                "Created": d.get("date_created"),
                "Updated": d.get("last_updated")
            }
        })

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
<title>Dataset Graph</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>

<style>
body {{ margin:0; font-family:Segoe UI; }}
#mynetwork {{ width:100vw; height:100vh; }}

#popup {{
    position:absolute;
    left:20px;
    bottom:20px;
    width:400px;
    max-height:60vh;
    overflow:auto;
    background:white;
    padding:15px;
    border-radius:8px;
    box-shadow:0 4px 10px rgba(0,0,0,0.2);
    display:none;
}}

table {{
    width:100%;
    border-collapse:collapse;
    font-size:13px;
}}

td {{
    border-bottom:1px solid #eee;
    padding:6px;
    vertical-align:top;
}}

td:first-child {{
    font-weight:bold;
    width:40%;
    color:#2c3e50;
}}

h4 {{ margin-top:0; }}
button {{
    margin-top:10px;
    padding:6px 10px;
    border:none;
    background:#2c3e50;
    color:white;
    border-radius:4px;
    cursor:pointer;
}}
</style>
</head>

<body>

<div id="mynetwork"></div>

<div id="popup">
    <h4 id="popup-title"></h4>
    <div id="popup-content"></div>
    <button onclick="closePopup()">Close</button>
</div>

<script>
var nodes = new vis.DataSet({json.dumps(nodes)});
var edges = new vis.DataSet({json.dumps(edges)});

var network = new vis.Network(
    document.getElementById('mynetwork'),
    {{nodes:nodes, edges:edges}},
    {{
        nodes: {{ shape:'dot', size:16 }},
        groups: {{
            searches: {{ color: {{background:'#D2B4DE'}} }},
            sources: {{ color: {{background:'#FAD7A1'}} }},
            observations: {{ color: {{background:'#A9CCE3'}} }},
            datasets: {{ color: {{background:'#A9DFBF'}}, size:22 }}
        }},
        physics: {{
            solver:'forceAtlas2Based',
            stabilization: {{iterations:120}}
        }}
    }}
);

function renderTable(meta) {{
    let html = "<table>";
    for (let key in meta) {{
        let val = meta[key];
        if (!val) continue;

        if (typeof val === "string" && val.startsWith("http")) {{
            val = `<a href="${{val}}" target="_blank">${{val}}</a>`;
        }}

        html += `<tr><td>${{key}}</td><td>${{val}}</td></tr>`;
    }}
    html += "</table>";
    return html;
}}

function showPopup(node) {{
    document.getElementById("popup").style.display = "block";
    document.getElementById("popup-title").innerText = node.group.toUpperCase();
    document.getElementById("popup-content").innerHTML = renderTable(node.meta);
}}

function closePopup() {{
    document.getElementById("popup").style.display = "none";
}}

network.on("click", function(params) {{
    if (params.nodes.length > 0) {{
        let node = nodes.get(params.nodes[0]);
        showPopup(node);
    }}
}});

network.on("doubleClick", function(params) {{
    if (params.nodes.length > 0) {{
        let node = nodes.get(params.nodes[0]);
        if (node.url) {{
            window.open(node.url, "_blank");
        }}
    }}
}});
</script>

</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Visualization generated: {OUTPUT_HTML}")

def make_visualization():
    searches, sources, observations, datasets, stats = fetch_data()
    if searches is not None:
        generate_html(searches, sources, observations, datasets, stats)

if __name__ == "__main__":
    make_visualization()