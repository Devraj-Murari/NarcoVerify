"""
NarcoVerify — Digital Companion for Field Drug Testing
SIH prototype. Pure Python / Streamlit. No JavaScript or React needed.

Run with:  streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import hashlib
import os
import re
import secrets
from datetime import datetime, date
from PIL import Image
import numpy as np
import io

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
APP_NAME = "NarcoVerify"
DB_PATH = "test_records.db"
REFERENCE_IMAGES_DIR = os.path.join("images", "reference")
os.makedirs(REFERENCE_IMAGES_DIR, exist_ok=True)



TEST_STRIP_ROI = (0.35, 0.40, 0.65, 0.55)
REFERENCE_CARD_ROI = (0.05, 0.75, 0.30, 0.95)

REFERENCE_COLORS = {
    "positive": (200, 60, 60),
    "negative": (230, 230, 220),
}
CLASSIFY_DISTANCE_THRESHOLD = 60
INCONCLUSIVE_LABEL = "inconclusive"

# Reference chart: substance, street names, relative danger level, standard
# emergency response (antidote class / supportive care — no dosing detail),
# and the published presumptive colour-test reaction used to identify it.
# This mirrors standard field-test / harm-reduction reference charts.
DRUG_REFERENCE = [
    {"name": "Fentanyl", "street_names": "China White, M-30s, Apache, Dance Fever", "danger": "Extreme Danger", "treatment": "Naloxone (Narcan), airway support", "test_reaction": "Fentanyl Test Strip (FTS): 1 Red Line = Positive"},
    {"name": "Heroin", "street_names": "Smack, Horse, H, Junk, Brown Sugar", "danger": "Extreme Danger", "treatment": "Naloxone (Narcan), CPR", "test_reaction": "Marquis Reagent: Dark Purple / Violet"},
    {"name": "Morphine", "street_names": "Mister Blue, Dreamer, Morf, M", "danger": "High Danger", "treatment": "Naloxone (Narcan)", "test_reaction": "Marquis Reagent: Dark Purple / Violet"},
    {"name": "Oxycodone", "street_names": "Oxy, Percs, Kickers, 30s, Oxycontin", "danger": "High Danger", "treatment": "Naloxone (Narcan)", "test_reaction": "Marquis Reagent: Pale Violet to Yellow"},
    {"name": "Hydrocodone", "street_names": "Vikes, Norco, Hydros, Lorcet", "danger": "High Danger", "treatment": "Naloxone (Narcan)", "test_reaction": "Marquis Reagent: Light Brown to Violet"},
    {"name": "Codeine", "street_names": "Lean, Sizzurp, Cody, Purple Drank", "danger": "Moderate to High", "treatment": "Naloxone (Narcan)", "test_reaction": "Marquis Reagent: Very Dark Violet"},
    {"name": "Methadone", "street_names": "Methadose, Diskets, Fizzies", "danger": "High Danger", "treatment": "Naloxone (requires higher, continuous dosing)", "test_reaction": "Mecke Reagent: Pink / Light Red"},
    {"name": "Hydromorphone", "street_names": "Dilaudid, Dillies, Footballs", "danger": "Extreme Danger", "treatment": "Naloxone (Narcan)", "test_reaction": "Marquis Reagent: Yellow to Dark Violet"},
    {"name": "Carfentanil", "street_names": "Wildnil, Drop Dead", "danger": "Fatal Danger", "treatment": "Naloxone (multiple high-dose injections)", "test_reaction": "Specialized Ultra-Sensitive FTS / LC-MS/MS"},
    {"name": "Buprenorphine", "street_names": "Bupe, Sub, Subs, Suboxone", "danger": "Moderate Danger", "treatment": "Naloxone (partial reversal), supportive care", "test_reaction": "Marquis Reagent: Pink shift to Violet"},
    {"name": "Tramadol", "street_names": "Ultras, Trammies", "danger": "Moderate to High", "treatment": "Naloxone, Benzodiazepines (if seizures occur)", "test_reaction": "Marquis Reagent: Yellow / Orange"},
    {"name": "Nitazenes", "street_names": "Iso, Frankenstein, N-Pyrrolidino", "danger": "Extreme Danger", "treatment": "Naloxone (multiple doses required)", "test_reaction": "Specialized Strip / LC-MS/MS Lab testing"},
    {"name": "Powder Cocaine", "street_names": "Blow, Coke, Snow, Powder, Yayo", "danger": "High Danger", "treatment": "Benzodiazepines, cooling, cardiac support", "test_reaction": "Scott Reagent: Bright Blue"},
    {"name": "Crack Cocaine", "street_names": "Rock, Crack, Freebase, Base", "danger": "High to Extreme", "treatment": "Benzodiazepines, rapid cooling, oxygen", "test_reaction": "Scott Reagent: Bright Blue"},
    {"name": "Methamphetamine", "street_names": "Ice, Crystal, Glass, Speed, Crank", "danger": "High Danger", "treatment": "Benzodiazepines, aggressive cooling, sedatives", "test_reaction": "Marquis Reagent: Reddish-Orange to Dark Brown"},
    {"name": "Amphetamine", "street_names": "Addys, Speed, Bennies, Smart Pills", "danger": "Moderate to High", "treatment": "Benzodiazepines, hydration, cooling", "test_reaction": "Marquis Reagent: Yellow to Dark Orange"},
    {"name": "Methylphenidate", "street_names": "Kiddy Coke, Vitamin R, Smarties", "danger": "Moderate Danger", "treatment": "Benzodiazepines, supportive care", "test_reaction": "Marquis Reagent: Orange / Red"},
    {"name": "MDMA (Ecstasy)", "street_names": "Molly, E, XTC, Beans, Mandy", "danger": "High Danger", "treatment": "Rapid cooling, IV fluids, sedatives", "test_reaction": "Marquis Reagent: Dark Purple to Black"},
    {"name": "Synthetic Cathinones", "street_names": "Bath Salts, Flakka, Gravel", "danger": "Extreme Danger", "treatment": "Antipsychotics, heavy sedation, cooling", "test_reaction": "Marquis Reagent: Yellow to Red-Brown"},
    {"name": "Mephedrone", "street_names": "Meow Meow, M-Cat, Drone", "danger": "High Danger", "treatment": "Sedatives, cardiovascular monitoring", "test_reaction": "Marquis Reagent: Bright Yellow"},
    {"name": "Khat", "street_names": "Qat, Chat, African Salad, Miraa", "danger": "Low to Moderate", "treatment": "Rest, supportive care", "test_reaction": "TLC / GC-MS Lab testing"},
    {"name": "Alprazolam", "street_names": "Xannies, Bars, Zanies, Planks", "danger": "High Danger (w/ alcohol)", "treatment": "Flumazenil (hospital setting), airway support", "test_reaction": "Benzodiazepine Dip Strip: Zone line shift"},
    {"name": "Diazepam", "street_names": "Vs, Downers, Blue Vs, Valium", "danger": "Moderate to High", "treatment": "Flumazenil (hospital only), supportive care", "test_reaction": "Benzodiazepine Dip Strip: Zone line shift"},
    {"name": "Clonazepam", "street_names": "K-Pins, Pins, Klonies", "danger": "Moderate to High", "treatment": "Flumazenil, respiratory monitoring", "test_reaction": "Benzodiazepine Dip Strip: Zone line shift"},
    {"name": "Lorazepam", "street_names": "Atties, Control", "danger": "Moderate to High", "treatment": "Flumazenil, airway protection", "test_reaction": "Benzodiazepine Dip Strip: Zone line shift"},
    {"name": "Flunitrazepam", "street_names": "Roofies, Forget-Me Pill, Rope", "danger": "High Danger", "treatment": "Flumazenil, airway protection", "test_reaction": "Rohypnol Test Strip / Immunoassay"},
    {"name": "GHB", "street_names": "Liquid Ecstasy, Georgia Home Boy, G", "danger": "High Danger", "treatment": "Airway support, atropine (if bradycardia)", "test_reaction": "Cobalt Nitrate Test: Color shift"},
    {"name": "Phenobarbital", "street_names": "Downers, Barbs, Red Devils", "danger": "High Danger", "treatment": "Urinary alkalinization, charcoal, ventilation", "test_reaction": "Barbiturate Dip Card: Immunoassay shift"},
    {"name": "Zolpidem", "street_names": "A-Minus, Sleep-Easy, Zombie Pills", "danger": "Moderate Danger", "treatment": "Flumazenil, supportive care", "test_reaction": "Specialized Multi-Panel Urine Screen"},
    {"name": "Carisoprodol", "street_names": "Soma, Las Vegas Cocktail", "danger": "Moderate to High", "treatment": "Supportive care, mechanical ventilation", "test_reaction": "GC-MS / LC-MS Lab Analysis"},
    {"name": "Xylazine", "street_names": "Tranq, Zombie Drug, Sleep-Cut", "danger": "Extreme Danger", "treatment": "Naloxone (for mixed opioids), wound care", "test_reaction": "Xylazine Test Strip (XTS): 1 Line = Positive"},
    {"name": "LSD", "street_names": "Acid, Blotter, Lucy, Dots, Trips", "danger": "Moderate (Psychological)", "treatment": "Benzodiazepines, quiet environment", "test_reaction": "Ehrlich Reagent: Purple / Violet"},
    {"name": "Psilocybin", "street_names": "Magic Mushrooms, Shrooms, Mushies", "danger": "Low to Moderate", "treatment": "Benzodiazepines, supportive reassurance", "test_reaction": "Mecke Reagent: Green / Blue shift"},
    {"name": "DMT", "street_names": "Business Trip, Fantasy, Dimitri", "danger": "Moderate Danger", "treatment": "Quiet space, sedatives if panic occurs", "test_reaction": "Ehrlich Reagent: Purple / Violet"},
    {"name": "Mescaline", "street_names": "Peyote, Buttons, Mesc", "danger": "Low to Moderate", "treatment": "Benzodiazepines, supportive care", "test_reaction": "Marquis Reagent: Orange to Brown"},
    {"name": "2C-B", "street_names": "Nexus, Bees, Venus", "danger": "Moderate Danger", "treatment": "Benzodiazepines, quiet room", "test_reaction": "Marquis Reagent: Bright Green"},
    {"name": "Ayahuasca", "street_names": "Yage, Aya, The Tea, La Purga", "danger": "Low to Moderate", "treatment": "Reassurance, IV hydration", "test_reaction": "Advanced Lab Panel (DMT detection)"},
    {"name": "Salvia Divinorum", "street_names": "Sally D, Diviner's Sage, Magic Mint", "danger": "Moderate Danger", "treatment": "Injury prevention, calm space", "test_reaction": "TLC / GC-MS Lab confirmation"},
    {"name": "Ketamine", "street_names": "Special K, K, Kit Kat, Cat Valium", "danger": "Moderate to High", "treatment": "Supportive care, quiet monitoring", "test_reaction": "Morris Reagent: Violet / Blue"},
    {"name": "Phencyclidine (PCP)", "street_names": "Angel Dust, Wack, Embalming Fluid", "danger": "High Danger", "treatment": "Sedation (benzos), restraint, cooling", "test_reaction": "PCP Immunoassay Dip Card"},
    {"name": "Dextromethorphan", "street_names": "Robo, Skittles, Dex, Triple C", "danger": "Moderate Danger", "treatment": "Naloxone (at high overdose doses), cooling", "test_reaction": "Marquis Reagent: Grey to Black"},
    {"name": "Nitrous Oxide", "street_names": "Whippets, Hippie Crack, Laughing Gas", "danger": "Moderate Danger", "treatment": "Supplemental oxygen, Vitamin B12 therapy", "test_reaction": "Gas Chromatography (Headspace)"},
    {"name": "Cannabis (THC)", "street_names": "Weed, Pot, Mary Jane, Ganja, Herb", "danger": "Low Danger (Acute)", "treatment": "Time, reassurance, hydration", "test_reaction": "THC Immunoassay Strip / Fast Blue BB"},
    {"name": "Synthetic Cannabinoids", "street_names": "K2, Spice, Mr. Nice Guy, Genie", "danger": "High to Extreme", "treatment": "Antipsychotics, IV fluids, cooling", "test_reaction": "Synthetic Cannabinoid Strip / LC-MS"},
    {"name": "Hashish", "street_names": "Hash, Dope, Chocolate", "danger": "Low Danger", "treatment": "Supportive care, rest", "test_reaction": "Fast Blue BB Reagent: Dark Red / Purple"},
    {"name": "Kratom", "street_names": "Thang, Kakuam, Herbal Speedball", "danger": "Moderate Danger", "treatment": "Naloxone (for opioid-like toxicity)", "test_reaction": "LC-MS/MS Lab Analysis"},
    {"name": "Tianeptine", "street_names": "Gas Station Heroin, ZaZa, Tianaa", "danger": "High Danger", "treatment": "Naloxone, organ support", "test_reaction": "LC-MS/MS Lab Confirmation"},
    {"name": "Inhalant Solvents", "street_names": "Glue, Paint Thinner, Moon Gas", "danger": "High Danger (Sudden Death)", "treatment": "Pure oxygen, cardiac monitoring", "test_reaction": "Gas Chromatography (Blood/Breath)"},
    {"name": "Amyl Nitrite", "street_names": "Poppers, Rush, Snappers, Sub-Zero", "danger": "Moderate to High", "treatment": "Methylene Blue (for methemoglobinemia)", "test_reaction": "GC-MS Analysis"},
    {"name": "Ethanol", "street_names": "Alcohol, Booze, Hooch, Sauce", "danger": "High Danger (Overdose)", "treatment": "Thiamine, IV fluids, intubation if severe", "test_reaction": "Breathalyzer / Blood Alcohol Test"},
]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def render_location_picker():
    """Pure browser-JS GPS lookup — no extra pip package needed.
    Requires a secure context (localhost or https), same as the camera."""
    components.html(
        """
        <div style="font-family:sans-serif;font-size:13px;color:#AAB4C8;">
        <button id="geo-btn" style="border-radius:8px;border:1px solid #00E5B0;
            color:#00E5B0;background-color:transparent;padding:6px 14px;
            cursor:pointer;font-size:13px;">📍 Get my location</button>
        <div id="geo-result" style="margin-top:8px;"></div>
        </div>
        <script>
        const btn = document.getElementById('geo-btn');
        const out = document.getElementById('geo-result');

        btn.addEventListener('click', () => {
            if (!('geolocation' in navigator)) {
                out.innerHTML = "🚫 This browser has no geolocation support.";
                return;
            }
            out.innerHTML = "Requesting location…";
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude.toFixed(6);
                    const lon = pos.coords.longitude.toFixed(6);
                    out.innerHTML =
                        '✅ Latitude: <b>' + lat + '</b> &nbsp; Longitude: <b>' + lon + '</b>' +
                        '<br><span style="color:#5C6B8A;">Copy these into the Latitude / ' +
                        'Longitude fields below.</span>' +
                        '<br><button id="copy-btn" style="margin-top:6px;border-radius:6px;' +
                        'border:1px solid #1F2A44;background:#141B2D;color:#AAB4C8;' +
                        'padding:3px 10px;cursor:pointer;font-size:12px;">Copy "lat, lon"</button>';
                    document.getElementById('copy-btn').addEventListener('click', () => {
                        navigator.clipboard.writeText(lat + ', ' + lon);
                    });
                },
                (err) => {
                    if (err.code === err.PERMISSION_DENIED) {
                        out.innerHTML = "🚫 Location permission is blocked for this site. " +
                            "Click the lock/location icon in the address bar, allow " +
                            "Location, then click the button again.";
                    } else {
                        out.innerHTML = "Could not get a location: " + err.message;
                    }
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        });
        </script>
        """,
        height=90,
    )


def render_camera_permission_status():
    """Shows the browser's *actual* current camera permission for this site.
    If the widget below never prompts, it's almost always because this
    already says 'blocked' — the browser remembers a past decision and
    won't ask again on its own."""
    components.html(
        """
        <div id="cam-perm-status" style="font-family:sans-serif;font-size:13px;
             color:#AAB4C8;border:1px solid #1F2A44;border-radius:8px;
             padding:10px 14px;margin-bottom:10px;">
            Checking camera permission for this site…
        </div>
        <script>
        const el = document.getElementById('cam-perm-status');

        function render(state) {
            if (state === 'granted') {
                el.innerHTML = '✅ Camera permission is <b>granted</b> for this site. ' +
                    'If the widget still shows nothing, another app (Zoom, Teams, ' +
                    'another browser tab) may be holding the camera exclusively.';
            } else if (state === 'denied') {
                el.innerHTML = '🚫 Camera permission is <b>blocked</b> for this site — ' +
                    'that is why you never see a prompt. Click the camera/lock icon ' +
                    'in the address bar, set Camera to "Allow", then reload this page.';
            } else if (state === 'prompt') {
                el.innerHTML = '❔ No decision has been made yet. Click directly on the ' +
                    'camera widget below — that is what triggers the browser prompt.';
            } else {
                el.innerHTML = 'Could not read a permission state — try clicking the ' +
                    'camera widget below directly.';
            }
        }

        (async () => {
            try {
                if (navigator.permissions && navigator.permissions.query) {
                    const status = await navigator.permissions.query({ name: 'camera' });
                    render(status.state);
                    status.onchange = () => render(status.state);
                } else {
                    el.innerText = "This browser can't report permission status directly — " +
                        "try the camera widget below, or check the address-bar camera icon.";
                }
            } catch (e) {
                el.innerText = "This browser can't report permission status directly — " +
                    "try the camera widget below, or check the address-bar camera icon.";
            }
        })();
        </script>
        """,
        height=60,
    )


