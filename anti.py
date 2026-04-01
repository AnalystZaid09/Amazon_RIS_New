import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="RIS Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0068c9;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper functions
def clean_text(x):
    if pd.isna(x):
        return ""
    # Remove all non-alphanumeric characters for robust matching
    return re.sub(r"[^a-z0-9]", "", str(x).lower())

def normalize_sku(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "")

def normalize_shipping_state(shipping_state, fc_state, state_rules):
    if pd.isna(fc_state):
        return shipping_state
        
    ship = clean_text(shipping_state)
    target_fc_clean = clean_text(fc_state)
    
    # Iterate through all rules to find a match for the FC state (case-insensitive)
    for rule_fc, variants in state_rules.items():
        if target_fc_clean == clean_text(rule_fc):
            # Check if the shipping state matches any of the allowed variants for this FC
            for variant in variants:
                if ship == clean_text(variant):
                    return rule_fc
    
    return shipping_state

def find_column(df, patterns):
    """
    Finds a column in a dataframe based on a list of possible name patterns (lowercase, no spaces).
    Returns the actual column name or None if not found.
    """
    if df is None:
        return None
    
    # Normalize patterns for matching
    norm_patterns = [p.lower().replace("_", "").replace(" ", "").replace("-", "") for p in patterns]
    
    for col in df.columns:
        col_norm = str(col).lower().replace("_", "").replace(" ", "").replace("-", "")
        if col_norm in norm_patterns:
            return col
    return None

def to_excel(df):
    output = BytesIO()
    # Convert object columns to string to avoid PyArrow type conversion errors
    df_copy = df.copy()
    for col in df_copy.columns:
        if df_copy[col].dtype == 'object':
            df_copy[col] = df_copy[col].astype(str)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_copy.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# State rules for normalization
STATE_RULES = {
    "Delhi": ["delhi", "dl", "newdelhi", "nctdelhi", "haryana", "harayana", "hr"],
    "Haryana": ["haryana", "harayana", "hr", "delhi", "dl", "newdelhi", "nctdelhi", "chandigarh", "chd"],
    "Karnataka": ["karnataka", "ka", "bangalore", "bengaluru", "karnaraka", "karnaka"],
    "Madhya Pradesh": ["madhyapradesh", "mp", "indore", "bhopal"],
    "Maharashtra": ["maharashtra", "mh", "dadra", "nagarhaveli", "dadra&nagarhaveli", "dnh", "maharastra"],
    "Uttar Pradesh": ["uttarpradesh", "up"],
    "Telangana": ["telangana", "tg", "hyderabad", "telanagana", "telengana", "telagana", "hyderabadtelangana"],
    "West Bengal": ["westbengal", "wb", "kolkata"],
    "Punjab": ["punjab", "pb", "chandigarh", "chd"],
    "Kerala": ["kerala", "kl", "trivandrum", "thiruvananthapuram"],
    "Orissa": ["orissa", "odisha", "or", "bhubaneswar"],
    "Tamil Nadu": ["tamilnadu", "tn", "chennai"],
    "Gujarat": ["gujarat", "gj", "ahmedabad", "surat"],
    "Rajasthan": ["rajasthan", "rj", "jaipur"],
    "Andhra Pradesh": ["andhrapradesh", "ap", "visakhapatnam", "vizag"],
    "Bihar": ["bihar", "br", "patna"],
}

# Title
st.title("📊 RIS Analysis Dashboard")
st.markdown("---")

# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'all_results' not in st.session_state:
    st.session_state.all_results = {}
if 'manager_data' not in st.session_state:
    st.session_state.manager_data = None
if 'manager_results' not in st.session_state:
    st.session_state.manager_results = {}
if 'samriddhi_data' not in st.session_state:
    st.session_state.samriddhi_data = None
if 'samriddhi_results' not in st.session_state:
    st.session_state.samriddhi_results = {}

