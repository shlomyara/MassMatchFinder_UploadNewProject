import streamlit as st
import itertools
import pandas as pd
import io
import time
from supabase import create_client, Client

# ===========================================================
# 🔧 Supabase setup
# ===========================================================
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===========================================================
# Helper functions
# ===========================================================
def save_dataset_to_cloud(name, main, list2):
    try:
        data = {"name": name, "main": main, "list2_raw": list2}
        # Upsert dataset
        res = supabase.table("datasets").upsert(data).execute()
        if res.get("status_code") not in (200, 201):
            st.error(f"❌ Failed to save dataset to cloud: {res.get('data')}")
        else:
            st.success(f"✅ Dataset '{name}' saved to cloud!")
    except Exception as e:
        st.error(f"❌ Error saving dataset to cloud: {e}")

def load_datasets_from_cloud():
    try:
        res = supabase.table("datasets").select("*").execute()
        datasets = {}
        if res.get("data"):
            for row in res["data"]:
                datasets[row["name"]] = {"main": row["main"], "list2_raw": row["list2_raw"]}
        return datasets
    except Exception as e:
        st.warning(f"Could not load datasets from cloud: {e}")
        return {}

def delete_dataset(name):
    try:
        supabase.table("datasets").delete().eq("name", name).execute()
    except Exception as e:
        st.error(f"❌ Failed to delete dataset from cloud: {e}")

def rename_dataset(old_name, new_name):
    try:
        # Fetch old dataset
        res = supabase.table("datasets").select("*").eq("name", old_name).execute()
        if res.get("data"):
            dataset = res["data"][0]
            dataset["name"] = new_name
            supabase.table("datasets").upsert(dataset).execute()
            supabase.table("datasets").delete().eq("name", old_name).execute()
    except Exception as e:
        st.error(f"❌ Failed to rename dataset in cloud: {e}")

def rerun():
    # Safe replacement for experimental_rerun
    st.session_state["rerun_flag"] = True

# ===========================================================
# Initialize session state for rerun
# ===========================================================
if "rerun_flag" not in st.session_state:
    st.session_state["rerun_flag"] = False

if st.session_state["rerun_flag"]:
    st.session_state["rerun_flag"] = False
    st.experimental_rerun()

# ===========================================================
# Title and description
# ===========================================================
st.title("🧮 MassMatchFinder with Cloud Datasets")
st.markdown("""
Enter a target mass and tolerance, choose or create a dataset,  
and select which combinations to run.  
Upload, type, or select from built-in or cloud lists.
""")

# ===========================================================
# Input
# ===========================================================
target = st.number_input("🎯 Target number to match", format="%.5f")
tolerance = st.number_input("🎯 Acceptable error/tolerance", value=0.1, format="%.5f")

# ===========================================================
# Built-in datasets
# ===========================================================
data_config = {
    "I_Tide_Linear": {
        "main": [174.058, 197.084, 127.063, 147.055, 87.055, 200.095, 170.113, 207.113, 114.042, 114.042, 101.047, 129.042, 131.040],
        "list2_raw": [174.058, 173.051, 197.084, 127.063, 147.055, 87.055, 200.095, 170.113, 207.113, 114.042, 101.047, 129.042, 130.032, 131.040, 42.010, 0.984, 2.015, '+71.037', '+242.109', '+56.06', '-15.977', '+252.082', '+230.11', '-18.010', '-14.015', '-17.026', '+100.05', '+222.06', '-33.987', '-1.007', '+1896.83']
    },
    "I_Tide_Syclic": {
        "main": [173.051, 197.084, 127.063, 147.055, 87.055, 200.095, 170.113, 207.113, 114.042, 114.042, 101.047, 129.042, 130.032],
        "list2_raw": [87.055, 114.042, 130.032, '+71.037', '+56.06', '-15.977', '+1896.83']
    },
    "S_Tide": {
        "main": [138.066, 97.052, 128.058, 57.021, 101.047, 147.068, 101.047, 87.032, 115.026, 163.063, 87.032, 128.094, 163.063, 113.084, 115.026, 129.042, 156.101, 71.037, 71.037, 128.094, 115.026, 147.068, 113.084, 128.094, 186.079, 113.084, 129.042, 87.032, 87.055, 57.021, 57.021, 87.032, 57.021, 87.032, 57.021, 129.042, 297.243],
        "list2_raw": [138.066, 97.052, 128.058, 57.021, 101.047, 87.032, 115.026, 87.032, 128.094, 163.063, 113.084, 129.042, 156.101, 71.037, 115.026, 147.068, 186.079, 129.042, 129.042, 297.243, 42.010, 0.984, 2.015, '+71.037', '+242.109', '+56.06', '-15.977', '+252.082', '+230.11', '-18.010', '-14.015', '-17.026', '+100.05', '+222.06', '-33.987', '-1.007']
    }
}

