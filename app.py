import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import IntegrityError
from datetime import datetime
import os

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="KEEP-Stock", page_icon="📦", layout="wide")

# Gen Z Aesthetic CSS - Dark Cyberpunk Theme with Custom Button Types
st.markdown("""
    <style>
    /* Dynamic Cyber Canvas Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c1b 0%, #201335 50%, #0b1e36 100%);
        color: #ffffff;
    }
    
    /* Standard User Buttons (Neon Cyan/Purple) */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background: linear-gradient(90deg, #8A2BE2, #00FFFF);
        color: white;
        font-weight: bold;
        border: none;
        box-shadow: 0px 4px 15px rgba(0, 255, 255, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 20px rgba(138, 43, 226, 0.6);
        color: #ffffff;
    }
    
    /* Crimson Neon Buttons For Exclusive Admin Interaction */
    .admin-btn button {
        background: linear-gradient(90deg, #FF4B2B, #FF416C) !important;
        box-shadow: 0px 4px 15px rgba(255, 75, 43, 0.3) !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        height: 3em !important;
        border: none !important;
    }
    .admin-btn button:hover {
        box-shadow: 0px 6px 20px rgba(255, 65, 108, 0.6) !important;
        transform: translateY(-2px);
    }
    
    /* Premium Glassmorphism Floating Cards */
    .custom-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 25px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 20px;
    }
    
    h1, h2, h3 {
        color: #00FFFF !important;
        font-family: 'Inter', sans-serif;
    }
    .stWidgetFormLabel, label {
        color: #e0e0e0 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        color: #ffffff;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #8A2BE2, #00FFFF) !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. MULTI-TENANT DATABASE ROUTINES (POSTGRESQL) ---
def get_connection():
    """Establishes connection using Streamlit secrets dynamically."""
    if "postgres" in st.secrets:
        return psycopg2.connect(st.secrets["postgres"]["url"])
    elif "POSTGRESQL_URL" in st.secrets:
        return psycopg2.connect(st.secrets["POSTGRESQL_URL"])
    else:
        raise Exception("Configuration Error: Connection string missing from environment secrets.")

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id SERIAL PRIMARY KEY, 
                  user_id TEXT,
                  name TEXT, 
                  brand TEXT, 
                  model TEXT, 
                  price REAL, 
                  date_bought TEXT,
                  timestamp TEXT)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  password TEXT,
                  role TEXT DEFAULT 'user')''')
                  
    try:
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'")
    except Exception:
        pass
        
    try:
        c.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS user_id TEXT")
    except Exception:
        pass

    conn.commit()
    c.close()
    conn.close()

def add_user(username, password, role):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
        conn.commit()
        c.close()
        conn.close()
        return True
    except IntegrityError:
        return False

def check_user(username, password, role):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=%s AND password=%s AND role=%s", (username, password, role))
    user = c.fetchone()
    c.close()
    conn.close()
    return user is not None

def add_item(user_id, name, brand, model, price, date_bought):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO items (user_id, name, brand, model, price, date_bought, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
              (user_id, name, brand, model, price, date_bought, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    c.close()
    conn.close()

def update_item(item_id, name, brand, model, price, date_bought):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""UPDATE items 
                 SET name=%s, brand=%s, model=%s, price=%s, date_bought=%s 
                 WHERE id=%s""", (name, brand, model, price, str(date_bought), item_id))
    conn.commit()
    c.close()
    conn.close()