# Sidebar for file upload
with st.sidebar:
    st.header("� Select Manager Type")
    manager_type = st.selectbox(
        "Choose Manager Type",
        ["Portal", "Manager", "RIS Samriddhi"],
        index=0
    )
    
    st.markdown("---")
    
    if manager_type == "Portal":
        st.header("�📁 Upload Files")
        st.markdown("Upload all three required files:")
        
        ris_file = st.file_uploader("Upload RIS.csv", type=['csv'], key='ris')
        state_fc_file = st.file_uploader("Upload State FC Cluster.xlsx", type=['xlsx', 'xls'], key='statefc')
        purchase_file = st.file_uploader("Upload PM.xlsx", type=['xlsx', 'xls'], key='purchase')
        
        st.markdown("---")
        
        # Clear cache button
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.session_state.processed_data = None
            st.session_state.all_results = {}
            st.session_state.manager_data = None
            st.session_state.manager_results = {}
            st.rerun()
        
        if st.button("🔄 Process Data", use_container_width=True):
            if ris_file and state_fc_file and purchase_file:
                with st.spinner("Processing data..."):
                    try:
                        # Read files with robust encoding and strip whitespace from headers
                        ris_df = pd.read_csv(ris_file, encoding='utf-8-sig')
                        ris_df.columns = ris_df.columns.str.strip()
                        
                        state_fc_df = pd.read_excel(state_fc_file, sheet_name="Sheet2")
                        state_fc_df.columns = state_fc_df.columns.str.strip()
                        
                        purchase_df = pd.read_excel(purchase_file)
                        purchase_df.columns = purchase_df.columns.str.strip()
                        
                        # Rename columns in state_fc_df
                        state_fc_df = state_fc_df.rename(columns={
                            state_fc_df.columns[0]: "FC",
                            state_fc_df.columns[1]: "FC State",
                            state_fc_df.columns[2]: "FC Cluster",
                            state_fc_df.columns[3]: "FC State Cluster"
                        })
                        
                        # Create mappings with stripped string keys for robust matching
                        state_fc_df["FC"] = state_fc_df["FC"].astype(str).str.strip()
                        ris_df["FC"] = ris_df["FC"].astype(str).str.strip()
                        
                        # Robust Column Mapping for Portal
                        portal_col_map = {}
                        for col in ris_df.columns:
                            c_clean = col.lower().replace(" ", "").replace("-", "").replace("_", "")
                            if c_clean == "shippingstate": portal_col_map[col] = "Shipping State"
                            if c_clean in ["shippedquantity", "shippedqty", "qty"]: portal_col_map[col] = "Shipped Quantity"
                            if c_clean in ["merchantsku", "sku"]: portal_col_map[col] = "Merchant SKU"
                            if c_clean == "fc": portal_col_map[col] = "FC"
                        ris_df = ris_df.rename(columns=portal_col_map)
                        
                        fc_state_map = dict(zip(state_fc_df["FC"], state_fc_df["FC State"]))
                        fc_cluster_map = dict(zip(state_fc_df["FC"], state_fc_df["FC Cluster"]))
                        fc_state_cluster_map = dict(zip(state_fc_df["FC"], state_fc_df["FC State Cluster"]))
                        
                        # Map FC data to RIS
                        ris_df["FC State"] = ris_df["FC"].map(fc_state_map)
                        ris_df["FC Cluster"] = ris_df["FC"].map(fc_cluster_map)
                        ris_df["FC State Cluster"] = ris_df["FC"].map(fc_state_cluster_map)
                        
                        # Normalize SKUs
                        purchase_df["Amazon Sku Name"] = purchase_df["Amazon Sku Name"].apply(normalize_sku)
                        ris_df["Merchant SKU"] = ris_df["Merchant SKU"].apply(normalize_sku)
                        
                        # Create product mappings
                        asin_map = dict(zip(purchase_df["Amazon Sku Name"], purchase_df["ASIN"]))
                        vendor_sku_map = dict(zip(purchase_df["Amazon Sku Name"], purchase_df["Vendor SKU Codes"]))
                        brand_manager_map = dict(zip(purchase_df["Amazon Sku Name"], purchase_df["Brand Manager"]))
                        brand_map = dict(zip(purchase_df["Amazon Sku Name"], purchase_df["Brand"]))
                        product_name_map = dict(zip(purchase_df["Amazon Sku Name"], purchase_df["Product Name"]))
                        
                        # Map product data to RIS
                        ris_df["ASIN"] = ris_df["Merchant SKU"].map(asin_map)
                        ris_df["Vendor SKU"] = ris_df["Merchant SKU"].map(vendor_sku_map)
                        ris_df["Brand"] = ris_df["Merchant SKU"].map(brand_map)
                        ris_df["Brand Manager"] = ris_df["Merchant SKU"].map(brand_manager_map)
                        ris_df["Product Name"] = ris_df["Merchant SKU"].map(product_name_map)
                        
                        # Normalize shipping state
                        ris_df["Shipping State Corrected"] = ris_df.apply(
                            lambda x: normalize_shipping_state(x["Shipping State"], x["FC State"], STATE_RULES),
                            axis=1
                        )
                        
                        # Calculate RIS Status
                        ris_df["RIS Status"] = np.where(
                            ris_df["Shipping State Corrected"].str.upper().str.strip() == 
                            ris_df["FC State"].str.upper().str.strip(),
                            "RIS",
                            "Non RIS"
                        )
                        
                        # Convert all object columns to string to avoid PyArrow serialization errors
                        for col in ris_df.columns:
                            if ris_df[col].dtype == 'object':
                                ris_df[col] = ris_df[col].astype(str)
                        
                        # Store processed data
                        st.session_state.processed_data = ris_df
                        
                        # Generate all pivots
                        results = {}
                        
                        # 1. Brand-wise RIS
                        brand_wise = pd.pivot_table(
                            ris_df, index="Brand", columns="RIS Status",
                            values="Shipped Quantity", aggfunc="sum", fill_value=0
                        ).reset_index()
                        # Ensure columns exist
                        if "RIS" not in brand_wise.columns:
                            brand_wise["RIS"] = 0
                        if "Non RIS" not in brand_wise.columns:
                            brand_wise["Non RIS"] = 0
                        brand_wise["Grand Total"] = brand_wise["RIS"] + brand_wise["Non RIS"]
                        brand_wise["RIS %"] = ((brand_wise["RIS"] / brand_wise["Grand Total"]) * 100).round(2)
                        brand_wise["Non RIS %"] = ((brand_wise["Non RIS"] / brand_wise["Grand Total"]) * 100).round(2)
                        # Add Grand Total row
                        grand_total_row = pd.DataFrame({
                            "Brand": ["Grand Total"],
                            "RIS": [brand_wise["RIS"].sum()],
                            "Non RIS": [brand_wise["Non RIS"].sum()],
                            "Grand Total": [brand_wise["Grand Total"].sum()],
                            "RIS %": [round((brand_wise["RIS"].sum() / brand_wise["Grand Total"].sum()) * 100, 2)],
                            "Non RIS %": [round((brand_wise["Non RIS"].sum() / brand_wise["Grand Total"].sum()) * 100, 2)]
                        })
                        brand_wise = pd.concat([brand_wise, grand_total_row], ignore_index=True)
                        results['brand_wise'] = brand_wise
                        
                        # 2. ASIN-wise RIS
                        asin_wise = pd.pivot_table(
                            ris_df, index=["ASIN", "Brand"], columns="RIS Status",
                            values="Shipped Quantity", aggfunc="sum", fill_value=0
                        ).reset_index()
                        if "RIS" not in asin_wise.columns:
                            asin_wise["RIS"] = 0
                        if "Non RIS" not in asin_wise.columns:
                            asin_wise["Non RIS"] = 0
                        asin_wise["Grand Total"] = asin_wise["RIS"] + asin_wise["Non RIS"]
                        asin_wise["RIS %"] = ((asin_wise["RIS"] / asin_wise["Grand Total"]) * 100).round(2)
                        asin_wise["Non RIS %"] = ((asin_wise["Non RIS"] / asin_wise["Grand Total"]) * 100).round(2)
                        # Add Grand Total row
                        grand_total_row = pd.DataFrame({
                            "ASIN": ["Grand Total"],
                            "Brand": [""],
                            "RIS": [asin_wise["RIS"].sum()],
                            "Non RIS": [asin_wise["Non RIS"].sum()],
                            "Grand Total": [asin_wise["Grand Total"].sum()],
                            "RIS %": [round((asin_wise["RIS"].sum() / asin_wise["Grand Total"].sum()) * 100, 2)],
                            "Non RIS %": [round((asin_wise["Non RIS"].sum() / asin_wise["Grand Total"].sum()) * 100, 2)]
                        })
                        asin_wise = pd.concat([asin_wise, grand_total_row], ignore_index=True)
                        results['asin_wise'] = asin_wise
                        
                        # 3. Cluster-wise RIS
                        cluster_wise = pd.pivot_table(
                            ris_df, index="FC Cluster", columns="RIS Status",
                            values="Shipped Quantity", aggfunc="sum", fill_value=0
                        ).reset_index()
                        if "RIS" not in cluster_wise.columns:
                            cluster_wise["RIS"] = 0
                        if "Non RIS" not in cluster_wise.columns:
                            cluster_wise["Non RIS"] = 0
                        cluster_wise["Grand Total"] = cluster_wise["RIS"] + cluster_wise["Non RIS"]
                        cluster_wise["RIS %"] = ((cluster_wise["RIS"] / cluster_wise["Grand Total"]) * 100).round(2)
                        cluster_wise["Non RIS %"] = ((cluster_wise["Non RIS"] / cluster_wise["Grand Total"]) * 100).round(2)
                        # Add Grand Total row
                        grand_total_row = pd.DataFrame({
                            "FC Cluster": ["Grand Total"],
                            "RIS": [cluster_wise["RIS"].sum()],
                            "Non RIS": [cluster_wise["Non RIS"].sum()],
                            "Grand Total": [cluster_wise["Grand Total"].sum()],
                            "RIS %": [round((cluster_wise["RIS"].sum() / cluster_wise["Grand Total"].sum()) * 100, 2)],
                            "Non RIS %": [round((cluster_wise["Non RIS"].sum() / cluster_wise["Grand Total"].sum()) * 100, 2)]
                        })
                        cluster_wise = pd.concat([cluster_wise, grand_total_row], ignore_index=True)
                        results['cluster_wise'] = cluster_wise
                        
                        # 4. Cluster-Brand pivot WITH GRAND TOTAL
                        cluster_brand = pd.pivot_table(
                            ris_df, index=["FC Cluster", "Brand"], columns="RIS Status",
                            values="Shipped Quantity", aggfunc="sum", fill_value=0
                        ).reset_index()
                        if "RIS" not in cluster_brand.columns:
                            cluster_brand["RIS"] = 0
                        if "Non RIS" not in cluster_brand.columns:
                            cluster_brand["Non RIS"] = 0
                        # Ensure numeric types
                        cluster_brand["RIS"] = pd.to_numeric(cluster_brand["RIS"], errors='coerce').fillna(0)
                        cluster_brand["Non RIS"] = pd.to_numeric(cluster_brand["Non RIS"], errors='coerce').fillna(0)
                        cluster_brand["Grand Total"] = cluster_brand["RIS"] + cluster_brand["Non RIS"]
                        cluster_brand["RIS %"] = ((cluster_brand["RIS"] / cluster_brand["Grand Total"]) * 100).round(2).fillna(0)
                        cluster_brand["Non RIS %"] = ((cluster_brand["Non RIS"] / cluster_brand["Grand Total"]) * 100).round(2).fillna(0)
                        
                        # Calculate Grand Total from original data
                        total_ris = float(cluster_brand["RIS"].sum())
                        total_non_ris = float(cluster_brand["Non RIS"].sum())
                        total_grand = total_ris + total_non_ris
                        
                        # Add Grand Total row
                        grand_total_row = pd.DataFrame({
                            "FC Cluster": ["Grand Total"],
                            "Brand": [""],
                            "RIS": [total_ris],
                            "Non RIS": [total_non_ris],
                            "Grand Total": [total_grand],
                            "RIS %": [round((total_ris / total_grand) * 100, 2) if total_grand > 0 else 0],
                            "Non RIS %": [round((total_non_ris / total_grand) * 100, 2) if total_grand > 0 else 0]
                        })
                        cluster_brand = pd.concat([cluster_brand, grand_total_row], ignore_index=True)
                        results['cluster_brand'] = cluster_brand
                        
                        # 5. State Cluster-wise RIS
                        state_cluster = pd.pivot_table(
                            ris_df, index="FC State Cluster", columns="RIS Status",
                            values="Shipped Quantity", aggfunc="sum", fill_value=0
                        ).reset_index()
                        if "RIS" not in state_cluster.columns:
                            state_cluster["RIS"] = 0
                        if "Non RIS" not in state_cluster.columns:
                            state_cluster["Non RIS"] = 0
                        state_cluster["Grand Total"] = state_cluster["RIS"] + state_cluster["Non RIS"]
                        state_cluster["RIS %"] = ((state_cluster["RIS"] / state_cluster["Grand Total"]) * 100).round(2)
                        state_cluster["Non RIS %"] = ((state_cluster["Non RIS"] / state_cluster["Grand Total"]) * 100).round(2)
                        # Add Grand Total row
                        grand_total_row = pd.DataFrame({
                            "FC State Cluster": ["Grand Total"],
                            "RIS": [state_cluster["RIS"].sum()],
                            "Non RIS": [state_cluster["Non RIS"].sum()],
                            "Grand Total": [state_cluster["Grand Total"].sum()],
                            "RIS %": [round((state_cluster["RIS"].sum() / state_cluster["Grand Total"].sum()) * 100, 2)],
                            "Non RIS %": [round((state_cluster["Non RIS"].sum() / state_cluster["Grand Total"].sum()) * 100, 2)]
                        })
                        state_cluster = pd.concat([state_cluster, grand_total_row], ignore_index=True)
                        results['state_cluster'] = state_cluster
                        
                        # 6. State-FC pivot WITH GRAND TOTAL
                        state_fc = pd.pivot_table(
                            ris_df, index=["FC State Cluster", "FC Cluster"], columns="RIS Status",
                            values="Shipped Quantity", aggfunc="sum", fill_value=0
                        ).reset_index()
                        if "RIS" not in state_fc.columns:
                            state_fc["RIS"] = 0
                        if "Non RIS" not in state_fc.columns:
                            state_fc["Non RIS"] = 0
                        # Ensure numeric types
                        state_fc["RIS"] = pd.to_numeric(state_fc["RIS"], errors='coerce').fillna(0)
                        state_fc["Non RIS"] = pd.to_numeric(state_fc["Non RIS"], errors='coerce').fillna(0)
                        state_fc["Grand Total"] = state_fc["RIS"] + state_fc["Non RIS"]
                        state_fc["RIS %"] = ((state_fc["RIS"] / state_fc["Grand Total"]) * 100).round(2).fillna(0)
                        state_fc["Non RIS %"] = ((state_fc["Non RIS"] / state_fc["Grand Total"]) * 100).round(2).fillna(0)
                        
                        # Calculate Grand Total from original data
                        total_ris = float(state_fc["RIS"].sum())
                        total_non_ris = float(state_fc["Non RIS"].sum())
                        total_grand = total_ris + total_non_ris
                        
                        # Add Grand Total row
                        grand_total_row = pd.DataFrame({
                            "FC State Cluster": ["Grand Total"],
                            "FC Cluster": [""],
                            "RIS": [total_ris],
                            "Non RIS": [total_non_ris],
                            "Grand Total": [total_grand],
                            "RIS %": [round((total_ris / total_grand) * 100, 2) if total_grand > 0 else 0],
                            "Non RIS %": [round((total_non_ris / total_grand) * 100, 2) if total_grand > 0 else 0]
                        })
                        state_fc = pd.concat([state_fc, grand_total_row], ignore_index=True)
                        results['state_fc'] = state_fc
                        
                        st.session_state.all_results = results
                        st.success("✅ Data processed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error processing files: {str(e)}")
            else:
                st.warning("⚠️ Please upload all three files first!")
    
    elif manager_type == "Manager":
        # Manager option - Upload RIS Week file and PM file
        st.header("📁 Upload Manager Files")
        st.markdown("Upload the required files:")
        
        ris_week_file = st.file_uploader("Upload RIS Week File", type=['csv', 'xlsx', 'xls'], key='ris_week')
        pm_file = st.file_uploader("Upload PM File", type=['xlsx', 'xls'], key='pm_file')
        
        st.markdown("---")
        
        # Clear cache button
        if st.button("🗑️ Clear Cache", use_container_width=True, key='manager_clear'):
            st.session_state.manager_data = None
            st.session_state.manager_results = {}
            st.session_state.processed_data = None
            st.session_state.all_results = {}
            st.rerun()
        
        if st.button("🔄 Process Manager Data", use_container_width=True, key='manager_process'):
            if ris_week_file and pm_file:
                with st.spinner("Processing Manager data..."):
                    try:
                        # Read RIS Week file (support both CSV and Excel)
                        if ris_week_file.name.endswith('.csv'):
                            ris_week_df = pd.read_csv(ris_week_file, encoding='utf-8-sig')
                        else:
                            ris_week_df = pd.read_excel(ris_week_file)
                        
                        ris_week_df.columns = ris_week_df.columns.str.strip()
                        
                        # Read PM file
                        pm_df = pd.read_excel(pm_file)
                        pm_df.columns = pm_df.columns.str.strip()
                        
                        # Calculate Non RIS = total - ris_units
                        # First, check which columns exist for total and ris_units
                        total_col = None
                        ris_col = None
                        
                        # Look for total column (case-insensitive search)
                        for col in ris_week_df.columns:
                            col_lower = col.lower().replace(" ", "").replace("_", "")
                            if col_lower in ['total', 'totalunits', 'totalqty', 'totalquantity']:
                                total_col = col
                                break
                        
                        # Look for RIS units column
                        for col in ris_week_df.columns:
                            col_lower = col.lower().replace(" ", "").replace("_", "")
                            if col_lower in ['risunits', 'ris', 'risqty', 'risquantity', 'ris_units']:
                                ris_col = col
                                break
                        
                        if total_col and ris_col:
                            # Convert to numeric and calculate Non RIS
                            ris_week_df[total_col] = pd.to_numeric(ris_week_df[total_col], errors='coerce').fillna(0)
                            ris_week_df[ris_col] = pd.to_numeric(ris_week_df[ris_col], errors='coerce').fillna(0)
                            ris_week_df["Non RIS"] = ris_week_df[total_col] - ris_week_df[ris_col]
                        else:
                            st.warning(f"⚠️ Could not find total or ris_units columns. Found columns: {list(ris_week_df.columns)}")
                        
                        # Create mappings from PM file using ASIN
                        # Find ASIN column in both dataframes (case-insensitive)
                        pm_asin_col = None
                        ris_asin_col = None
                        
                        for col in pm_df.columns:
                            if col.lower() == 'asin':
                                pm_asin_col = col
                                break
                        
                        for col in ris_week_df.columns:
                            if col.lower() == 'asin':
                                ris_asin_col = col
                                break
                        
                        if pm_asin_col:
                            pm_df[pm_asin_col] = pm_df[pm_asin_col].astype(str).str.strip().str.upper()
                        
                        if ris_asin_col:
                            ris_week_df[ris_asin_col] = ris_week_df[ris_asin_col].astype(str).str.strip().str.upper()
                        
                            # Create mappings
                            brand_map = dict(zip(pm_df[pm_asin_col], pm_df["Brand"])) if "Brand" in pm_df.columns else {}
                            brand_manager_map = dict(zip(pm_df[pm_asin_col], pm_df["Brand Manager"])) if "Brand Manager" in pm_df.columns else {}
                            vendor_sku_map = dict(zip(pm_df[pm_asin_col], pm_df["Vendor SKU Codes"])) if "Vendor SKU Codes" in pm_df.columns else {}
                            
                            ris_week_df["Brand"] = ris_week_df[ris_asin_col].map(brand_map)
                            ris_week_df["Brand Manager"] = ris_week_df[ris_asin_col].map(brand_manager_map)
                            ris_week_df["Vendor SKU Codes"] = ris_week_df[ris_asin_col].map(vendor_sku_map)
                        else:
                            st.warning(f"⚠️ ASIN column not found in RIS Week file. Found columns: {list(ris_week_df.columns)}")
                        
                        # Convert all object columns to string
                        for col in ris_week_df.columns:
                            if ris_week_df[col].dtype == 'object':
                                ris_week_df[col] = ris_week_df[col].astype(str)
                        
                        # Store the processed data in session state
                        st.session_state.manager_data = ris_week_df
                        
                        # Generate pivot tables for Manager
                        manager_results = {}
                        
                        # Find column names (case-insensitive)
                        ris_units_col = None
                        total_units_col = None
                        cluster_col = None
                        brand_col = None
                        asin_col_for_pivot = ris_asin_col  # Use the already found ASIN column
                        
                        for col in ris_week_df.columns:
                            col_lower = col.lower().replace(" ", "").replace("_", "")
                            if col_lower in ['risunits', 'ris', 'risqty', 'risquantity', 'risunit']:
                                ris_units_col = col
                            if col_lower in ['total', 'totalunits', 'totalqty', 'totalquantity', 'totalunit']:
                                total_units_col = col
                            if col_lower in ['custcluster', 'cluster', 'customercluster']:
                                cluster_col = col
                            if col_lower in ['brand', 'merchantbrandname', 'brandname']:
                                brand_col = col
                            if col_lower == 'asin' and not asin_col_for_pivot:
                                asin_col_for_pivot = col
                        
                        # 1. Brand-wise Pivot
                        if brand_col and ris_units_col and total_units_col and "Non RIS" in ris_week_df.columns:
                            # Convert columns to numeric for aggregation
                            ris_week_df[ris_units_col] = pd.to_numeric(ris_week_df[ris_units_col], errors='coerce').fillna(0)
                            ris_week_df["Non RIS"] = pd.to_numeric(ris_week_df["Non RIS"], errors='coerce').fillna(0)
                            ris_week_df[total_units_col] = pd.to_numeric(ris_week_df[total_units_col], errors='coerce').fillna(0)
                            
                            brand_pivot = ris_week_df.groupby(brand_col).agg({
                                ris_units_col: 'sum',
                                'Non RIS': 'sum',
                                total_units_col: 'sum'
                            }).reset_index()
                            brand_pivot.columns = ["Brand", "RIS Units", "Non RIS", "Total Units"]
                            # Calculate percentages
                            brand_pivot["RIS %"] = ((brand_pivot["RIS Units"] / brand_pivot["Total Units"]) * 100).round(2).fillna(0)
                            brand_pivot["Non RIS %"] = ((brand_pivot["Non RIS"] / brand_pivot["Total Units"]) * 100).round(2).fillna(0)
                            # Add Grand Total
                            total_ris = brand_pivot["RIS Units"].sum()
                            total_non_ris = brand_pivot["Non RIS"].sum()
                            total_units = brand_pivot["Total Units"].sum()
                            grand_total = pd.DataFrame({
                                "Brand": ["Grand Total"],
                                "RIS Units": [total_ris],
                                "Non RIS": [total_non_ris],
                                "Total Units": [total_units],
                                "RIS %": [round((total_ris / total_units) * 100, 2) if total_units > 0 else 0],
                                "Non RIS %": [round((total_non_ris / total_units) * 100, 2) if total_units > 0 else 0]
                            })
                            brand_pivot = pd.concat([brand_pivot, grand_total], ignore_index=True)
                            manager_results['brand_wise'] = brand_pivot
                        
                        # 2. ASIN-wise Pivot
                        if asin_col_for_pivot and ris_units_col and total_units_col and "Non RIS" in ris_week_df.columns:
                            asin_pivot = ris_week_df.groupby(asin_col_for_pivot).agg({
                                ris_units_col: 'sum',
                                'Non RIS': 'sum',
                                total_units_col: 'sum'
                            }).reset_index()
                            asin_pivot.columns = ["ASIN", "RIS Units", "Non RIS", "Total Units"]
                            # Calculate percentages
                            asin_pivot["RIS %"] = ((asin_pivot["RIS Units"] / asin_pivot["Total Units"]) * 100).round(2).fillna(0)
                            asin_pivot["Non RIS %"] = ((asin_pivot["Non RIS"] / asin_pivot["Total Units"]) * 100).round(2).fillna(0)
                            # Add Grand Total
                            total_ris = asin_pivot["RIS Units"].sum()
                            total_non_ris = asin_pivot["Non RIS"].sum()
                            total_units = asin_pivot["Total Units"].sum()
                            grand_total = pd.DataFrame({
                                "ASIN": ["Grand Total"],
                                "RIS Units": [total_ris],
                                "Non RIS": [total_non_ris],
                                "Total Units": [total_units],
                                "RIS %": [round((total_ris / total_units) * 100, 2) if total_units > 0 else 0],
                                "Non RIS %": [round((total_non_ris / total_units) * 100, 2) if total_units > 0 else 0]
                            })
                            asin_pivot = pd.concat([asin_pivot, grand_total], ignore_index=True)
                            manager_results['asin_wise'] = asin_pivot
                        
                        # 3. Cluster-wise Pivot
                        if cluster_col and ris_units_col and total_units_col and "Non RIS" in ris_week_df.columns:
                            cluster_pivot = ris_week_df.groupby(cluster_col).agg({
                                ris_units_col: 'sum',
                                'Non RIS': 'sum',
                                total_units_col: 'sum'
                            }).reset_index()
                            cluster_pivot.columns = ["Cluster", "RIS Units", "Non RIS", "Total Units"]
                            # Calculate percentages
                            cluster_pivot["RIS %"] = ((cluster_pivot["RIS Units"] / cluster_pivot["Total Units"]) * 100).round(2).fillna(0)
                            cluster_pivot["Non RIS %"] = ((cluster_pivot["Non RIS"] / cluster_pivot["Total Units"]) * 100).round(2).fillna(0)
                            # Add Grand Total
                            total_ris = cluster_pivot["RIS Units"].sum()
                            total_non_ris = cluster_pivot["Non RIS"].sum()
                            total_units = cluster_pivot["Total Units"].sum()
                            grand_total = pd.DataFrame({
                                "Cluster": ["Grand Total"],
                                "RIS Units": [total_ris],
                                "Non RIS": [total_non_ris],
                                "Total Units": [total_units],
                                "RIS %": [round((total_ris / total_units) * 100, 2) if total_units > 0 else 0],
                                "Non RIS %": [round((total_non_ris / total_units) * 100, 2) if total_units > 0 else 0]
                            })
                            cluster_pivot = pd.concat([cluster_pivot, grand_total], ignore_index=True)
                            manager_results['cluster_wise'] = cluster_pivot
                        
                        # 4. Cluster-ASIN Pivot
                        if cluster_col and asin_col_for_pivot and ris_units_col and total_units_col and "Non RIS" in ris_week_df.columns:
                            cluster_asin_pivot = ris_week_df.groupby([cluster_col, asin_col_for_pivot]).agg({
                                ris_units_col: 'sum',
                                'Non RIS': 'sum',
                                total_units_col: 'sum'
                            }).reset_index()
                            cluster_asin_pivot.columns = ["Cluster", "ASIN", "RIS Units", "Non RIS", "Total Units"]
                            # Calculate percentages
                            cluster_asin_pivot["RIS %"] = ((cluster_asin_pivot["RIS Units"] / cluster_asin_pivot["Total Units"]) * 100).round(2).fillna(0)
                            cluster_asin_pivot["Non RIS %"] = ((cluster_asin_pivot["Non RIS"] / cluster_asin_pivot["Total Units"]) * 100).round(2).fillna(0)
                            # Add Grand Total
                            total_ris = cluster_asin_pivot["RIS Units"].sum()
                            total_non_ris = cluster_asin_pivot["Non RIS"].sum()
                            total_units = cluster_asin_pivot["Total Units"].sum()
                            grand_total = pd.DataFrame({
                                "Cluster": ["Grand Total"],
                                "ASIN": [""],
                                "RIS Units": [total_ris],
                                "Non RIS": [total_non_ris],
                                "Total Units": [total_units],
                                "RIS %": [round((total_ris / total_units) * 100, 2) if total_units > 0 else 0],
                                "Non RIS %": [round((total_non_ris / total_units) * 100, 2) if total_units > 0 else 0]
                            })
                            cluster_asin_pivot = pd.concat([cluster_asin_pivot, grand_total], ignore_index=True)
                            manager_results['cluster_asin'] = cluster_asin_pivot
                        
                        st.session_state.manager_results = manager_results
                        st.success("✅ Manager data processed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error processing files: {str(e)}")
            else:
                st.warning("⚠️ Please upload both RIS Week file and PM file!")

    elif manager_type == "RIS Samriddhi":
        st.header("📋 Upload Samriddhi Files")
        st.markdown("Upload the required files:")
        
        samriddhi_file = st.file_uploader("Upload Samriddhi File (CSV)", type=['csv'], key='samriddhi_file')
        pm_file_samriddhi = st.file_uploader("Upload PM File (Excel)", type=['xlsx', 'xls'], key='pm_file_samriddhi')
        
        st.markdown("---")
        
        # Clear cache button
        if st.button("🗑️ Clear Cache", use_container_width=True, key='samriddhi_clear'):
            st.session_state.samriddhi_data = None
            st.session_state.samriddhi_results = {}
            st.session_state.processed_data = None
            st.session_state.all_results = {}
            st.session_state.manager_data = None
            st.session_state.manager_results = {}
            st.rerun()
            
        if st.button("🔄 Process Samriddhi Data", use_container_width=True, key='samriddhi_process'):
            if samriddhi_file and pm_file_samriddhi:
                with st.spinner("Processing Samriddhi data..."):
                    try:
                        # Read Samriddhi CSV
                        sam_df = pd.read_csv(samriddhi_file, encoding='utf-8-sig')
                        sam_df.columns = sam_df.columns.str.strip()
                        
                        # Read PM Excel
                        pm_df = pd.read_excel(pm_file_samriddhi)
                        pm_df.columns = pm_df.columns.str.strip()
                        
                        # Normalize ASIN columns with robust detection
                        pm_asin_col = find_column(pm_df, ['asin', 'amazonasin', 'itemasin'])
                        sam_asin_col = find_column(sam_df, ['asin', 'amazonasin', 'itemasin'])
                        
                        if pm_asin_col and sam_asin_col:
                            # Standardize keys: upper, string, strip
                            pm_df[pm_asin_col] = pm_df[pm_asin_col].astype(str).str.strip().str.upper()
                            sam_df[sam_asin_col] = sam_df[sam_asin_col].astype(str).str.strip().str.upper()
                            
                            # Find required columns in PM file robustly
                            pm_sku_col = find_column(pm_df, ['amazonskuname', 'sku', 'merchantsku'])
                            pm_brand_col = find_column(pm_df, ['brand', 'brandname', 'merchantbrand'])
                            pm_manager_col = find_column(pm_df, ['brandmanager', 'manager', 'bm'])
                            pm_vsku_col = find_column(pm_df, ['vendorskucodes', 'vendorsku', 'vsku'])
                            pm_pname_col = find_column(pm_df, ['productname', 'title', 'itemname', 'product'])
                            
                            # Create mappings (only if columns exist)
                            sku_map = dict(zip(pm_df[pm_asin_col], pm_df[pm_sku_col])) if pm_sku_col else {}
                            brand_map = dict(zip(pm_df[pm_asin_col], pm_df[pm_brand_col])) if pm_brand_col else {}
                            bm_map = dict(zip(pm_df[pm_asin_col], pm_df[pm_manager_col])) if pm_manager_col else {}
                            v_sku_map = dict(zip(pm_df[pm_asin_col], pm_df[pm_vsku_col])) if pm_vsku_col else {}
                            p_name_map = dict(zip(pm_df[pm_asin_col], pm_df[pm_pname_col])) if pm_pname_col else {}
                            
                            # Map columns to Samriddhi DataFrame
                            sam_df["Amazon Sku Name"] = sam_df[sam_asin_col].map(sku_map)
                            sam_df["Vendor Sku Codes"] = sam_df[sam_asin_col].map(v_sku_map)
                            sam_df["Brand"] = sam_df[sam_asin_col].map(brand_map)
                            sam_df["Brand Manager"] = sam_df[sam_asin_col].map(bm_map)
                            sam_df["Product Name"] = sam_df[sam_asin_col].map(p_name_map)
                            
                            # Show warnings for missing PM columns
                            missing_pm = []
                            if not pm_sku_col: missing_pm.append("SKU")
                            if not pm_brand_col: missing_pm.append("Brand")
                            if not pm_manager_col: missing_pm.append("Brand Manager")
                            if not pm_vsku_col: missing_pm.append("Vendor SKU")
                            if not pm_pname_col: missing_pm.append("Product Name")
                            if missing_pm:
                                st.warning(f"⚠️ PM file is missing columns for: {', '.join(missing_pm)}")

                            # Reorder columns to place new columns after ASIN
                            cols = list(sam_df.columns)
                            new_cols = ["Amazon Sku Name", "Vendor Sku Codes", "Brand", "Brand Manager", "Product Name"]
                            for c in new_cols:
                                if c in cols: cols.remove(c)
                            
                            asin_idx = cols.index(sam_asin_col) if sam_asin_col in cols else -1
                            if asin_idx != -1:
                                final_cols = cols[:asin_idx+1] + new_cols + cols[asin_idx+1:]
                                # Ensure only existing columns are used
                                final_cols = [c for c in final_cols if c in sam_df.columns]
                                sam_df = sam_df[final_cols]
                        else:
                            if not sam_asin_col:
                                st.error(f"❌ ASIN column not found in Samriddhi file. Columns: {list(sam_df.columns)}")
                            if not pm_asin_col:
                                st.error(f"❌ ASIN column not found in PM file. Columns: {list(pm_df.columns)}")

                        # Convert columns to string/numeric as appropriate and handle ris_week specifically
                        ris_week_cols = [c for c in sam_df.columns if c.lower().startswith("ris_week")]
                        
                        for col in sam_df.columns:
                            if col in ris_week_cols:
                                # For ris_week columns, fill NaNs with 0 and convert to percentage
                                sam_df[col] = pd.to_numeric(sam_df[col], errors='coerce').fillna(0)
                                sam_df[col] = (sam_df[col] * 100).round(2)
                            elif sam_df[col].dtype == 'object':
                                sam_df[col] = sam_df[col].astype(str)
                            else:
                                # For other numeric columns, just ensure numeric type
                                sam_df[col] = pd.to_numeric(sam_df[col], errors='coerce')
                        
                        # Store processed data
                        st.session_state.samriddhi_data = sam_df
                        
                        # Generate pivots
                        sam_results = {}
                        
                        # Total Units columns (robust find)
                        total_cw_col = find_column(sam_df, ['totalunitscw', 'cwtotal', 'unitscw'])
                        total_l30d_col = find_column(sam_df, ['totalunitsl30d', 'l30dtotal', 'unitsl30d'])
                        cluster_col = find_column(sam_df, ['custcluster', 'cluster', 'customercluster'])

                        # 1. Brand-wise Pivot
                        if "Brand" in sam_df.columns and total_cw_col and total_l30d_col:
                            # Sum logic
                            sam_df[total_cw_col] = pd.to_numeric(sam_df[total_cw_col], errors='coerce').fillna(0)
                            sam_df[total_l30d_col] = pd.to_numeric(sam_df[total_l30d_col], errors='coerce').fillna(0)
                            
                            brand_pivot = sam_df.groupby("Brand").agg({
                                total_cw_col: 'sum',
                                total_l30d_col: 'sum'
                            }).reset_index()
                            # Add Grand Total
                            grand_total = pd.DataFrame({
                                "Brand": ["Grand Total"],
                                total_cw_col: [brand_pivot[total_cw_col].sum()],
                                total_l30d_col: [brand_pivot[total_l30d_col].sum()]
                            })
                            brand_pivot = pd.concat([brand_pivot, grand_total], ignore_index=True)
                            sam_results['brand_wise'] = brand_pivot
                            
                        # 2. Cluster-wise Pivot
                        if cluster_col and total_cw_col and total_l30d_col:
                            cluster_pivot = sam_df.groupby(cluster_col).agg({
                                total_cw_col: 'sum',
                                total_l30d_col: 'sum'
                            }).reset_index()
                            # Add Grand Total
                            grand_total = pd.DataFrame({
                                cluster_col: ["Grand Total"],
                                total_cw_col: [cluster_pivot[total_cw_col].sum()],
                                total_l30d_col: [cluster_pivot[total_l30d_col].sum()]
                            })
                            cluster_pivot = pd.concat([cluster_pivot, grand_total], ignore_index=True)
                            sam_results['cluster_wise'] = cluster_pivot
                            
                        # 3. ASIN-wise Pivot
                        if sam_asin_col and total_cw_col and total_l30d_col:
                            asin_pivot = sam_df.groupby(sam_asin_col).agg({
                                total_cw_col: 'sum',
                                total_l30d_col: 'sum'
                            }).reset_index()
                            # Add Grand Total
                            grand_total = pd.DataFrame({
                                sam_asin_col: ["Grand Total"],
                                total_cw_col: [asin_pivot[total_cw_col].sum()],
                                total_l30d_col: [asin_pivot[total_l30d_col].sum()]
                            })
                            asin_pivot = pd.concat([asin_pivot, grand_total], ignore_index=True)
                            sam_results['asin_wise'] = asin_pivot

                        st.session_state.samriddhi_results = sam_results
                        st.success("✅ Samriddhi data processed successfully!")
                    except Exception as e:
                        st.error(f"❌ Error processing files: {str(e)}")
            else:
                st.warning("⚠️ Please upload both Samriddhi and PM files!")