def danger_badge(danger_text: str):
    d = danger_text.lower()
    if "fatal" in d or "extreme" in d:
        color = "#FF4D4D"
    elif "high" in d:
        color = "#FF9F43"
    elif "moderate" in d:
        color = "#F5D547"
    elif "low" in d:
        color = "#4DD68C"
    else:
        color = "#888888"
    return f"""<span style="background:{color}22;color:{color};
        border:1px solid {color};padding:2px 10px;border-radius:999px;
        font-size:12px;font-weight:600;">{danger_text}</span>"""


# --------------------------------------------------------------------------
# DATABASE
# --------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            timestamp TEXT,
            operator_id TEXT,
            latitude TEXT,
            longitude TEXT,
            image_hash TEXT,
            record_signature TEXT,
            classification TEXT
        )
    """)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tests)").fetchall()]
    if "patient_id" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN patient_id TEXT DEFAULT ''")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            operator_id TEXT PRIMARY KEY,
            salt TEXT,
            password_hash TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_record(patient_id, operator_id, lat, lon, image_hash, signature, classification):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO tests
           (patient_id, timestamp, operator_id, latitude, longitude, image_hash,
            record_signature, classification)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, datetime.now().isoformat(timespec="seconds"), operator_id, lat, lon,
         image_hash, signature, classification),
    )
    conn.commit()
    conn.close()


def fetch_records(search_term="", result_filter="All", date_from=None, date_to=None):
    conn = sqlite3.connect(DB_PATH)
    query = (
        "SELECT id, patient_id, timestamp, operator_id, latitude, longitude, "
        "image_hash, record_signature, classification FROM tests WHERE 1=1"
    )
    params = []
    if search_term:
        query += " AND (patient_id LIKE ? OR CAST(id AS TEXT) LIKE ?)"
        params += [f"%{search_term}%", f"%{search_term}%"]
    if result_filter != "All":
        query += " AND classification = ?"
        params.append(result_filter)
    if date_from:
        query += " AND date(timestamp) >= date(?)"
        params.append(date_from.isoformat())
    if date_to:
        query += " AND date(timestamp) <= date(?)"
        params.append(date_to.isoformat())
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def clear_all_data():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()


# --------------------------------------------------------------------------
# AUTH (per-operator account, password chosen at signup)
# --------------------------------------------------------------------------
def hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


def operator_exists(operator_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT 1 FROM operators WHERE operator_id = ?", (operator_id,)).fetchone()
    conn.close()
    return row is not None


def create_operator(operator_id: str, password: str):
    salt_hex = secrets.token_hex(16)
    pw_hash = hash_password(password, salt_hex)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO operators (operator_id, salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (operator_id, salt_hex, pw_hash, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def verify_operator(operator_id: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT salt, password_hash FROM operators WHERE operator_id = ?", (operator_id,)
    ).fetchone()
    conn.close()
    if not row:
        return False
    salt_hex, stored_hash = row
    return hash_password(password, salt_hex) == stored_hash


# --------------------------------------------------------------------------
# IMAGE / CLASSIFICATION HELPERS
# --------------------------------------------------------------------------
def region_average_color(image: Image.Image, roi):
    w, h = image.size
    x1, y1, x2, y2 = int(roi[0]*w), int(roi[1]*h), int(roi[2]*w), int(roi[3]*h)
    crop = np.array(image.crop((x1, y1, x2, y2)).convert("RGB"))
    return tuple(crop.reshape(-1, 3).mean(axis=0))


def color_distance(c1, c2):
    return float(np.linalg.norm(np.array(c1) - np.array(c2)))


def classify_image(image: Image.Image):
    card_color = region_average_color(image, REFERENCE_CARD_ROI)
    strip_color = region_average_color(image, TEST_STRIP_ROI)
    best_label, best_dist = INCONCLUSIVE_LABEL, CLASSIFY_DISTANCE_THRESHOLD
    for label, ref_color in REFERENCE_COLORS.items():
        d = color_distance(strip_color, ref_color)
        if d < best_dist:
            best_label, best_dist = label, d
    return best_label, strip_color, card_color


def hash_image_bytes(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def make_record_signature(patient_id, operator_id, image_hash, classification, lat, lon, timestamp):
    payload = f"{timestamp}|{patient_id}|{operator_id}|{image_hash}|{classification}|{lat}|{lon}"
    return hashlib.sha256(payload.encode()).hexdigest()


# --------------------------------------------------------------------------
# THEME / STYLING
# --------------------------------------------------------------------------
def apply_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;600&display=swap');

        html, body, [class*="css"]  { font-family: 'Space Grotesk', sans-serif; }
        code, .stCode, pre { font-family: 'JetBrains Mono', monospace !important; }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        h1, h2, h3 { letter-spacing: 0.3px; }
        h1 { color: #00E5B0 !important; }

        section[data-testid="stSidebar"] {
            background-color: #0F1830;
            border-right: 1px solid #1F2A44;
        }

        div[data-testid="stExpander"] {
            border: 1px solid #1F2A44;
            border-radius: 10px;
            background-color: #141B2D;
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid #00E5B0;
            color: #00E5B0;
            background-color: transparent;
            transition: 0.15s ease-in-out;
        }
        .stButton > button:hover {
            background-color: #00E5B0;
            color: #0B1120;
        }

        .nv-card {
            background-color: #141B2D;
            border: 1px solid #1F2A44;
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }
        .nv-hero {
            background: linear-gradient(135deg, #0F1830 0%, #141B2D 100%);
            border: 1px solid #1F2A44;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# APP
# --------------------------------------------------------------------------
st.set_page_config(page_title=f"{APP_NAME} — Field Drug Test Companion", layout="centered", page_icon="🧪")
apply_theme()
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "operator_id" not in st.session_state:
    st.session_state.operator_id = ""

st.sidebar.markdown(f"### 🧪 {APP_NAME}")
page = st.sidebar.radio(
    "Navigate", ["Home", "Sign Up", "Login", "New Test", "Reference", "Log"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reload"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ Clear Data")
st.sidebar.caption("Permanently deletes ALL saved test records and images.")
confirm_clear = st.sidebar.checkbox("I understand this cannot be undone")
if st.sidebar.button("🗑️ Clear Data", disabled=not confirm_clear):
    clear_all_data()
    st.sidebar.success("All data cleared.")
    st.rerun()

# Pages that require login.
PROTECTED_PAGES = {"New Test", "Reference", "Log"}
if page in PROTECTED_PAGES and not st.session_state.logged_in:
    st.warning("Please log in first (see Login page in the sidebar).")
    st.stop()

# ---- HOME --------------------------------------------------------------
if page == "Home":
    st.markdown(
        f"""<div class="nv-hero">
        <h1 style="margin-bottom:0;">🧪 {APP_NAME}</h1>
        <p style="font-size:18px;color:#AAB4C8;margin-top:4px;">
        Digital Companion for Field Drug Testing</p>
        <p style="color:#CBD5E1;">NarcoVerify works alongside existing colorimetric
        field-test kits — no new hardware — to turn a subjective colour-change
        reading into a standardised, tamper-evident digital record.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("### What it does")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="nv-card"><b>📷 Capture</b><br><span style="color:#AAB4C8;">Photograph the test result with a reference colour card in frame.</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="nv-card"><b>🧬 Classify</b><br><span style="color:#AAB4C8;">Automatic positive / negative / inconclusive classification.</span></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="nv-card"><b>🔒 Log</b><br><span style="color:#AAB4C8;">Timestamp, GPS, operator ID and image hash — tamper-evident record.</span></div>', unsafe_allow_html=True)

    st.markdown("### Get started")
    st.write("New here? Create an account on **Sign Up**. Already have one? Head to **Login**.")

    st.markdown("---")
    st.caption(
        "⚠️ Output is a **presumptive** field-test result and supporting digital record. "
        "It does not replace laboratory confirmatory testing."
    )
    st.caption(f"Built for Smart India Hackathon · Team {APP_NAME}")

