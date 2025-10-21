# ============================================================
#  VSPD Legend Plant Extractor  —  Streamlit Cloud Version
# ============================================================

import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io
import re

# -------------------------------
# CONFIGURATION AND THEME
# -------------------------------
st.set_page_config(page_title="VSPD Legend Plant Extractor", page_icon="🌿", layout="wide")
VSPD_GOLD = "#d59b3b"

# Logo and title
try:
    st.image("vspd_logo.png", width=160)
except Exception:
    st.markdown(f"<h2 style='color:{VSPD_GOLD}'>VSPD Legend Plant Extractor</h2>", unsafe_allow_html=True)

st.markdown(
    f"""
    <h1 style='text-align:center;color:{VSPD_GOLD};'>VSPD Legend Plant Extractor</h1>
    <hr style='border:1px solid {VSPD_GOLD};'>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# USER INPUTS
# -------------------------------
project_name = st.text_input("Enter Project Name:", placeholder="e.g. Desert Vista HOA")
uploaded_files = st.file_uploader(
    "Upload plant legend (PDF, JPG, or PNG):",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

# -------------------------------
# HORTICULTURAL CLASSIFICATION TABLE
# -------------------------------
CATEGORY_LOOKUP = {
    "Tree": [
        "quercus", "prosopis", "acacia", "parkinsonia", "cercidium",
        "fraxinus", "olea", "pistacia", "populus", "pinus", "chilopsis"
    ],
    "Accent": [
        "agave", "yucca", "hesperaloe", "dasylirion", "aloe",
        "cactus", "echinocactus", "ferocactus", "opuntia", "fouquieria",
        "chamaerops", "phoenix", "washingtonia"
    ],
    "Shrub": [
        "leucophyllum", "calliandra", "tecoma", "esperanza",
        "caesalpinia", "melampodium", "buxus", "nerium"
    ],
    "Groundcover": [
        "lantana", "myoporum", "dalea", "dymondia", "carissa",
        "trachelospermum", "verbena", "gazania"
    ],
}

# -------------------------------
# OCR EXTRACTION FUNCTION
# -------------------------------
def extract_text(upload):
    """Extracts raw text from uploaded PDF or image file."""
    text = ""
    file_bytes = upload.read()
    if upload.name.lower().endswith(".pdf"):
        images = convert_from_bytes(file_bytes)
        for img in images:
            text += pytesseract.image_to_string(img)
    else:
        image = Image.open(io.BytesIO(file_bytes))
        text += pytesseract.image_to_string(image)
    return text

# -------------------------------
# CATEGORY DETERMINATION
# -------------------------------
def determine_category(name, fallback="Accent"):
    """Determines the correct plant category using lookup table."""
    lname = name.lower()
    for cat, genus_list in CATEGORY_LOOKUP.items():
        if any(genus in lname for genus in genus_list):
            return cat
    return fallback

# -------------------------------
# TEXT PARSING FUNCTION
# -------------------------------
def parse_plant_text(raw_text):
    """Extracts quantity, names, sizes, and dimensions from OCR text."""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    data = []
    category = None

    for line in lines:
        # Detect section headings
        if re.search(r"trees?|accents?|shrubs?|groundcovers?", line, re.IGNORECASE):
            if "tree" in line.lower():
                category = "Tree"
            elif "accent" in line.lower():
                category = "Accent"
            elif "shrub" in line.lower():
                category = "Shrub"
            elif "groundcover" in line.lower():
                category = "Groundcover"
            continue

        # Match lines starting with a quantity
        match = re.match(r"^(\d+)\s+(.*)$", line)
        if not match:
            continue

        qty = int(match.group(1))
        desc = match.group(2).strip()

        # Extract height × width
        dim_match = re.search(r"(\d+['′]?)\s*[×x]\s*(\d+['′]?)", desc)
        dims = f"{dim_match.group(1)} × {dim_match.group(2)}" if dim_match else ""

        # Extract size (e.g., 15 Gal, 24" Box, Bare Root)
        size_match = re.search(r"(\d+\s*(?:[Gg]al|[Bb]ox|[Ii][Nn]\.?|[Ff]t\.?|BTH|Bare Root).*)", desc)
        size = size_match.group(1).strip() if size_match else ""

        # Clean name fields
        name = desc.replace(size, "").replace(dims, "").strip()
        name = re.sub(r"\s{2,}", " ", name)
        name = name.replace("-", "—").strip()

        # Determine category from name if missing
        final_cat = category or determine_category(name)

        data.append([final_cat, qty, name, size, dims])

    df = pd.DataFrame(
        data, columns=["Category", "Quantity", "Botanical / Common Name", "Size", "Height × Width"]
    )

    # Combine duplicates
    df = df.groupby(["Category", "Botanical / Common Name", "Size", "Height × Width"], as_index=False)["Quantity"].sum()

    # Sort by category + size
    cat_order = {"Tree": 1, "Accent": 2, "Shrub": 3, "Groundcover": 4}
    size_order = {"Box": 1, "Gal": 2, "Cal": 3, "": 4}
    df["CatOrder"] = df["Category"].map(cat_order)
    df["SizeOrder"] = df["Size"].apply(lambda s: next((v for k, v in size_order.items() if k.lower() in s.lower()), 5))
    df = df.sort_values(by=["CatOrder", "SizeOrder"]).drop(columns=["CatOrder", "SizeOrder"])
    return df

# -------------------------------
# MAIN PROCESSING PIPELINE
# -------------------------------
if uploaded_files and project_name:
    with st.spinner("Extracting and processing plant data... please wait 🌿"):
        all_text = ""
        for file in uploaded_files:
            all_text += extract_text(file)
        df = parse_plant_text(all_text)

    # Add project header row for Excel
    header_df = pd.DataFrame(
        {"Category": [f"Project: {project_name} — Generated by VSPD Legend Plant Extractor (VSPD)"]}
    )
    final_df = pd.concat([header_df, df], ignore_index=True)

    # Preview Table
    st.markdown(f"<h3 style='color:{VSPD_GOLD};'>Extracted Plant Schedule Preview</h3>", unsafe_allow_html=True)
    st.markdown(f"<div style='border:2px solid {VSPD_GOLD};padding:10px;border-radius:10px;'>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Export Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        final_df.to_excel(writer, index=False, sheet_name="Plant Schedule")
    output.seek(0)

    # Download button
    st.download_button(
        label="📥 Download Plant Schedule",
        data=output,
        file_name=f"Plant_Schedule_{project_name.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.balloons()

# -------------------------------
# FOOTER
# -------------------------------
st.markdown(f"<hr style='border:1px solid {VSPD_GOLD};'>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:{VSPD_GOLD};'>Powered by VSPD</p>", unsafe_allow_html=True)
