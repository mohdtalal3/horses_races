import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import os
import requests

# Page config
st.set_page_config(
    page_title="Horse Racing Dashboard",
    page_icon="🏇",
    layout="wide"
)

# === Google Drive Setup ===
FILE_ID = "1VGY4hMY1RJpEh4Hqs_qL_ci9Hp2bkW37"  # <-- Replace with your actual file ID
DB_FILE = "horse_races.db"

@st.cache_data
def download_db():
    if not os.path.exists(DB_FILE):
        with st.status("Downloading database from Google Drive...", expanded=True) as status:
            try:
                url = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
                st.info(f"Attempting to download from: {url}")
                
                response = requests.get(url, stream=True)
                if response.status_code != 200:
                    st.error(f"Download failed with status code: {response.status_code}")
                    st.stop()
                
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024  # 1 Kibibyte
                progress_bar = st.progress(0)
                
                with open(DB_FILE, "wb") as f:
                    dl = 0
                    for data in response.iter_content(block_size):
                        dl += len(data)
                        f.write(data)
                        if total_size > 0:
                            progress = min(dl / total_size, 1.0)
                            progress_bar.progress(progress)
                
                status.update(label="Database downloaded successfully!", state="complete")
                st.success(f"Database saved to {DB_FILE}")
            except Exception as e:
                st.error(f"Error downloading database: {e}")
                if os.path.exists(DB_FILE):
                    os.remove(DB_FILE)
                st.stop()
    
    return DB_FILE

# Check for and download the database file
db_path = download_db()
if not os.path.exists(db_path):
    st.error(f"Database file '{db_path}' not found and couldn't be downloaded.")
    st.stop()

# Direct SQLite connection to test column access
try:
    conn = sqlite3.connect(db_path)
    # Get a small sample to verify column names
    df_sample = pd.read_sql("SELECT * FROM races LIMIT 1", conn)
    actual_columns = df_sample.columns.tolist()
    conn.close()
    
    # Display columns for debugging
    st.sidebar.markdown("### Debug Info")
    with st.sidebar.expander("Available Columns"):
        st.write(actual_columns)
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.error("The database file may be corrupted or not have the expected structure.")
    st.stop()

# Function to load all data
@st.cache_data
def load_all_data():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM races", conn)
    conn.close()
    # Convert dates to datetime if they're not already
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    for date_col in date_cols:
        if df[date_col].dtype == 'object':
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    return df

# Title
st.title("🏇 Horse Racing Dashboard")

# Load all data into memory - fixed approach
try:
    with st.spinner("Loading race data..."):
        df = load_all_data()
    st.success(f"Loaded {len(df)} race records")
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Find the correct column names regardless of case
def find_column(df, name_part):
    # Exact match first
    if name_part in df.columns:
        return name_part
    
    # Case insensitive match
    for col in df.columns:
        if name_part.lower() == col.lower():
            return col
    
    # Partial match
    for col in df.columns:
        if name_part.lower() in col.lower():
            return col
    
    return None

# Find important columns
horse_id_col = find_column(df, "Horse ID")
horse_name_col = find_column(df, "Horse Name")
race_number_col = find_column(df, "Race Number")
race_date_col = find_column(df, "Race Date")
race_location_col = find_column(df, "Race Location")
race_class_col = find_column(df, "Race Class")
race_distance_col = find_column(df, "Race Distance")
jockey_booking_col = find_column(df, "Jockey Booking")
finish_position_col = find_column(df, "Finish Position")
barrier_col = find_column(df, "Barrier")
weight_carried_col = find_column(df, "Weight Carried")
direction_col = find_column(df, "Direction")
track_condition_col = find_column(df, "Track Condition")
weather_col = find_column(df, "Weather")
rail_col = find_column(df, "Rail")
straight_col = find_column(df, "Straight")
first_400m_col = find_column(df, "First 400m")
last_800m_col = find_column(df, "Last 800m")
last_600m_col = find_column(df, "Last 600m")
last_400m_col = find_column(df, "Last 400m")
last_200m_col = find_column(df, "Last 200m")
race_link_col = find_column(df, "Race Link")

# Define column order (using found column names) - updated to place Race Class after Race Location
ordered_columns = [
    col for col in [
        horse_id_col, horse_name_col, race_number_col, race_date_col, 
        race_location_col, race_class_col, race_distance_col, jockey_booking_col, 
        finish_position_col, barrier_col, weight_carried_col, 
        direction_col, track_condition_col, weather_col, rail_col, 
        straight_col, first_400m_col, last_800m_col, last_600m_col, 
        last_400m_col, last_200m_col, race_link_col
    ] if col is not None
]

# Add any columns that weren't in the specified order
remaining_columns = [col for col in df.columns if col not in ordered_columns]
ordered_columns.extend(remaining_columns)

# Create sidebar filters
st.sidebar.header("Filters")

# Horse name filter
if horse_name_col:
    horse_names = sorted(df[horse_name_col].unique())
    # Set first horse as default instead of "All"
    default_horse = horse_names[0] if horse_names else None
    selected_horse = st.sidebar.selectbox("Select Horse", options=horse_names, index=0)
else:
    st.warning("Horse Name column not found")
    selected_horse = None
    
# If no horse is selected, show a message
if not selected_horse:
    st.warning("Please select a horse to view data")
    st.stop()

