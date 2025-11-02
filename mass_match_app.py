import streamlit as st
import itertools
import pandas as pd
import io
import time
from supabase import create_client, Client
from streamlit.runtime.scriptrunner import RerunException, get_script_run_ctx

# ===============================
# 🔄 Helper to trigger Streamlit rerun
# ===============================
def rerun():
    raise RerunException(get_script_run_ctx())

# ===============================
# Supabase client
# ===============================
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# App Title
# ===============================
st.title("🧮 MassMatchFinder with Cloud Datasets")
st.markdown("""
Enter a target mass and tolerance, choose or create a dataset,  
and select which combinations to run.  
You can upload, type, or select from built-in or saved lists.
""")

# ===============================
# Inputs
# ===============================
target = st.number_input("🎯 Target number to match", format="%.5f")
tolerance = st.number_input("🎯 Acceptable error/tolerance (e.g., 0.1)", value=0.1, format="%.5f")

# ===============================
# Base Data Config
# ===============================
data_config = {
    "I_Tide_Linear": {
        "main": [174.058, 197.084, 127.063, 147.055, 87.055, 200.095, 170.113, 207.113, 114.042, 114.042, 101.047, 129.042, 131.040],
        "list2_raw": [174.058, 173.051, 197.084, 127.063, 147.055, 87.055, 200.095, 170.113, 207.113, 114.042, 101.047, 129.042, 130.032, 131.040, 42.010, 0.984, 2.015, '+71.037', '+242.109', '+56.06', '-15.977', '+252.082', '+230.11', '-18.010', '-14.015', '-17.026', '+100.05', '+222.06', '-33.987', '-1.007', '+1896.83']
    },
    "I_Tide_Syclic": {
        "main": [173.051, 197.084, 127.063, 147.055, 87.055, 200.095, 170.113, 207.113, 114.042, 114.042, 101.047, 129.042, 130.032],
        "list2_raw": [87.055, 114.042, 130.032, '+71.037', '+56.06', '-15.977', '+1896.83']
    }
}

# ===============================
# Supabase Dataset Helpers
# ===============================
def load_datasets_from_cloud():
    try:
        response = supabase.table("datasets").select("*").execute()
        if response.data:
            for row in response.data:
                name = row.get("name")
                main = row.get("main") or []
                list2 = row.get("list2") or main
                data_config[name] = {"main": main, "list2_raw": list2}
    except Exception as e:
        st.warning(f"Could not load datasets from cloud: {e}")

def save_dataset(name, main_list, list2_list):
    try:
        supabase.table("datasets").upsert({"name": name, "main": main_list, "list2": list2_list}).execute()
    except Exception as e:
        st.error(f"❌ Failed to save dataset to cloud: {e}")

def delete_dataset(name):
    try:
        supabase.table("datasets").delete().eq("name", name).execute()
    except Exception as e:
        st.error(f"❌ Failed to delete dataset: {e}")

def rename_dataset(old_name, new_name):
    try:
        supabase.table("datasets").update({"name": new_name}).eq("name", old_name).execute()
    except Exception as e:
        st.error(f"❌ Failed to rename dataset: {e}")

# ===============================
# Load Cloud Datasets
# ===============================
load_datasets_from_cloud()

# ===============================
# Upload File
# ===============================
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
        custom_name = "User_Uploaded"
        data_config[custom_name] = {"main": main_list, "list2_raw": list2_list}
        save_dataset(custom_name, main_list, list2_list)
        st.success(f"✅ Uploaded list added as '{custom_name}'! Main: {len(main_list)}, List2: {len(list2_list)}")
        rerun()
    except Exception as e:
        st.error(f"Error reading file: {e}")

