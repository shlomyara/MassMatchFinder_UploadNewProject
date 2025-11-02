
import streamlit as st
import itertools
import pandas as pd
import io
import time

# --- Title ---
st.title("🧮 MassMatchFinder            UploadNewProjects")
st.markdown("""
Enter a target mass and tolerance, choose or create a dataset,  
and select which combinations to run.  
You can upload, type, or select from built-in lists.
""")

# --- Input ---
target = st.number_input("🎯 Target number to match", format="%.5f")
tolerance = st.number_input("🎯 Acceptable error/tolerance (e.g., 0.1)", value=0.1, format="%.5f")

# --- Data Configuration (Base Lists) ---
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
# 📤 UPLOAD FILE
# ===========================================================
st.subheader("📤 Upload your own dataset (optional)")
uploaded_file = st.file_uploader("Upload a .csv or .txt file with one or two lists", type=["csv", "txt"])

def parse_uploaded_file(file):
    """Parse uploaded file into main_list and list2_list."""
    content = file.read().decode("utf-8").strip()

    # Case 1: CSV
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

    # Case 2: TXT with #MAIN / #LIST2 sections
    if "#MAIN" in content and "#LIST2" in content:
        main_part = content.split("#MAIN")[1].split("#LIST2")[0]
        list2_part = content.split("#LIST2")[1]
        main_list = [float(x.strip()) for x in main_part.splitlines() if x.strip() and not x.startswith("#")]
        list2_list = [x.strip() for x in list2_part.splitlines() if x.strip() and not x.startswith("#")]
        return main_list, list2_list

    # Case 3: simple numeric list
    try:
        items = [float(x.strip()) for x in content.replace("\n", ",").split(",") if x.strip()]
        return items, items
    except Exception:
        raise ValueError("Could not parse file format.")

if uploaded_file is not None:
    try:
        main_list, list2_list = parse_uploaded_file(uploaded_file)
        data_config["User_Uploaded"] = {"main": main_list, "list2_raw": list2_list}
        st.success(f"✅ Uploaded list added! Main: {len(main_list)}, List2: {len(list2_list)}")
    except Exception as e:
        st.error(f"Error reading file: {e}")

# ===========================================================
# ✍️ MANUAL LIST ENTRY
# ===========================================================
st.subheader("✍️ Or manually add a new dataset")

with st.expander("➕ Add New Custom Dataset"):
    custom_name = st.text_input("Dataset name (e.g., MyExperiment1)")
    main_text = st.text_area("Main list values (comma or newline separated)", "")
    list2_text = st.text_area("List2 modifiers (optional — use + or - for signs)", "")

    if st.button("Add Custom Dataset"):
        try:
            main_list = [float(x.strip()) for x in main_text.replace("\n", ",").split(",") if x.strip()]
            if list2_text.strip():
                list2_raw = [x.strip() for x in list2_text.replace("\n", ",").split(",") if x.strip()]
            else:
                list2_raw = main_list  # fallback
            if not custom_name:
                custom_name = f"Custom_{len(data_config) + 1}"
            data_config[custom_name] = {"main": main_list, "list2_raw": list2_raw}
            st.success(f"✅ Custom dataset '{custom_name}' added with {len(main_list)} main values.")
        except Exception as e:
            st.error(f"Error adding dataset: {e}")

# ===========================================================
# 📂 SELECT DATASET
# ===========================================================
selected_list_name = st.selectbox("Select dataset to use:", list(data_config.keys()))
selected_data = data_config[selected_list_name]
selected_list = selected_data["main"]
sum_selected = sum(selected_list)
list2_raw = selected_data["list2_raw"]

st.markdown(f"**Using `{selected_list_name}`** with {len(list2_raw)} List2 modifiers.")

# ===========================================================
# 🔧 Parse list2 into + and - groups
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
# ⚙️ Calculation Toggles
# ===========================================================
st.subheader("⚙️ Choose which combination types to include:")
run_main_only = st.checkbox(f"{selected_list_name} only", True)
run_additions = st.checkbox(f"{selected_list_name} + additions", True)
run_subtractions = st.checkbox(f"{selected_list_name} - subtractions", True)
run_sub_add = st.checkbox(f"{selected_list_name} - sub + add", True)
run_list2_only = st.checkbox("List2 only combinations", False)

# ===========================================================
# 🧠 Helper Functions
# ===========================================================
def within_tolerance(value):
    return abs(value - target) <= tolerance

def add_result(description, value, steps, results):
    if within_tolerance(value):
        error = abs(value - target)
        results.append((len(steps), error, description, value, error))

# ===========================================================
# ▶️ Run Calculations
# ===========================================================
results = []

st.divider()
run_button = st.button("▶️ Run Matching Search")

if run_button:
    with st.spinner("Running calculations... please wait ⏳"):
        progress = st.progress(0)
        total_steps = 1
        current_step = 0

        # Estimate total steps
        if run_additions:
            total_steps += sum(len(list(itertools.combinations_with_replacement(list2_add, r))) for r in range(1, 4))
        if run_subtractions:
            total_steps += sum(len(list(itertools.combinations(list2_sub, r))) for r in range(1, 4))
        if run_sub_add:
            total_steps += len(list2_sub) * len(list2_add)
        if run_list2_only:
            all_list2 = list2_add + [-v for v in list2_sub]
            total_steps += sum(len(list(itertools.combinations_with_replacement(all_list2, r))) for r in range(2, 6))

        # Base list only
        if run_main_only:
            add_result(f"{selected_list_name} only", sum_selected, [], results)
            progress.progress(0.05)

        # Additions
        if run_additions:
            for r in range(1, 4):
                for combo in itertools.combinations_with_replacement(list2_add, r):
                    value = sum_selected + sum(combo)
                    add_result(f"{selected_list_name} + {combo}", value, combo, results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step / total_steps, 1.0))

        # Subtractions
        if run_subtractions:
            for r in range(1, 4):
                for combo in itertools.combinations(list2_sub, r):
                    value = sum_selected - sum(combo)
                    add_result(f"{selected_list_name} - {combo}", value, combo, results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step / total_steps, 1.0))

        # Sub + Add
        if run_sub_add:
            for sub in list2_sub:
                for add in list2_add:
                    value = sum_selected - sub + add
                    add_result(f"{selected_list_name} - ({sub},) + ({add},)", value, [sub, add], results)
                    current_step += 1
                    if current_step % 100 == 0:
                        progress.progress(min(current_step / total_steps, 1.0))

        # List2 only
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

    # --- Results display ---
    if results:
        st.success(f"✅ Found {len(results)} matches within ±{tolerance:.5f}")
        for _, _, desc, val, error in sorted(results, key=lambda x: (x[0], x[1])):
            st.write(f"🔹 `{desc}` = **{val:.5f}** (error: {error:.5f})")
    else:
        st.warning("No matches found with current settings.")