# ---- SIGN UP -------------------------------------------------------------
elif page == "Sign Up":
    st.title("Create Account")
    with st.form("signup_form"):
        new_op_id = st.text_input("Choose an Operator ID")
        new_password = st.text_input("Choose a Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Sign Up")
    if submitted:
        if not new_op_id.strip() or not new_password:
            st.error("Operator ID and password are required.")
        elif len(new_password) < 4:
            st.error("Password must be at least 4 characters.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        elif operator_exists(new_op_id.strip()):
            st.error("That Operator ID is already taken. Choose another or log in instead.")
        else:
            create_operator(new_op_id.strip(), new_password)
            st.success("Account created. Head to the Login page to sign in.")

# ---- LOGIN --------------------------------------------------------------
elif page == "Login":
    st.title("Operator Login")
    with st.form("login_form"):
        op_id = st.text_input("Operator ID", value=st.session_state.operator_id)
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")
    if submitted:
        if verify_operator(op_id.strip(), password):
            st.session_state.operator_id = op_id.strip()
            st.session_state.logged_in = True
            st.success(f"Logged in as {op_id.strip()}")
        else:
            st.error("Incorrect Operator ID or password. No account? Use Sign Up.")

# ---- NEW TEST -------------------------------------------------------------
elif page == "New Test":
    st.title("New Field Test")

    patient_id = st.text_input("Patient ID")

    st.caption("Tap the button to look up your GPS location, or enter it manually below.")
    render_location_picker()
    col1, col2 = st.columns(2)
    with col1:
        lat = st.text_input("Latitude", value="")
    with col2:
        lon = st.text_input("Longitude", value="")

    st.info(
        "Place the **reference colour card** in the bottom-left of frame and the "
        "**test strip** centred in frame, then capture."
    )

    render_camera_permission_status()

    photo = None
    try:
        photo = st.camera_input("Capture test result")
    except Exception as e:
        st.error(f"Camera could not be started: {e}")

    if photo is None:
        with st.expander("Camera not working?"):
            st.caption(
                "Browsers only allow camera access on a **secure connection** "
                "(`https://…` or `http://localhost`) and only after you accept the "
                "camera permission prompt for this site. If the widget above is "
                "blank or stuck, check the camera icon in your address bar, reload "
                "the page, or use the fallback upload below instead."
            )
            fallback = st.file_uploader(
                "Upload a photo of the test result instead", type=["png", "jpg", "jpeg"]
            )
            if fallback is not None:
                photo = fallback

    if photo is not None:
        if not patient_id.strip():
            st.warning("Enter a Patient ID before saving this record.")

        image_bytes = photo.getvalue()
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except Exception:
            st.error("Could not read that photo — please retake or re-upload it.")
            st.stop()

        classification, strip_color, card_color = classify_image(image)
        image_hash = hash_image_bytes(image_bytes)
        timestamp = datetime.now().isoformat(timespec="seconds")
        signature = make_record_signature(
            patient_id, st.session_state.operator_id, image_hash, classification, lat, lon, timestamp
        )

        badge_color = {"positive": "🔴", "negative": "🟢", INCONCLUSIVE_LABEL: "🟡"}
        st.subheader(f"{badge_color.get(classification, '⚪')} Result: {classification.upper()}")
        st.caption(
            "This is a presumptive field-test result and supporting digital record. "
            "It does not replace laboratory confirmatory testing."
        )
        st.code(f"Image hash: {image_hash}")
        st.code(f"Record signature: {signature}")

        if st.button("Confirm & Save Record", disabled=not patient_id.strip()):
            save_record(
                patient_id, st.session_state.operator_id, lat, lon,
                image_hash, signature, classification
            )
            st.success("Record saved to log.")

# ---- REFERENCE -------------------------------------------------------------
elif page == "Reference":
    st.title("Drug Reference Chart")
    st.caption(
        "Street names, relative danger level, standard emergency response, and the "
        "published presumptive colour-test reaction for each substance. For field "
        "identification support only — confirmatory lab testing is still required."
    )

    search = st.text_input("🔍 Search by substance or street name")
    entries = DRUG_REFERENCE
    if search:
        s = search.lower()
        entries = [
            d for d in DRUG_REFERENCE
            if s in d["name"].lower() or s in d["street_names"].lower()
        ]
    st.caption(f"{len(entries)} of {len(DRUG_REFERENCE)} substances shown")

    for drug in entries:
        st.markdown('<div class="nv-card">', unsafe_allow_html=True)
        slug = slugify(drug["name"])
        img_path = os.path.join(REFERENCE_IMAGES_DIR, f"{slug}.jpg")
        col_img, col_info = st.columns([1, 2])
        with col_img:
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.markdown(
                    """<div style="background:#0F1830;border:1px dashed #2A3654;
                    border-radius:8px;height:110px;display:flex;align-items:center;
                    justify-content:center;text-align:center;color:#5C6B8A;
                    font-size:12px;padding:8px;">No photo yet</div>""",
                    unsafe_allow_html=True,
                )
        with col_info:
            st.markdown(f"**{drug['name']}**")
            st.markdown(danger_badge(drug["danger"]), unsafe_allow_html=True)
            st.write(f"**Street names:** {drug['street_names']}")
            st.write(f"**Test reaction:** {drug['test_reaction']}")
            st.write(f"**Emergency response:** {drug['treatment']}")
        st.markdown("</div>", unsafe_allow_html=True)

# ---- LOG --------------------------------------------------------------
elif page == "Log":
    st.title("Test Log")

    if st.button("🔄 Reload"):
        st.rerun()

    search = st.text_input("Search by Patient ID or Test ID")

    col1, col2 = st.columns(2)
    with col1:
        result_filter = st.selectbox(
            "Result", ["All", "positive", "negative", INCONCLUSIVE_LABEL]
        )
    with col2:
        use_date_filter = st.checkbox("Filter by date")
    date_from, date_to = None, None
    if use_date_filter:
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            date_from = st.date_input("From", value=date.today())
        with dcol2:
            date_to = st.date_input("To", value=date.today())

    rows = fetch_records(search, result_filter, date_from, date_to)
    st.caption(f"{len(rows)} record(s) found")

    badge = {"positive": "🔴", "negative": "🟢", INCONCLUSIVE_LABEL: "🟡"}
    for r in rows:
        (rid, patient_id, ts, op, lat, lon, img_hash, sig, cls) = r
        label = f"{badge.get(cls, '⚪')} Test #{rid} — Patient {patient_id} — {cls.upper()} — {ts}"
        with st.expander(label):
            st.write(f"**Patient ID:** {patient_id}")
            st.write(f"**Operator:** {op}")
            st.write(f"**Timestamp:** {ts}")
            st.write(f"**Location:** {lat}, {lon}")
            st.code(f"Image hash: {img_hash}")
            st.code(f"Record signature: {sig}")