# ===============================
# Manual Dataset Entry
# ===============================
st.subheader("✍️ Add a new dataset manually")
with st.expander("➕ Add New Custom Dataset"):
    custom_name = st.text_input("Dataset name (e.g., MyExperiment1)")
    main_text = st.text_area("Main list values (comma or newline separated)", "")
    list2_text = st.text_area("List2 modifiers (optional — use + or - for signs)", "")

    if st.button("Add Custom Dataset"):
        try:
            main_list = [float(x.strip()) for x in main_text.replace("\n", ",").split(",") if x.strip()]
            list2_list = [x.strip() for x in list2_text.replace("\n", ",").split(",") if x.strip()] if list2_text.strip() else main_list
            if not custom_name:
                custom_name = f"Custom_{len(data_config)+1}"
            data_config[custom_name] = {"main": main_list, "list2_raw": list2_list}
            save_dataset(custom_name, main_list, list2_list)
            st.success(f"✅ Custom dataset '{custom_name}' added and saved to cloud.")
            rerun()
        except Exception as e:
            st.error(f"Error adding dataset: {e}")

# ===============================
# Dataset Selection
# ===============================
dataset_names = list(data_config.keys())
selected_list_name = st.selectbox("Select dataset to use:", dataset_names)
selected_data = data_config[selected_list_name]
selected_list = selected_data["main"]
sum_selected = sum(selected_list)
list2_raw = selected_data["list2_raw"]

st.markdown(f"**Using `{selected_list_name}`** with {len(list2_raw)} List2 modifiers.")

# ===============================
# Parse list2 into + and - groups
# ===============================
list2_add, list2_sub = [], []
for item in list2_raw:
    if isinstance(item, str):
        if item.startswith('+'):
            list2_add.append(float(item[1:]))
        elif item.startswith('-'):
            list2_sub.append(float(item[1:]))
        else:
            try:
                val = float(item)
                list2_add.append(val)
                list2_sub.append(val)
            except:
                pass
    else:
        list2_add.append(item)
        list2_sub.append(item)

# ===============================
# Combination Toggles
# ===============================
st.subheader("⚙️ Choose which combination types to include:")
run_main_only = st.checkbox(f"{selected_list_name} only", True)
run_additions = st.checkbox(f"{selected_list_name} + additions", True)
run_subtractions = st.checkbox(f"{selected_list_name} - subtractions", True)
run_sub_add = st.checkbox(f"{selected_list_name} - sub + add", True)
run_list2_only = st.checkbox("List2 only combinations", False)

# ===============================
# Calculation Helpers
# ===============================
def within_tolerance(value):
    return abs(value - target) <= tolerance

def add_result(description, value, steps, results):
    if within_tolerance(value):
        error = abs(value - target)
        results.append((len(steps), error, description, value, error))

# ===============================
# Run Calculations
# ===============================
results = []

st.divider()
run_button = st.button("▶️ Run Matching Search")

if run_button:
    with st.spinner("Running calculations... please wait ⏳"):
        progress = st.progress(0)
        total_steps = 1
        current_step = 0

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
                        progress.progress(min(current_step / total_steps, 1.0))

        if run_subtractions:
            for r in range(1, 4):
                for combo in itertools.combinations(list2_sub, r):
                    value = sum_selected - sum(combo)
                    add_result(f"{selected_list_name} - {combo}", value, combo, results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step / total_steps, 1.0))

        if run_sub_add:
            for sub in list2_sub:
                for add in list2_add:
                    value = sum_selected - sub + add
                    add_result(f"{selected_list_name} - ({sub},) + ({add},)", value, [sub, add], results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step / total_steps, 1.0))

        if run_list2_only:
            all_list2 = list2_add + [-v for v in list2_sub]
            for r in range(2, 6):
                for combo in itertools.combinations_with_replacement(all_list2, r):
                    value = sum(combo)
                    add_result(f"List2 only {combo}", value, combo, results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step / total_steps, 1.0))

        progress.progress(1.0)

    if results:
        st.success(f"✅ Found {len(results)} matches within ±{tolerance:.5f}")
        for _, _, desc, val, error in sorted(results, key=lambda x: (x[0], x[1])):
            st.write(f"🔹 `{desc}` = **{val:.5f}** (error: {error:.5f})")
    else:
        st.warning("No matches found with current settings.")