# Load cloud datasets
cloud_datasets = load_datasets_from_cloud()
data_config.update(cloud_datasets)

# ===========================================================
# Upload file
# ===========================================================
st.subheader("📤 Upload your own dataset")
uploaded_file = st.file_uploader("Upload CSV/TXT with one or two lists", type=["csv", "txt"])

def parse_uploaded_file(file):
    content = file.read().decode("utf-8").strip()
    try:
        df = pd.read_csv(io.StringIO(content))
        if df.shape[1] >= 2:
            return df.iloc[:, 0].dropna().astype(float).tolist(), [str(x) for x in df.iloc[:, 1].dropna().tolist()]
        else:
            return df.iloc[:, 0].dropna().astype(float).tolist(), df.iloc[:, 0].dropna().astype(float).tolist()
    except:
        if "#MAIN" in content and "#LIST2" in content:
            main_part = content.split("#MAIN")[1].split("#LIST2")[0]
            list2_part = content.split("#LIST2")[1]
            main_list = [float(x.strip()) for x in main_part.splitlines() if x.strip() and not x.startswith("#")]
            list2_list = [x.strip() for x in list2_part.splitlines() if x.strip() and not x.startswith("#")]
            return main_list, list2_list
        else:
            items = [float(x.strip()) for x in content.replace("\n", ",").split(",") if x.strip()]
            return items, items

if uploaded_file is not None:
    try:
        main_list, list2_list = parse_uploaded_file(uploaded_file)
        name = f"Uploaded_{len(data_config)+1}"
        data_config[name] = {"main": main_list, "list2_raw": list2_list}
        save_dataset_to_cloud(name, main_list, list2_list)
    except Exception as e:
        st.error(f"Error reading file: {e}")

# ===========================================================
# Manual dataset entry
# ===========================================================
st.subheader("✍️ Add New Custom Dataset")
with st.expander("➕ Add New Custom Dataset"):
    custom_name = st.text_input("Dataset name", "")
    main_text = st.text_area("Main list values (comma or newline separated)", "")
    list2_text = st.text_area("List2 modifiers (optional)", "")
    if st.button("Add Custom Dataset"):
        try:
            main_list = [float(x.strip()) for x in main_text.replace("\n", ",").split(",") if x.strip()]
            list2_raw = [x.strip() for x in list2_text.replace("\n", ",").split(",") if x.strip()] if list2_text.strip() else main_list
            if not custom_name:
                custom_name = f"Custom_{len(data_config)+1}"
            data_config[custom_name] = {"main": main_list, "list2_raw": list2_raw}
            save_dataset_to_cloud(custom_name, main_list, list2_raw)
            rerun()
        except Exception as e:
            st.error(f"Error adding dataset: {e}")

# ===========================================================
# Select dataset
# ===========================================================
selected_list_name = st.selectbox("Select dataset to use:", list(data_config.keys()))
selected_data = data_config[selected_list_name]
selected_list = selected_data["main"]
list2_raw = selected_data["list2_raw"]
sum_selected = sum(selected_list)
st.markdown(f"**Using `{selected_list_name}`** with {len(list2_raw)} List2 modifiers.")

