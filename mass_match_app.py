
import streamlit as st
import itertools
import pandas as pd
import io
import time
import json
from supabase import create_client, Client

# ===========================================================
# 🔌 Connect to Supabase (Cloud persistence)
# ===========================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===========================================================
# 📦 Load Saved Datasets from Supabase
# ===========================================================
@st.cache_data(show_spinner=False)
def load_cloud_datasets():
    try:
        data = supabase.table("datasets").select("*").execute().data
        datasets = {}
        for row in data:
            main = json.loads(row["main_list"])
            list2 = json.loads(row["list2_list"])
            datasets[row["name"]] = {"main": main, "list2_raw": list2}
        return datasets
    except Exception as e:
        st.warning(f"⚠️ Could not load cloud datasets: {e}")
        return {}

def save_cloud_dataset(name, main_list, list2_raw):
    try:
        supabase.table("datasets").upsert({
            "name": name,
            "main_list": json.dumps(main_list),
            "list2_list": json.dumps(list2_raw)
        }).execute()
    except Exception as e:
        st.error(f"❌ Failed to save dataset to cloud: {e}")

# ===========================================================
# --- Title ---
# ===========================================================
st.title("🧮 MassMatchFinder            UploadNewProjects")
st.markdown("""
Enter a target mass and tolerance, choose or create a dataset,  
and select which combinations to run.  
You can upload, type, or select from built-in lists.
""")

# ===========================================================
# --- Input ---
# ===========================================================
target = st.number_input("🎯 Target number to match", format="%.5f")
tolerance = st.number_input("🎯 Acceptable error/tolerance (e.g., 0.1)", value=0.1, format="%.5f")

# ===========================================================
# --- Data Configuration (Built-in Lists) ---
# ===========================================================
data_config = {
    "I_Tide_Linear": {
        "main": [
            174.058, 197.084, 127.063, 147.055, 87.055,
            200.095, 170.113, 207.113, 114.042, 114.042,
            101.047, 129.042, 131.040
        ],
        "list2_raw": [
            174.058, 173.051, 197.084, 127.063, 147.055,
            87.055, 200.095, 170.113, 207.113, 114.042,
            101.047, 129.042, 130.032, 131.040, 42.010,
            0.984, 2.015, '+71.037', '+242.109', '+56.06', '-15.977', '+252.082',
            '+230.11', '-18.010', '-14.015', '-17.026',
            '+100.05', '+222.06', '-33.987', '-1.007', '+1896.83'
        ]
    },
    "I_Tide_Syclic": {
        "main": [
            173.051, 197.084, 127.063, 147.055, 87.055,
            200.095, 170.113, 207.113, 114.042, 114.042,
            101.047, 129.042, 130.032
        ],
        "list2_raw": [
            87.055, 114.042, 130.032, '+71.037', '+56.06', '-15.977', '+1896.83'
        ]
    },
    "S_Tide": {
        "main": [
             138.066, 97.052, 128.058, 57.021, 101.047, 147.068, 101.047, 87.032, 115.026,
    163.063, 87.032, 128.094, 163.063, 113.084, 115.026, 129.042, 156.101, 71.037,
    71.037, 128.094, 115.026, 147.068, 113.084, 128.094, 186.079, 113.084, 129.042,
    87.032, 87.055, 57.021, 57.021, 87.032, 57.021, 87.032, 57.021, 129.042, 297.243
        ],
        "list2_raw": [
            138.066, 97.052, 128.058, 57.021, 101.047, 87.032, 115.026,
87.032, 128.094, 163.063, 113.084, 129.042, 156.101, 71.037,
115.026, 147.068, 186.079, 129.042,
129.042, 297.243, 42.010, 0.984, 2.015, '+71.037', '+242.109', '+56.06', '-15.977', '+252.082',
    '+230.11', '-18.010', '-14.015', '-17.026',
    '+100.05', '+222.06', '-33.987', '-1.007'
        ]
    }
}

# ===========================================================
# 🌐 Load Cloud Datasets and Merge
# ===========================================================
cloud_datasets = load_cloud_datasets()
data_config.update(cloud_datasets)

# ===========================================================
# 📤 Upload File
# ===========================================================
st.subheader("📤 Upload your own dataset (optional)")
uploaded_file = st.file_uploader("Upload a .csv or .txt file with one or two lists", type=["csv", "txt"])

def parse_uploaded_file(file):
    content = file.read().decode("utf-8").strip()
    try:
        df = pd.read_csv(io.StringIO(content))
        if df.shape[1] >= 2:
            main_list = df.iloc[:, 0].dropna().astype(float).tolist()
            list2_list = [str(x) for x in df.iloc[:, 1].dropna().tolist()]
            return main_list, list2_list
        else:
            main_list = df.iloc[:, 0].dropna().astype(float).tolist()
            return main_list, main_list
    except Exception:
        pass

    if "#MAIN" in content and "#LIST2" in content:
        main_part = content.split("#MAIN")[1].split("#LIST2")[0]
        list2_part = content.split("#LIST2")[1]
        main_list = [float(x.strip()) for x in main_part.splitlines() if x.strip() and not x.startswith("#")]
        list2_list = [x.strip() for x in list2_part.splitlines() if x.strip() and not x.startswith("#")]
        return main_list, list2_list

    try:
        items = [float(x.strip()) for x in content.replace("\n", ",").split(",") if x.strip()]
        return items, items
    except Exception:
        raise ValueError("Could not parse file format.")

if uploaded_file is not None:
    try:
        main_list, list2_list = parse_uploaded_file(uploaded_file)
        data_config["User_Uploaded"] = {"main": main_list, "list2_raw": list2_list}
        save_cloud_dataset("User_Uploaded", main_list, list2_list)
        st.success(f"✅ Uploaded list added! Main: {len(main_list)}, List2: {len(list2_list)} (saved to cloud)")
    except Exception as e:
        st.error(f"Error reading file: {e}")

# ===========================================================
# ✍️ Manual List Entry
# ===========================================================
st.subheader("✍️ Or manually add a new dataset")
with st.expander("➕ Add New Custom Dataset"):
    custom_name = st.text_input("Dataset name (e.g., MyExperiment1)")
    main_text = st.text_area("Main list values (comma or newline separated)", "")
    list2_text = st.text_area("List2 modifiers (optional — use + or - for signs)", "")

    if st.button("Add Custom Dataset"):
        try:
            main_list = [float(x.strip()) for x in main_text.replace("\n", ",").split(",") if x.strip()]
            list2_raw = [x.strip() for x in list2_text.replace("\n", ",").split(",") if x.strip()] if list2_text.strip() else main_list
            if not custom_name:
                custom_name = f"Custom_{len(data_config) + 1}"
            data_config[custom_name] = {"main": main_list, "list2_raw": list2_raw}
            save_cloud_dataset(custom_name, main_list, list2_raw)
            st.success(f"✅ Custom dataset '{custom_name}' added and saved to cloud.")
        except Exception as e:
            st.error(f"Error adding dataset: {e}")

# ===========================================================
# (Rest of your existing app: selection, calculations, etc.)
# ===========================================================
