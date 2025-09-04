import streamlit as st
import pandas as pd
import requests
import sqlite3

# ---- API FUNCTIONS ----

def fetch_classifications():
    data_class = []
    for i in range(1, 8):
        response = requests.get(
            "https://api.harvardartmuseums.org/classification",
            params={"apikey": "9aed1d07-9679-4018-84eb-f13f236d9be6", "page": i}
        )
        records = response.json().get('records', [])
        data_class.extend(records)
    return pd.DataFrame(data_class)

def fetch_objects_by_classification(classification, pages=3):
    selected_objects = []
    for i in range(1, pages + 1):
        response = requests.get(
            "https://api.harvardartmuseums.org/object",
            params={
                "apikey": "9aed1d07-9679-4018-84eb-f13f236d9be6",
                "classification": classification,
                "page": i,
                "size": 100
            }
        )
        records = response.json().get('records', [])
        selected_objects.extend(records)
    return selected_objects


# Setup DB connection
conn = sqlite3.connect("harvard_artifacts.db", check_same_thread=False)
cursor = conn.cursor()

# ---- TABLE CREATION ----
def create_tables():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifact_metadata (
            id INTEGER PRIMARY KEY,
            title TEXT,
            culture TEXT,
            period TEXT,
            century TEXT,
            medium TEXT,
            dimensions TEXT,
            description TEXT,
            department TEXT,
            classification TEXT,
            accessionyear INTEGER,
            accessionmethod TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifact_media (
            objectid INTEGER,
            imagecount INTEGER,
            mediacount INTEGER,
            colorcount INTEGER,
            rank INTEGER,
            datebegin INTEGER,
            dateend INTEGER,
            FOREIGN KEY(objectid) REFERENCES artifact_metadata(id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifact_colors (
            objectid INTEGER,
            color TEXT,
            spectrum TEXT,
            hue TEXT,
            percent REAL,
            css3 TEXT,
            FOREIGN KEY(objectid) REFERENCES artifact_metadata(id)
        );
    """)
    conn.commit()

create_tables()

# Step 3: Insert to DB
def insert_to_db(data):
    for obj in data:
        # Table 1: artifact_metadata
        metadata = (
            obj.get('id'),
            obj.get('title'),
            obj.get('culture'),
            obj.get('period'),
            obj.get('century'),
            obj.get('medium'),
            obj.get('dimensions'),
            obj.get('description'),
            obj.get('department'),
            obj.get('classification'),
            obj.get('accessionyear'),
            obj.get('accessionmethod')
        )
        cursor.execute("INSERT OR IGNORE INTO artifact_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", metadata)

        # Table 2: artifact_media
        media = (
            obj.get('id'),
            obj.get('imagecount'),
            obj.get('mediacount'),
            obj.get('colorcount'),
            obj.get('rank'),
            obj.get('datebegin'),
            obj.get('dateend')
        )
        cursor.execute("INSERT OR IGNORE INTO artifact_media VALUES (?, ?, ?, ?, ?, ?, ?);", media)

        # Table 3: artifact_colors
        if 'colors' in obj and isinstance(obj['colors'], list):
            for color in obj['colors']:
                color_data = (
                    obj.get('id'),
                    color.get('color'),
                    color.get('spectrum'),
                    color.get('hue'),
                    color.get('percent'),
                    color.get('css3')
                )
                cursor.execute("INSERT INTO artifact_colors VALUES (?, ?, ?, ?, ?, ?);", color_data)

    conn.commit()



query_options = {
    # artifact_metadata
    "🏺 Artifacts from 11th Century (Byzantine)": 
        "SELECT * FROM artifact_metadata WHERE century = '11th century' AND culture = 'Byzantine';",

    "🌍 Unique Cultures": 
        "SELECT DISTINCT culture FROM artifact_metadata WHERE culture IS NOT NULL;",

    "🏺 Artifacts from Archaic Period": 
        "SELECT * FROM artifact_metadata WHERE period = 'Archaic';",

    "📅 Artifact Titles by Accession Year (Descending)": 
        "SELECT title, accessionyear FROM artifact_metadata ORDER BY accessionyear DESC;",

    "🏛️ Artifact Count per Department": 
        "SELECT department, COUNT(*) AS artifact_count FROM artifact_metadata GROUP BY department;",

    # artifact_media
    "🖼️ Artifacts with >1 Image": 
        "SELECT * FROM artifact_media WHERE imagecount > 1;",

    "⭐ Average Rank of Artifacts": 
        "SELECT AVG(rank) AS average_rank FROM artifact_media;",

    "🎨 Artifacts with More Colors than Media": 
        "SELECT * FROM artifact_media WHERE colorcount > mediacount;",

    "📆 Artifacts Created Between 1500 and 1600": 
        "SELECT * FROM artifact_media WHERE datebegin >= 1500 AND dateend <= 1600;",

    "🚫 Artifacts with No Media Files": 
        "SELECT COUNT(*) AS no_media_count FROM artifact_media WHERE mediacount = 0;",

    # artifact_colors
    "🌈 Distinct Hues": 
        "SELECT DISTINCT hue FROM artifact_colors WHERE hue IS NOT NULL;",

    "🎨 Top 5 Most Used Colors": 
        "SELECT color, COUNT(*) AS freq FROM artifact_colors GROUP BY color ORDER BY freq DESC LIMIT 5;",
    
    "📊 Avg Coverage % per Hue": 
        "SELECT hue, AVG(percent) AS avg_coverage FROM artifact_colors GROUP BY hue;",
    
    "🎯 Colors Used for a Given Artifact ID (e.g., 304727)": 
        "SELECT * FROM artifact_colors WHERE objectid = 304727;",

    "🔢 Total Number of Color Entries": 
        "SELECT COUNT(*) AS total_colors FROM artifact_colors;",
    # Join queries
    "🧵 Titles and Hues (Byzantine Artifacts)": 
        """
        SELECT m.title, c.hue 
        FROM artifact_metadata m
        JOIN artifact_colors c ON m.id = c.objectid
        WHERE m.culture = 'Byzantine';
        """,

    "🎨 Titles with Associated Hues": 
        """
        SELECT m.title, c.hue 
        FROM artifact_metadata m
        JOIN artifact_colors c ON m.id = c.objectid;
        """,

    "🧩 Titles, Cultures, Media Ranks (Where Period Exists)": 
        """
        SELECT m.title, m.culture, a.rank 
        FROM artifact_metadata m
        JOIN artifact_media a ON m.id = a.objectid
        WHERE m.period IS NOT NULL;
        """,

    "🔝 Top 10 Ranked Artifacts with Hue 'Grey'": 
        """
        SELECT m.title, a.rank, c.hue
        FROM artifact_metadata m
        JOIN artifact_media a ON m.id = a.objectid
        JOIN artifact_colors c ON m.id = c.objectid
        WHERE c.hue = 'Grey'
        ORDER BY a.rank DESC
        LIMIT 10;
        """,

    "📊 Artifacts per Classification (w/ Avg Media Count)": 
        """
        SELECT m.classification, COUNT(*) AS total_artifacts, AVG(a.mediacount) AS avg_media_count
        FROM artifact_metadata m
        JOIN artifact_media a ON m.id = a.objectid
        GROUP BY m.classification;
        """
}


# 🧠 MY CUSTOM SQL QUERIES (NEW ADDITIONS)
my_custom_queries = {
    "📅 Artifacts Acquired After 2000": 
        "SELECT * FROM artifact_metadata WHERE accessionyear > 2000;",

    "🏺 Sculptures with Dimensions Info": 
        "SELECT * FROM artifact_metadata WHERE classification = 'Sculpture' AND dimensions IS NOT NULL;",

    "🧵 Artifacts with Culture and Period Info": 
        "SELECT * FROM artifact_metadata WHERE culture IS NOT NULL AND period IS NOT NULL;",

    "🎨 Artifacts with More Than 3 Colors": 
        """
        SELECT objectid, COUNT(*) AS color_count
        FROM artifact_colors
        GROUP BY objectid
        HAVING COUNT(*) > 3;
        """,

    "🔍 Artifacts Missing Descriptions": 
        "SELECT * FROM artifact_metadata WHERE description IS NULL OR TRIM(description) = '';",

    "🏛️ Departments with Over 100 Artifacts": 
        """
        SELECT department, COUNT(*) AS total
        FROM artifact_metadata
        GROUP BY department
        HAVING total > 100;
        """,

    "📸 Artifacts with Highest Image Count (Top 10)": 
        """
        SELECT objectid, imagecount
        FROM artifact_media
        ORDER BY imagecount DESC
        LIMIT 10;
        """,

    "🎯 Top-Ranked Artifacts with Titles": 
        """
        SELECT m.title, a.rank
        FROM artifact_metadata m
        JOIN artifact_media a ON m.id = a.objectid
        WHERE a.rank = 1;
        """,

    "🎭 Artifacts with Same Start and End Date": 
        "SELECT * FROM artifact_media WHERE datebegin = dateend AND datebegin IS NOT NULL;",

    "🔗 Artifact Title, Medium, and Dominant Hue": 
        """
        SELECT m.title, m.medium, c.hue
        FROM artifact_metadata m
        JOIN artifact_colors c ON m.id = c.objectid
        WHERE c.percent = (
            SELECT MAX(c2.percent)
            FROM artifact_colors c2
            WHERE c2.objectid = m.id
        )
        LIMIT 50;
        """
}

import streamlit as st
import pandas as pd
import requests
from streamlit_lottie import st_lottie

# 1. ---------- Load Lottie from URL ----------
def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None

# 2. ---------- Load animations ----------
hero_anim = load_lottie_url("https://assets9.lottiefiles.com/packages/lf20_mjlh3hcy.json")      # Header
loading_anim = load_lottie_url("https://assets10.lottiefiles.com/packages/lf20_qp1q7mct.json")   # Loading
fetch_anim = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_vfzoart5.json")      # Fetching
db_anim = load_lottie_url("https://assets9.lottiefiles.com/packages/lf20_szlepvdh.json")         # DB
query_anim = load_lottie_url("https://assets4.lottiefiles.com/packages/lf20_j1adxtyb.json")      # Query

# 3. ---------- Page config ----------
st.set_page_config(page_title="Harvard Artifacts Explorer", layout="wide")

# 4. ---------- App Title with Animation ----------
st.title("🏛️ Harvard’s Artifacts Collection")

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown("Explore, store, and query Harvard's art collection.")
with col_head2:
    if hero_anim:
        st_lottie(hero_anim, height=120)

# --------------------------------------------
# SECTION 1: Select Classification & Fetch Data
# --------------------------------------------
st.header("🔍 Explore & Fetch Data")

col1, col2 = st.columns([2, 1])
with col1:
    df_classification = fetch_classifications()
    df_filtered = df_classification[df_classification['objectcount'] >= 2500]
    classification_options = df_filtered['name'].unique()[:5]
    selected_classification = st.selectbox("🎯 Choose classification", classification_options)

with col2:
    st.metric("📦 Total Classifications", len(classification_options))
    if fetch_anim:
        st_lottie(fetch_anim, height=120)

# Fetch Artifacts
if st.button("📥 Fetch Artifacts"):
    with st.spinner("⏳ Fetching artifacts from Harvard API..."):
        if loading_anim:
            st_lottie(loading_anim, height=120)
        artifacts = fetch_objects_by_classification(selected_classification, pages=3)
        st.session_state["fetched_data"] = artifacts
        st.success(f"✅ {len(artifacts)} records fetched for '{selected_classification}'")
        st.write("📝 Sample Record:")
        st.json(artifacts[0] if artifacts else {})

# --------------------------------------------
# SECTION 2: Insert into Database
# --------------------------------------------
st.header("📂 Store in Database")

col_db1, col_db2 = st.columns([1, 4])
with col_db1:
    if db_anim:
        st_lottie(db_anim, height=100)

with col_db2:
    if st.button("💾 Insert into Database"):
        if "fetched_data" in st.session_state:
            insert_to_db(st.session_state["fetched_data"])
            st.success("✅ Data successfully inserted into SQLite database.")
        else:
            st.warning("⚠️ Please fetch data before inserting.")

# --------------------------------------------
# SECTION 3: Explore Stored Data
# --------------------------------------------
st.header("📊 Explore Stored Data")

with st.expander("📁 Browse Database Tables"):
    tab1, tab2, tab3 = st.tabs(["🗄️ Artifact_Metadata", "🖼️ Artifact_Media", "🎨 Artifact_Colors"])

    with tab1:
        df1 = pd.read_sql_query("SELECT * FROM artifact_metadata", conn)
        st.dataframe(df1, use_container_width=True)

    with tab2:
        df2 = pd.read_sql_query("SELECT * FROM artifact_media", conn)
        st.dataframe(df2, use_container_width=True)

    with tab3:
        df3 = pd.read_sql_query("SELECT * FROM artifact_colors", conn)
        st.dataframe(df3, use_container_width=True)

# --------------------------------------------
# SECTION 4: Run SQL Queries
# --------------------------------------------
st.header("🔎 Run SQL Queries")

query_tabs = st.tabs(["📂 Prebuilt Queries", "🧪 Custom Queries"])

# --- Prebuilt Queries
with query_tabs[0]:
    col_q1, col_q2 = st.columns([1, 4])
    with col_q1:
        if query_anim:
            st_lottie(query_anim, height=100)
    with col_q2:
        selected_query = st.selectbox("📘 Choose a Prewritten Query", list(query_options.keys()))
        if st.button("▶️ Run Prebuilt Query"):
            try:
                result_df = pd.read_sql_query(query_options[selected_query], conn)
                st.success("✅ Query executed successfully!")
                st.dataframe(result_df, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Error running query:\n{e}")

# --- Custom Queries
with query_tabs[1]:
    selected_custom = st.selectbox("🧬 Choose a Custom Query", list(my_custom_queries.keys()))
    if st.button("▶️ Run Custom Query"):
        try:
            result_df = pd.read_sql_query(my_custom_queries[selected_custom], conn)
            st.success("✅ Custom query executed!")
            st.dataframe(result_df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error running custom query:\n{e}")