# ===========================================================
# Dataset management
# ===========================================================
st.subheader("🛠 Manage saved datasets")
if data_config:
    manage_dataset_name = st.selectbox("Select dataset to manage:", list(data_config.keys()), key="manage_select")
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input(f"Rename '{manage_dataset_name}' to:", "")
        if st.button(f"Rename '{manage_dataset_name}'", key="rename_btn"):
            if new_name:
                rename_dataset(manage_dataset_name, new_name)
                data_config[new_name] = data_config.pop(manage_dataset_name)
                st.success(f"✅ Dataset renamed to '{new_name}'")
                rerun()
    with col2:
        if st.button(f"Delete '{manage_dataset_name}'", key="delete_btn"):
            confirm = st.checkbox(f"Confirm delete '{manage_dataset_name}'?", key="confirm_delete")
            if confirm:
                delete_dataset(manage_dataset_name)
                data_config.pop(manage_dataset_name)
                st.success(f"✅ Dataset '{manage_dataset_name}' deleted")
                rerun()

# ===========================================================
# Parse list2 into + and -
# ===========================================================
list2_add, list2_sub = [], []
for item in list2_raw:
    if isinstance(item, str):
        if item.startswith('+'):
            list2_add.append(float(item[1:]))
        elif item.startswith('-'):
            list2_sub.append(float(item[1:]))
        else:
            try:
                list2_add.append(float(item))
                list2_sub.append(float(item))
            except:
                pass
    else:
        list2_add.append(item)
        list2_sub.append(item)

# ===========================================================
# Calculation toggles
# ===========================================================
st.subheader("⚙️ Choose which combination types to include:")
run_main_only = st.checkbox(f"{selected_list_name} only", True)
run_additions = st.checkbox(f"{selected_list_name} + additions", True)
run_subtractions = st.checkbox(f"{selected_list_name} - subtractions", True)
run_sub_add = st.checkbox(f"{selected_list_name} - sub + add", True)
run_list2_only = st.checkbox("List2 only combinations", False)

# ===========================================================
# Helper functions
# ===========================================================
def within_tolerance(value):
    return abs(value - target) <= tolerance

def add_result(description, value, steps, results):
    if within_tolerance(value):
        error = abs(value - target)
        results.append((len(steps), error, description, value, error))

# ===========================================================
# Run calculations
# ===========================================================
results = []
st.divider()
if st.button("▶️ Run Matching Search"):
    with st.spinner("Running calculations..."):
        progress = st.progress(0)
        current_step = 0
        total_steps = 1

        if run_additions:
            total_steps += sum(len(list(itertools.combinations_with_replacement(list2_add, r))) for r in range(1, 4))
        if run_subtractions:
            total_steps += sum(len(list(itertools.combinations(list2_sub, r))) for r in range(1, 4))
        if run_sub_add:
            total_steps += len(list2_sub) * len(list2_add)
        if run_list2_only:
            all_list2 = list2_add + [-v for v in list2_sub]
            total_steps += sum(len(list(itertools.combinations_with_replacement(all_list2, r))) for r in range(2, 6))

        if run_main_only:
            add_result(f"{selected_list_name} only", sum_selected, [], results)
            progress.progress(0.05)

        if run_additions:
            for r in range(1, 4):
                for combo in itertools.combinations_with_replacement(list2_add, r):
                    value = sum_selected + sum(combo)
                    add_result(f"{selected_list_name} + {combo}", value, combo, results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step/total_steps,1.0))

        if run_subtractions:
            for r in range(1, 4):
                for combo in itertools.combinations(list2_sub, r):
                    value = sum_selected - sum(combo)
                    add_result(f"{selected_list_name} - {combo}", value, combo, results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step/total_steps,1.0))

        if run_sub_add:
            for sub in list2_sub:
                for add in list2_add:
                    value = sum_selected - sub + add
                    add