# Date range filter
if race_date_col:
    # Filter to only show dates for the selected horse
    horse_dates = df[df[horse_name_col] == selected_horse][race_date_col]
    min_date = horse_dates.min().date() if not pd.isna(horse_dates.min()) else datetime.date.today()
    max_date = horse_dates.max().date() if not pd.isna(horse_dates.max()) else datetime.date.today()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
else:
    st.warning("Race Date column not found")
    date_range = None

# Location filter
if race_location_col:
    # Only show locations for the selected horse
    horse_locations = sorted(df[df[horse_name_col] == selected_horse][race_location_col].unique())
    selected_location = st.sidebar.multiselect("Select Location(s)", options=horse_locations)
else:
    st.warning("Race Location column not found")
    selected_location = []

# Race class filter
if race_class_col:
    # Only show race classes for the selected horse
    horse_classes = sorted(df[df[horse_name_col] == selected_horse][race_class_col].unique())
    selected_race_class = st.sidebar.multiselect("Select Race Class(es)", options=horse_classes)
else:
    selected_race_class = []

# Track condition filter
if track_condition_col:
    # Only show track conditions for the selected horse
    horse_conditions = sorted(df[df[horse_name_col] == selected_horse][track_condition_col].dropna().unique())
    selected_track_condition = st.sidebar.multiselect("Select Track Condition(s)", options=horse_conditions)
else:
    selected_track_condition = []

# Filter data based on selections - using in-memory filtering instead of SQL
# Start with just the selected horse
filtered_df = df[df[horse_name_col] == selected_horse].copy()

# Apply date filter
if date_range and len(date_range) == 2 and race_date_col:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df[race_date_col].dt.date >= start_date) &
        (filtered_df[race_date_col].dt.date <= end_date)
    ]

# Apply location filter
if selected_location and race_location_col:
    filtered_df = filtered_df[filtered_df[race_location_col].isin(selected_location)]

# Apply race class filter
if selected_race_class and race_class_col:
    filtered_df = filtered_df[filtered_df[race_class_col].isin(selected_race_class)]

# Apply track condition filter
if selected_track_condition and track_condition_col:
    filtered_df = filtered_df[filtered_df[track_condition_col].isin(selected_track_condition)]

# Reorder columns for display
filtered_df_ordered = filtered_df[ordered_columns]

# Display filtered results
st.header(f"Race Results for {selected_horse}")
st.write(f"Showing {len(filtered_df_ordered)} records")

# Display table with ordered columns
st.dataframe(filtered_df_ordered, use_container_width=True)

# Export functionality
if not filtered_df.empty:
    # Create a buffer to hold the Excel file
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Save the ordered dataframe to Excel
        filtered_df_ordered.to_excel(writer, index=False, sheet_name='Filtered Data')
    
    # Set filename with the horse name
    filename = f"{selected_horse}_races.xlsx"
    
    # Offer download button
    st.download_button(
        label=f"Download {selected_horse} Data",
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.ms-excel"
    )

# Performance metrics
st.header("Performance Metrics")

if finish_position_col:
    # Create metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Total races
    col1.metric("Total Races", len(filtered_df))
    
    # Wins (assuming 1st place is indicated by "1" in "Finish Position")
    wins = filtered_df[filtered_df[finish_position_col] == "1"].shape[0]
    col2.metric("Wins", wins)
    
    # Win percentage
    win_percent = (wins / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
    col3.metric("Win %", f"{win_percent:.1f}%")
    
    # Average finish position (numeric values only)
    try:
        # Convert finish positions to numeric, ignoring non-numeric values
        numeric_positions = pd.to_numeric(filtered_df[finish_position_col], errors="coerce")
        avg_position = numeric_positions.mean()
        col4.metric("Avg Position", f"{avg_position:.1f}")
    except:
        col4.metric("Avg Position", "N/A")
    
    # Show performance by track condition if data exists
    if track_condition_col:
        st.subheader("Performance by Track Condition")
        track_perf = filtered_df.groupby(track_condition_col).agg(
            Races=(horse_name_col, "count"),
            Wins=(finish_position_col, lambda x: (x == "1").sum())
        )
        track_perf["Win %"] = (track_perf["Wins"] / track_perf["Races"] * 100).round(1)
        st.dataframe(track_perf)

# Show data visualization
st.header("Visualizations")

if not filtered_df.empty:
    # Race count by location if location column exists
    if race_location_col:
        st.subheader("Races by Location")
        location_counts = filtered_df[race_location_col].value_counts().reset_index()
        location_counts.columns = ["Location", "Race Count"]
        st.bar_chart(location_counts.set_index("Location"))
    
    # Performance over time (if dates are available)
    if race_date_col:
        st.subheader("Performance Over Time")
        # Group by date and count races
        time_data = filtered_df.set_index(race_date_col).resample('M').size()
        st.line_chart(time_data)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Horse Racing Dashboard - Data Analytics Tool")
st.sidebar.info(f"Viewing data for: {selected_horse}")

# Add database info
st.sidebar.markdown("---")
if st.sidebar.checkbox("Show database info"):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM races")
        row_count = cursor.fetchone()[0]
        
        conn.close()
        
        st.sidebar.write(f"Database: {DB_FILE}")
        st.sidebar.write(f"Tables: {[t[0] for t in tables]}")
        st.sidebar.write(f"Total records: {row_count}")
        
        if os.path.exists(DB_FILE):
            size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
            st.sidebar.write(f"Database size: {size_mb:.2f} MB")
    except Exception as e:
        st.sidebar.error(f"Error getting database info: {e}") 