# Main content area
if st.session_state.processed_data is not None:
    tabs = st.tabs([
        "📋 Processed Data",
        "🏷️ Brand-wise RIS",
        "🔖 ASIN-wise RIS",
        "🏢 Cluster-wise RIS",
        "📊 Cluster-Brand Analysis",
        "🗺️ State Cluster Analysis",
        "📍 State-FC Analysis"
    ])
    
    # Tab 1: Processed Data
    with tabs[0]:
        st.header("Processed RIS Data")
        df = st.session_state.processed_data
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", f"{len(df):,}")
        with col2:
            ris_count = len(df[df["RIS Status"] == "RIS"])
            st.metric("RIS Orders", f"{ris_count:,}")
        with col3:
            non_ris_count = len(df[df["RIS Status"] == "Non RIS"])
            st.metric("Non-RIS Orders", f"{non_ris_count:,}")
        with col4:
            ris_percent = (ris_count / len(df) * 100) if len(df) > 0 else 0
            st.metric("RIS %", f"{ris_percent:.2f}%")
        
        st.markdown("---")
        st.dataframe(df, use_container_width=True, height=400)
        
        st.download_button(
            label="📥 Download Processed Data (Excel)",
            data=to_excel(df),
            file_name="processed_ris_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Tab 2: Brand-wise RIS
    with tabs[1]:
        st.header("Brand-wise RIS Analysis")
        if 'brand_wise' in st.session_state.all_results:
            df = st.session_state.all_results['brand_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Brand-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="brand_wise_ris.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Tab 3: ASIN-wise RIS
    with tabs[2]:
        st.header("ASIN-wise RIS Analysis")
        if 'asin_wise' in st.session_state.all_results:
            df = st.session_state.all_results['asin_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download ASIN-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="asin_wise_ris.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Tab 4: Cluster-wise RIS
    with tabs[3]:
        st.header("Cluster-wise RIS Analysis")
        if 'cluster_wise' in st.session_state.all_results:
            df = st.session_state.all_results['cluster_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Cluster-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="cluster_wise_ris.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Tab 5: Cluster-Brand Analysis
    with tabs[4]:
        st.header("Cluster-Brand RIS Analysis")
        if 'cluster_brand' in st.session_state.all_results:
            df = st.session_state.all_results['cluster_brand']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Cluster-Brand Analysis (Excel)",
                data=to_excel(df),
                file_name="cluster_brand_ris.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Tab 6: State Cluster Analysis
    with tabs[5]:
        st.header("State Cluster RIS Analysis")
        if 'state_cluster' in st.session_state.all_results:
            df = st.session_state.all_results['state_cluster']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download State Cluster Analysis (Excel)",
                data=to_excel(df),
                file_name="state_cluster_ris.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Tab 7: State-FC Analysis
    with tabs[6]:
        st.header("State-FC RIS Analysis")
        if 'state_fc' in st.session_state.all_results:
            df = st.session_state.all_results['state_fc']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download State-FC Analysis (Excel)",
                data=to_excel(df),
                file_name="state_fc_ris.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


elif st.session_state.manager_data is not None:
    # Manager Data Display with Tabs
    manager_tabs = st.tabs([
        "📋 Processed Data",
        "🏷️ Brand-wise",
        "🔖 ASIN-wise",
        "🏢 Cluster-wise",
        "📊 Cluster-ASIN"
    ])
    
    # Tab 1: Processed Data
    with manager_tabs[0]:
        st.header("📊 Manager RIS Week Data")
        df = st.session_state.manager_data
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", f"{len(df):,}")
        with col2:
            if "Non RIS" in df.columns:
                non_ris_total = pd.to_numeric(df["Non RIS"], errors='coerce').sum()
                st.metric("Total Non RIS", f"{non_ris_total:,.0f}")
        with col3:
            # Find the RIS column
            ris_col = None
            for col in df.columns:
                col_lower = col.lower().replace(" ", "").replace("_", "")
                if col_lower in ['risunits', 'ris', 'risqty', 'risquantity', 'ris_units']:
                    ris_col = col
                    break
            if ris_col:
                ris_total = pd.to_numeric(df[ris_col], errors='coerce').sum()
                st.metric("Total RIS", f"{ris_total:,.0f}")
        
        st.markdown("---")
        st.dataframe(df, use_container_width=True, height=500)
        
        st.download_button(
            label="📥 Download Manager RIS Data (Excel)",
            data=to_excel(df),
            file_name="manager_ris_week_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Tab 2: Brand-wise Pivot
    with manager_tabs[1]:
        st.header("🏷️ Brand-wise Analysis")
        if 'brand_wise' in st.session_state.manager_results:
            df = st.session_state.manager_results['brand_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Brand-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="manager_brand_wise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Brand-wise pivot not available. Ensure Brand column is mapped from PM file.")
    
    # Tab 3: ASIN-wise Pivot
    with manager_tabs[2]:
        st.header("🔖 ASIN-wise Analysis")
        if 'asin_wise' in st.session_state.manager_results:
            df = st.session_state.manager_results['asin_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download ASIN-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="manager_asin_wise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ ASIN-wise pivot not available. Ensure ASIN column exists in RIS Week file.")
    
    # Tab 4: Cluster-wise Pivot
    with manager_tabs[3]:
        st.header("🏢 Cluster-wise Analysis")
        if 'cluster_wise' in st.session_state.manager_results:
            df = st.session_state.manager_results['cluster_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Cluster-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="manager_cluster_wise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Cluster-wise pivot not available. Ensure cust_cluster column exists in RIS Week file.")
    
    # Tab 5: Cluster-ASIN Pivot
    with manager_tabs[4]:
        st.header("📊 Cluster-ASIN Analysis")
        if 'cluster_asin' in st.session_state.manager_results:
            df = st.session_state.manager_results['cluster_asin']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Cluster-ASIN Analysis (Excel)",
                data=to_excel(df),
                file_name="manager_cluster_asin.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Cluster-ASIN pivot not available. Ensure both cust_cluster and ASIN columns exist.")

elif st.session_state.samriddhi_data is not None:
    # Samriddhi Data Display with Tabs
    sam_tabs = st.tabs([
        "📋 Processed Data",
        "📊 Deep Dive Pivot",
        "🏷️ Brand-wise",
        "🏢 Cluster-wise",
        "🔖 ASIN-wise"
    ])
    
    # Tab 1: Processed Data
    with sam_tabs[0]:
        st.header("📊 RIS Samriddhi Data")
        df = st.session_state.samriddhi_data
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", f"{len(df):,}")
        with col2:
            # Find total_units_cw column
            total_cw_col = find_column(df, ['totalunitscw', 'cwtotal', 'unitscw'])
            if total_cw_col:
                total_units = pd.to_numeric(df[total_cw_col], errors='coerce').sum()
                st.metric("Total Units (CW)", f"{total_units:,.0f}")
        with col3:
            # Find total_units_l30d column
            total_l30_col = find_column(df, ['totalunitsl30d', 'l30dtotal', 'unitsl30d'])
            if total_l30_col:
                total_l30 = pd.to_numeric(df[total_l30_col], errors='coerce').sum()
                st.metric("Total Units (L30D)", f"{total_l30:,.0f}")
        
        st.markdown("---")
        st.dataframe(df, use_container_width=True, height=500)
        
        st.download_button(
            label="📥 Download Samriddhi Data (Excel)",
            data=to_excel(df),
            file_name="samriddhi_ris_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Tab 2: Deep Dive Pivot
    with sam_tabs[1]:
        st.header("📊 Deep Dive Pivot Analysis")
        df = st.session_state.samriddhi_data
        
        # 1. Cluster Filter
        cluster_col = find_column(df, ['custcluster', 'cluster', 'customercluster'])
        
        if cluster_col:
            selected_clusters = st.multiselect(
                "Filter by Cluster",
                options=sorted(df[cluster_col].unique()),
                default=[]
            )
            
            # Filter Data
            if selected_clusters:
                filtered_df = df[df[cluster_col].isin(selected_clusters)]
            else:
                filtered_df = df
        else:
            filtered_df = df
            st.warning("⚠️ Cluster column not found for filtering.")

        # 2. Pivot Table
        ris_week_cols = [c for c in filtered_df.columns if c.lower().startswith("ris_week")]
        asin_col = None
        for col in filtered_df.columns:
            if col.lower() == 'asin':
                asin_col = col
                break
        
        if asin_col and ris_week_cols:
            pivot_df = filtered_df.groupby([asin_col, "Brand"]).agg({
                col: 'sum' for col in ris_week_cols
            }).reset_index()
            
            st.dataframe(pivot_df, use_container_width=True, height=500)
            
            st.download_button(
                label="📥 Download Deep Dive Pivot (Excel)",
                data=to_excel(pivot_df),
                file_name="deep_dive_pivot.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ ASIN or Weekly RIS columns not found for pivoting.")

    # Tab 3: Brand-wise Pivot
    with sam_tabs[2]:
        st.header("🏷️ Brand-wise Analysis")
        if 'brand_wise' in st.session_state.samriddhi_results:
            df = st.session_state.samriddhi_results['brand_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Brand-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="samriddhi_brand_wise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Brand-wise pivot not available.")
            
    # Tab 3: Cluster-wise Pivot
    with sam_tabs[3]:
        st.header("🏢 Cluster-wise Analysis")
        if 'cluster_wise' in st.session_state.samriddhi_results:
            df = st.session_state.samriddhi_results['cluster_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download Cluster-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="samriddhi_cluster_wise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Cluster-wise pivot not available.")
            
    # Tab 4: ASIN-wise Pivot
    with sam_tabs[4]:
        st.header("🔖 ASIN-wise Analysis")
        if 'asin_wise' in st.session_state.samriddhi_results:
            df = st.session_state.samriddhi_results['asin_wise']
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="📥 Download ASIN-wise Analysis (Excel)",
                data=to_excel(df),
                file_name="samriddhi_asin_wise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ ASIN-wise pivot not available.")

else:
    # Welcome screen
    st.info("👋 Welcome! Please upload the required files using the sidebar to begin analysis.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📄 RIS.csv
        - Main shipment data
        - Contains order details
        - Shipping information
        """)
    
    with col2:
        st.markdown("""
        ### 🗂️ State FC Cluster.xlsx
        - FC and cluster mapping
        - State assignments
        - Cluster definitions
        """)
    
    with col3:
        st.markdown("""
        ### 📦 PM.xlsx
        - Product master data
        - Brand information
        - ASIN mappings
        """)
    
    st.markdown("---")
    st.markdown("""
    ### 📊 Analysis Features:
    
    **Amazon Manager:**
    - Processed Data: Complete dataset with RIS status calculations
    - Brand-wise RIS: Performance metrics by brand
    - ASIN-wise RIS: Product-level analysis
    - Cluster-wise RIS: FC cluster performance
    - Cluster-Brand Analysis: Combined cluster and brand insights
    - State Cluster Analysis: State-level cluster metrics
    - State-FC Analysis: Detailed state and FC mapping
    
    **Manager:**
    - RIS Week Data with Non RIS calculations
    - Brand, Brand Manager, Vendor SKU mappings from PM file
    
    **RIS Samriddhi:**
    - Deep Dive ASIN level analysis
    - Support for custom Samriddhi CSV format
    - Mapping with Purchase Master for brand insights
    
    All reports can be downloaded as Excel files! 📥

    """)