def get_user_items(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name, brand, model, price, date_bought, timestamp FROM items WHERE user_id=%s", conn, params=(user_id,))
    conn.close()
    return df

def delete_item(item_id, user_id, global_override=False):
    conn = get_connection()
    c = conn.cursor()
    if global_override:
        c.execute("DELETE FROM items WHERE id=%s", (item_id,))
    else:
        c.execute("DELETE FROM items WHERE id=%s AND user_id=%s", (item_id, user_id))
    conn.commit()
    c.close()
    conn.close()

def admin_fetch_users():
    conn = get_connection()
    df = pd.read_sql_query("SELECT username FROM users WHERE role='user'", conn)
    conn.close()
    return df

def admin_fetch_master_feed():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name, brand, model, price, date_bought, timestamp, user_id FROM items", conn)
    conn.close()
    return df

def admin_delete_user(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=%s AND role='user'", (username,))
    c.execute("DELETE FROM items WHERE user_id=%s", (username,))
    conn.commit()
    c.close()
    conn.close()

def admin_nuke_system():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM items")
    c.execute("DELETE FROM users WHERE role='user'")
    conn.commit()
    c.close()
    conn.close()

# Initialize Database Architecture
init_db()

# --- 3. SESSION MANAGEMENT CONFIGURATION ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'role' not in st.session_state: st.session_state['role'] = "user"

# --- 4. DEDICATED SEPARATED ENTRYWAY PORTAL ---
def auth_screen():
    st.markdown("<br><div style='text-align: center;'><h1>📦 KEEP-Stock Hub</h1></div>", unsafe_allow_html=True)
    
    auth_mode = st.radio("Choose Entrance Hub", ["👤 Standard User Portal", "🔑 System Admin Hub"], horizontal=True)
    
    col1, col2, col3 = st.columns([1,1.8,1])
    with col2:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        
        if auth_mode == "👤 Standard User Portal":
            tab1, tab2 = st.tabs(["🚀 User Login", "✨ User Registration"])
            with tab1:
                st.markdown("### Access User Vault")
                u_log = st.text_input("Username", key="user_log_uid").strip().lower()
                p_log = st.text_input("Password", type="password", key="user_log_pwd")
                if st.button("Sign In as User"):
                    if check_user(u_log, p_log, "user"):
                        st.session_state.update({"logged_in": True, "user_name": u_log, "role": "user"})
                        st.toast(f"Welcome to KEEP-Stock, {u_log}!", icon="🔥")
                        st.rerun()
                    else: st.error("User credentials verification failed.")
            with tab2:
                st.markdown("### Register New Account Space")
                u_reg = st.text_input("Choose Username", key="user_reg_uid").strip().lower()
                p_reg = st.text_input("Choose Password", type="password", key="user_reg_pwd")
                if st.button("Create & Launch User Workspace"):
                    if not u_reg or not p_reg: st.error("Fields cannot be empty.")
                    elif add_user(u_reg, p_reg, "user"):
                        st.session_state.update({"logged_in": True, "user_name": u_reg, "role": "user"})
                        st.balloons()
                        st.rerun()
                    else: st.error("Username already exists in the system.")
                    
        else:
            tab1, tab2 = st.tabs(["🔒 Admin Authentication", "👑 Admin Registration"])
            with tab1:
                st.markdown("### Executive Control Authorization")
                a_log = st.text_input("Admin Username ID", key="adm_log_uid").strip().lower()
                ap_log = st.text_input("Admin Security Password", type="password", key="adm_log_pwd")
                st.markdown('<div class="admin-btn">', unsafe_allow_html=True)
                if st.button("EXECUTE ADMIN LOGIN"):
                    if check_user(a_log, ap_log, "admin"):
                        st.session_state.update({"logged_in": True, "user_name": a_log, "role": "admin"})
                        st.toast("Ecosystem Root Clearance Access Granted.", icon="👑")
                        st.rerun()
                    else: st.error("Administrative authentication failed.")
                st.markdown('</div>', unsafe_allow_html=True)
            with tab2:
                st.markdown("### Provision Administrative Access Key")
                a_reg = st.text_input("New Admin Registration Username", key="adm_reg_uid").strip().lower()
                ap_reg = st.text_input("Configure Admin Password", type="password", key="adm_reg_pwd")
                st.markdown('<div class="admin-btn">', unsafe_allow_html=True)
                if st.button("PROVISION ADMIN PRIVILEGES"):
                    if not a_reg or not ap_reg: st.error("Fields cannot be empty.")
                    elif add_user(a_reg, ap_reg, "admin"):
                        st.session_state.update({"logged_in": True, "user_name": a_reg, "role": "admin"})
                        st.balloons()
                        st.rerun()
                    else: st.error("Admin username string registered or taken.")
                st.markdown('</div>', unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)

# --- 5. CORE WORKSPACE ROUTER ENGINE ---
if not st.session_state['logged_in']:
    auth_screen()
else:
    current_user = st.session_state['user_name']
    user_tier = st.session_state['role']
    
    st.sidebar.title(f"📦 KEEP-Stock Hub")
    st.sidebar.info(f"Active Identity: {current_user.upper()} ({user_tier.upper()})")
    if st.sidebar.button("Secure System Logout"):
        st.session_state.clear()
        st.rerun()
        
    menu_options = ["Dashboard", "AI Smart Add", "Manual Add"]
    if user_tier == "admin": 
        menu_options.append("👑 Admin Suite Control")
    menu = st.sidebar.radio("Core Menu Matrix", menu_options)

    # --- MENU INTERACTION BLOCK A: PRIVATE PERSONAL VAULT ---
    if menu == "Dashboard":
        st.title("📊 Your Isolated Inventory Vault")
        
        raw_df = get_user_items(current_user)
        
        if not raw_df.empty:
            display_df = raw_df.copy()
            display_df.insert(0, 'Item No.', range(1, len(display_df) + 1))
            
            if 'price' in display_df.columns:
                display_df['price'] = display_df['price'].apply(lambda x: f"₹{x:,.2f}" if x else "₹0.00")
            
            system_id_mapping = dict(zip(range(1, len(raw_df) + 1), raw_df['id'].tolist()))
            display_df = display_df.drop(columns=['id'])
            st.dataframe(display_df, use_container_width=True)
            
            # --- COMPONENT UPDATE DESK CARD ---
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.subheader("⚙️ Asset Calibration Desk")
            
            panel_tab1, panel_tab2 = st.tabs(["✏️ Update Node Info", "🗑️ Delete Node Info"])
            
            with panel_tab1:
                st.write("Modify properties of a pre-determined inventory object entry.")
                selected_local_no = st.selectbox("Choose Item No. to Update Changes", list(system_id_mapping.keys()), key="update_item_selector")
                corresponding_db_id = system_id_mapping[selected_local_no]
                
                target_row_data = raw_df[raw_df['id'] == corresponding_db_id].iloc[0]
                
                with st.form("inline_update_form"):
                    u_name = st.text_input("Object Label / Name", value=str(target_row_data['name']))
                    uc1, uc2 = st.columns(2)
                    u_brand = uc1.text_input("Brand Classification", value=str(target_row_data['brand']))
                    u_model = uc2.text_input("Model Signature Identifier", value=str(target_row_data['model']))
                    
                    u_price = st.number_input("Valuation Metric (₹)", min_value=0.0, value=float(target_row_data['price']) if target_row_data['price'] else 0.0)
                    
                    try:
                        parsed_default_date = datetime.strptime(str(target_row_data['date_bought']), "%Y-%m-%d").date()
                    except ValueError:
                        parsed_default_date = datetime.today().date()
                        
                    u_date = st.date_input("Transaction Log Date Value", value=parsed_default_date)
                    
                    if st.form_submit_button("Commit Changes Successfully"):
                        if u_name:
                            update_item(corresponding_db_id, u_name, u_brand, u_model, u_price, u_date)
                            st.success(f"Item #{selected_local_no} update processed within the vault architecture grid.")
                            st.rerun()
                        else: st.error("Error: Object requires a valid entry name designation.")
                        
            with panel_tab2:
                delete_local_no = st.selectbox("Identify Item No. Node to Terminate", list(system_id_mapping.keys()), key="delete_item_selector")
                target_db_del_id = system_id_mapping[delete_local_no]
                if st.button("Drop Selected Record"):
                    delete_item(target_db_del_id, current_user, global_override=False)
                    st.success(f"Asset item #{delete_local_no} dropped completely from storage matrix.")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Your database table is blank. Register or scan fresh items to occupy this catalog space.")

    # --- MENU INTERACTION BLOCK B: CONVERSATIONAL AI IMAGE SCANNER ---
    elif menu == "AI Smart Add":
        st.title("🤖 AI Scan Node (Powered by Gemini)")
        st.markdown("### 1. Optical Capture Feed")
        img_file = st.camera_input("Acquire live device stream image snapshot")
        
        ai_extracted = {"name": "", "brand": "", "model": ""}
        
        if img_file:
            st.image(img_file)
            
            with st.spinner("🤖 Neural Parser State: Analyzing object structural signatures via Gemini..."):
                try:
                    from PIL import Image
                    import json
                    from google import genai
                    from google.genai import types
                    import time
                    
                    pil_image = Image.open(img_file)
                    
                    if "GEMINI_API_KEY" in st.secrets:
                        YOUR_GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
                    elif os.environ.get("GEMINI_API_KEY"):
                        YOUR_GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
                    else:
                        YOUR_GEMINI_KEY = "" 

                    client = genai.Client(api_key=YOUR_GEMINI_KEY)
                    
                    camera_prompt = """
                    Analyze this image and identify the primary piece of equipment or object.
                    You must respond ONLY with a raw JSON dictionary using exactly these keys: "name", "brand", "model", "price", "date".
                    
                    Rules:
                    - "name": The general name of the item (e.g., Laptop, Camera, Monitor).
                    - "brand": The manufacturer brand if visible or easily recognizable.
                    - "model": The specific model sequence or text visible on the item.
                    - "price": Estimate a standard market value in numbers (as a float). If entirely unknown, use 0.0.
                    - "date": Leave as an empty string "".
                    
                    Do not add markdown formatting or code blocks. Just return the raw JSON object string.
                    """
                    
                    time.sleep(2)
        
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[pil_image, camera_prompt]
                    )
                    
                    clean_json = response.text.replace("```json", "").replace("```", "").strip()
                    ai_extracted = json.loads(clean_json)
                    st.success("🤖 Vision Scan Complete! Metadata extracted successfully.")
                    
                except Exception as e:
                    st.error(f"Neural Link Connection Failed: {e}")

            st.markdown("### 2. Auto-Populated Configuration Fields")
            with st.form("ai_form_parser"):
                s_name = st.text_input("Detected Object Class Name", value=str(ai_extracted.get("name", "")))
                col1, col2 = st.columns(2)
                s_brand = col1.text_input("Brand Node Identification Signature", value=str(ai_extracted.get("brand", "")))
                s_model = col2.text_input("Model Sequence Code", value=str(ai_extracted.get("model", "")))
                
                try: s_price_val = float(ai_extracted.get("price", 0.0))
                except: s_price_val = 0.0

                s_price = st.number_input("Valuation Metric (₹)", min_value=0.0, step=50.0, value=s_price_val)
                s_date = st.date_input("Purchase Data Acquisition DateStamp", datetime.today())
                
                if st.form_submit_button("Commit Node Data to Secure Partition"):
                    if s_name:
                        add_item(current_user, s_name, s_brand, s_model, s_price, str(s_date))
                        st.balloons()
                        st.success(f"Asset block '{s_name}' logged inside your KEEP-Stock vault.")
                        st.rerun()
                    else: 
                        st.warning("Validation failure: Row variables require an identified object Name target.")

    # --- MENU INTERACTION BLOCK C: MANUAL LOG ENTRY SHEET ---
    elif menu == "Manual Add":
        st.title("📝 Direct Manual Log Processing Matrix")
        with st.form("manual_entry_matrix"):
            m_name = st.text_input("Asset Identity Allocation")
            m_col1, m_col2 = st.columns(2)
            m_brand = m_col1.text_input("Brand Entity Classification")
            m_model = m_col2.text_input("Model Version Control Parameter")
            
            m_price = st.number_input("Acquisition Price Matrix (₹)", min_value=0.0, step=100.0)
            m_date = st.date_input("Transaction Log Date Value")
            
            if st.form_submit_button("Execute Table Injection"):
                if m_name:
                    add_item(current_user, m_name, m_brand, m_model, m_price, str(m_date))
                    st.success("Target manual entry record generated inside your private profile grid partition.")
                    st.rerun()
                else: st.error("Target requires at least an Object Name classification label.")

    # --- MENU INTERACTION BLOCK D: ADMINISTRATIVE ECOSYSTEM HUBSUIT ---
    elif menu == "👑 Admin Suite Control" and user_tier == "admin":
        st.title("👑 KEEP-Stock System Admin Control Hub")
        
        users_df = admin_fetch_users()
        global_master_df = admin_fetch_master_feed()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ecosystem User Accounts", len(users_df))
        with col2:
            st.metric("Total Shared Assets Tracked", len(global_master_df))
        with col3:
            global_sum = global_master_df['price'].sum() if not global_master_df.empty else 0
            st.metric("Ecosystem Capital Value", f"₹{global_sum:,.2f}")
            
        # --- TARGET ACCOUNT ISOLATION DESK ---
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.subheader("🔍 Individual Tenant Profile Workspace Audit Desk")
        
        if not users_df.empty:
            target_tenant = st.selectbox("Target a User Partition to Audit Database Separately", users_df['username'].tolist(), key="audit_select")
            
            tenant_isolated_dataset = get_user_items(target_tenant)
            st.write(f"Showing localized dashboard metrics mapped exclusively for: **{target_tenant}**")
            
            if not tenant_isolated_dataset.empty:
                audit_display_df = tenant_isolated_dataset.copy()
                audit_display_df.insert(0, 'Item No.', range(1, len(audit_display_df) + 1))
                audit_id_mapping = dict(zip(range(1, len(tenant_isolated_dataset) + 1), tenant_isolated_dataset['id'].tolist()))
                audit_display_df = audit_display_df.drop(columns=['id'])
                
                st.dataframe(audit_display_df, use_container_width=True)
                
                adm_del_c1, adm_del_c2 = st.columns([3,1])
                with adm_del_c1:
                    target_deletion_local_no = st.selectbox("Administrative Overrides: Choose Item No. to Prune", 
                                                           list(audit_id_mapping.keys()), key="admin_node_pruner_id")
                with adm_del_c2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="admin-btn">', unsafe_allow_html=True)
                    if st.button("FORCE DESTRUCT ENTRY"):
                        actual_system_db_id = audit_id_mapping[target_deletion_local_no]
                        delete_item(actual_system_db_id, target_tenant, global_override=True)
                        st.success("Administrative hard delete override completed successfully.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info(f"Target system client '{target_tenant}' has an empty workspace table data array.")
        else:
            st.write("No tenant data profiles found matching systemic parameters.")
        st.markdown("</div>", unsafe_allow_html=True)

        # --- DANGEROUS SYSTEM USER PURGE CONTROLLER ---
        st.markdown("<div class='custom-card' style='border: 1px solid rgba(255, 75, 43, 0.4);'>", unsafe_allow_html=True)
        st.subheader("💀 Dangerous Zone: System User Purge")
        st.write("Deleting a user removes their login profile and cascades a command to erase all database assets owned by them.")
        
        if not users_df.empty:
            purge_target = st.selectbox("Select User Account to Permanently Delete", users_df['username'].tolist(), key="purge_select")
            
            st.markdown('<div class="admin-btn">', unsafe_allow_html=True)
            confirm_purge = st.button(f"PERMANENTLY PURGE USER: '{purge_target.upper()}'")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if confirm_purge:
                admin_delete_user(purge_target)
                st.error(f"Account space '{purge_target}' and all its associated items have been automatically dropped.")
                st.rerun()
        else:
            st.info("No system user database paths available to clear.")
        st.markdown("</div>", unsafe_allow_html=True)

        # --- MASTER SYSTEM RESET CRITERIA BLOCK ---
        st.markdown("<div class='custom-card' style='border: 2px dashed #FF0000;'>", unsafe_allow_html=True)
        st.subheader("🚨 Extreme Danger: Complete System Wipe")
        st.write("This button drops all standard database profiles and clears every tracked inventory file globally across the system.")
        
        st.markdown('<div class="admin-btn">', unsafe_allow_html=True)
        nuke_triggered = st.button("EXECUTE COMPLETE DATA DELETE WIPE")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if nuke_triggered:
            admin_nuke_system()
            st.error("Ecosystem reset executed successfully. All users and datasets have been completely deleted.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        # --- GLOBAL MASTER STORAGE TABLE VIEW BLOCK ---
        st.subheader("🌐 Global Infrastructure Shared Core Master Table")
        if not global_master_df.empty:
            clean_master_df = global_master_df.copy()
            clean_master_df.insert(0, 'Index No.', range(1, len(clean_master_df) + 1))
            clean_master_df = clean_master_df.drop(columns=['id'])
            
            if 'price' in clean_master_df.columns:
                clean_master_df['price'] = clean_master_df['price'].apply(lambda x: f"₹{x:,.2f}" if x else "₹0.00")
                
            st.dataframe(clean_master_df, use_container_width=True)
        else:
            st.info("Global core datastream is completely unpopulated.")