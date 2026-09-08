import streamlit as st
import json
import os
import random
import time
import requests
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="2-Player Team Survivor League",
    layout="wide",
    page_icon="🏈"
)

# --- INJECT CUSTOM CSS FOR HEADSHOT FRAMING ---
st.markdown("""
    <style>
    /* Headshot framing */
    div[data-testid="stColumn"] img {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        background-color: #f8f9fa;
        padding: 4px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        object-fit: cover;
        width: 100% !important;
        max-width: 115px !important;
    }
    
    /* Vertically center content inside cards */
    div[data-testid="stContainer"] > div {
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- PERSISTENT CLOUD STORAGE CONFIGURATION (JSONBIN & FANTASYPROS) ---
JSONBIN_BIN_ID = st.secrets.get("JSONBIN_BIN_ID", "6a9ef978ffd5d16053ea44d8")
JSONBIN_API_KEY = st.secrets.get("JSONBIN_API_KEY", "$2a$10$Ag5xmAzaVFlgJZyw.WrG8u5sSq8QvEI3yxcRsT9ifO835MLfTRhDu")
FP_API_KEY = st.secrets.get("FANTASYPROS_API_KEY", "oBmWgMxsyo7X9SminwGJGaxYd5sNH3Sg1aYqpaW8")

HEADERS_JSONBIN = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY
}

def load_picks():
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    try:
        response = requests.get(url, headers=HEADERS_JSONBIN, timeout=10)
        if response.status_code == 200:
            return response.json().get("record", {})
    except Exception as e:
        st.error(f"Error loading picks from cloud: {e}")
    
    return {
        "Wes": {f"Week {w}": [] for w in range(1, 17)},
        "Savanna": {f"Week {w}": [] for w in range(1, 17)}
    }

def save_picks(data):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    try:
        response = requests.put(url, json=data, headers=HEADERS_JSONBIN, timeout=10)
        if response.status_code == 200:
            return True
    except Exception as e:
        st.error(f"Error saving picks to cloud: {e}")
    return False

# --- NFL DIVISIONS DATA ---
DIVISIONS = {
    "AFC": {
        "East": ["BUF", "MIA", "NE", "NYJ"],
        "North": ["BAL", "CIN", "CLE", "PIT"],
        "South": ["HOU", "IND", "JAX", "TEN"],
        "West": ["DEN", "KC", "LV", "LAC"]
    },
    "NFC": {
        "East": ["DAL", "NYG", "PHI", "WAS"],
        "North": ["CHI", "DET", "GB", "MIN"],
        "South": ["ATL", "CAR", "NO", "TB"],
        "West": ["ARI", "LAR", "SF", "SEA"]
    }
}

NFL_TEAMS = [team for conf in DIVISIONS.values() for div in conf.values() for team in div]

# --- ESPN TEAM LOGO URL MAPPING ---
ESPN_LOGOS = {
    "ARI": "ari", "ATL": "atl", "BAL": "bal", "BUF": "buf",
    "CAR": "car", "CHI": "chi", "CIN": "cin", "CLE": "cle",
    "DAL": "dal", "DEN": "den", "DET": "det", "GB": "gb",
    "HOU": "hou", "IND": "ind", "JAX": "jax", "KC": "kc",
    "LV": "lv",   "LAC": "lac", "LAR": "lar", "MIA": "mia",
    "MIN": "min", "NE": "ne",   "NO": "no",   "NYG": "nyg",
    "NYJ": "nyj", "PHI": "phi", "PIT": "pit", "SEA": "sea",
    "SF": "sf",   "TB": "tb",   "TEN": "ten", "WAS": "was"
}

# --- 2026 WEEK 1 MATCHUP SCHEDULE ---
WEEK_1_MATCHUPS = {
    "NE": "@ SEA", "SEA": "vs NE",
    "SF": "@ LAR", "LAR": "vs SF",
    "CHI": "@ CAR", "CAR": "vs CHI",
    "TB": "@ CIN", "CIN": "vs TB",
    "NO": "@ DET", "DET": "vs NO",
    "BUF": "@ HOU", "HOU": "vs BUF",
    "BAL": "@ IND", "IND": "vs BAL",
    "CLE": "@ JAX", "JAX": "vs CLE",
    "ATL": "@ PIT", "PIT": "vs ATL",
    "NYJ": "@ TEN", "TEN": "vs NYJ",
    "ARI": "@ LAC", "LAC": "vs ARI",
    "MIA": "@ LV", "LV": "vs MIA",
    "GB": "@ MIN", "MIN": "vs GB",
    "WAS": "@ PHI", "PHI": "vs WAS",
    "DAL": "@ NYG", "NYG": "vs DAL",
    "DEN": "@ KC", "KC": "vs DEN"
}

# --- LOGIN CREDENTIALS ---
USERS = {
    "Wes": "wes123",        
    "Savanna": "sav123"
}

# --- INITIALIZE SESSION STATE ---
if "user" not in st.session_state:
    st.session_state["user"] = None

if "picks" not in st.session_state:
    st.session_state["picks"] = load_picks()

# --- HELPER FUNCTIONS ---
def clean_name(name):
    """Normalize names by removing suffixes, punctuation, and extra spaces."""
    if not name:
        return ""
    name = re.sub(r"[.'\"-]", "", name)
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name, flags=re.IGNORECASE)
    return " ".join(name.lower().split())

def get_used_teams(player, season=1):
    weeks = range(1, 9) if season == 1 else range(9, 17)
    used = []
    for w in weeks:
        used.extend(st.session_state["picks"][player][f"Week {w}"])
    return used

@st.cache_data(ttl=3600)
def fetch_nfl_players():
    url = "https://api.sleeper.app/v1/players/nfl"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

@st.cache_data(ttl=1800)
def fetch_nfl_state():
    url = "https://api.sleeper.app/v1/state/nfl"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"season": "2026", "week": 1}

@st.cache_data(ttl=300)
def fetch_fp_projections_v3(week_num):
    """Loops across positions to build a complete FantasyPros projection list."""
    url = "https://api.fantasypros.com/public/v2/json/nfl/2026/projections"
    headers = {"x-api-key": FP_API_KEY}
    positions = ["QB", "RB", "WR", "TE", "K", "DST"]
    all_players = []

    for pos in positions:
        params = {"scoring": "PPR", "week": week_num, "position": pos}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    all_players.extend(data)
                elif isinstance(data, dict):
                    if "players" in data and isinstance(data["players"], list):
                        all_players.extend(data["players"])
                    elif "projections" in data and isinstance(data["projections"], list):
                        all_players.extend(data["projections"])
        except Exception:
            continue
    return all_players

players_db = fetch_nfl_players()

# --- SIDEBAR LOGIN ---
st.sidebar.title("🔐 League Login")
if st.session_state["user"] is None:
    user_select = st.sidebar.selectbox("Select User", ["-- Select --"] + list(USERS.keys()))
    password_input = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Log In"):
        if user_select in USERS and USERS[user_select] == password_input:
            st.session_state["user"] = user_select
            st.sidebar.success(f"Welcome, {user_select}!")
            st.rerun()
        else:
            st.sidebar.error("Incorrect password.")
else:
    st.sidebar.write(f"Logged in as: **{st.session_state['user']}**")
    if st.sidebar.button("Log Out"):
        st.session_state["user"] = None
        st.rerun()

# --- HEADER ---
st.title("🏈 2-Player Team Survivor & Player Pool League")
st.markdown("Track used teams, execute Tuesday drafts, spin for Week 8/16 leftovers, and view active player rosters.")

# --- DASHBOARD TABS ---
tab_draft, tab_grid, tab_players = st.tabs(["🎯 Tuesday Draft Center", "📊 Team Tracking Grid", "⚡ Active Player Pool"])

# ---------------------------------------------------------
# TAB 1: DRAFT CENTER
# ---------------------------------------------------------
with tab_draft:
    st.session_state["picks"] = load_picks()
    
    current_user = st.session_state.get("user")
    if not current_user:
        st.info("👈 Please log in on the sidebar to make your weekly selections.")
    else:
        selected_week = st.selectbox("Select Week", [f"Week {w}" for w in range(1, 17)])
        week_num = int(selected_week.split()[1])
        season = 1 if week_num <= 8 else 2

        first_picker = "Savanna" if week_num % 2 != 0 else "Wes"
        st.caption(f"📢 First Pick Priority for {selected_week}: **{first_picker}**")

        used_by_me = get_used_teams(current_user, season)
        opponent = "Savanna" if current_user == "Wes" else "Wes"
        opp_picks_this_week = st.session_state["picks"][opponent][selected_week]

        my_current_picks = st.session_state["picks"][current_user][selected_week]
        used_other_weeks = [t for t in used_by_me if t not in my_current_picks]

        available_teams = sorted(list(set([t for t in NFL_TEAMS if t not in used_other_weeks and t not in opp_picks_this_week] + my_current_picks)))

        st.subheader(f"{current_user}'s Draft Room ({selected_week})")

        # Standard Selection
        if len(available_teams) >= 4:
            valid_defaults = [t for t in my_current_picks if t in available_teams]
            
            my_selection = st.multiselect(
                "Select 4 Teams for this week:",
                options=available_teams,
                default=valid_defaults,
                max_selections=4
            )
            if st.button("🔒 Save Weekly Picks"):
                if len(my_selection) == 4:
                    st.session_state["picks"][current_user][selected_week] = my_selection
                    save_picks(st.session_state["picks"])
                    st.success(f"Picks locked in and saved for {selected_week}: {', '.join(my_selection)}")
                    st.rerun()
                else:
                    st.warning("Please select exactly 4 teams.")

        # Week 8 / 16 Wheel Spin Trigger
        else:
            st.warning(f"Only {len(available_teams)} fresh team(s) remaining for selection in Season {season}!")
            valid_defaults = [t for t in my_current_picks if t in available_teams]
            
            my_selection = st.multiselect(
                "Select available fresh team(s):",
                options=available_teams,
                default=valid_defaults
            )

            wheel_pool = [t for t in NFL_TEAMS if t not in my_selection and t not in opp_picks_this_week]

            if len(my_selection) < 4 and wheel_pool:
                st.markdown("### 🎡 Leftover Team Wheel Spin")
                st.write("Spin the wheel to select your remaining team slot!")
                if st.button("🎰 SPIN THE WHEEL"):
                    with st.spinner("Spinning the wheel..."):
                        time.sleep(1.5)
                        spun_team = random.choice(wheel_pool)
                        my_selection.append(spun_team)
                        st.session_state["picks"][current_user][selected_week] = my_selection
                        save_picks(st.session_state["picks"])
                        st.balloons()
                        st.success(f"🎉 The wheel landed on: **{spun_team}**!")
                        st.rerun()

# ---------------------------------------------------------
# TAB 2: AFC/NFC DIVISIONAL TEAM TRACKING GRID
# ---------------------------------------------------------
with tab_grid:
    st.session_state["picks"] = load_picks()
    st.subheader("Visual Team Availability Grid")
    
    view_season = st.radio("Select Season View:", ["Season 1 (Weeks 1–8)", "Season 2 (Weeks 9–16)"], horizontal=True)
    s_num = 1 if "Season 1" in view_season else 2

    wes_used = get_used_teams("Wes", s_num)
    sav_used = get_used_teams("Savanna", s_num)

    conf_afc, conf_nfc = st.columns(2)

    for conf_name, conf_col in [("AFC", conf_afc), ("NFC", conf_nfc)]:
        with conf_col:
            st.markdown(f"### {conf_name}")
            div_cols = st.columns(4)
            divisions = ["East", "North", "South", "West"]
            
            for idx, div_name in enumerate(divisions):
                with div_cols[idx]:
                    st.markdown(f"**{div_name}**")
                    teams_in_div = DIVISIONS[conf_name][div_name]
                    
                    for team in teams_in_div:
                        logo_code = ESPN_LOGOS.get(team, team.lower())
                        logo_url = f"https://a.espncdn.com/i/teamlogos/nfl/500/{logo_code}.png"
                        
                        # Determine pick status
                        if team in wes_used and team in sav_used:
                            badge = "🔒 Both"
                        elif team in wes_used:
                            badge = "🔵 Wes"
                        elif team in sav_used:
                            badge = "🔴 Savanna"
                        else:
                            badge = "🟢 Available"

                        with st.container(border=True):
                            c_img, c_lbl = st.columns([1, 2])
                            with c_img:
                                st.image(logo_url, width=40)
                            with c_lbl:
                                st.markdown(f"**{team}**")
                                st.caption(badge)

# ---------------------------------------------------------
# TAB 3: LIVE PLAYER POOL & PROJECTIONS
# ---------------------------------------------------------
with tab_players:
    st.session_state["picks"] = load_picks()
    st.subheader("Active Weekly Player Pool")
    p_week_str = st.selectbox("View Player Pool for Week:", [f"Week {w}" for w in range(1, 17)], key="p_week")
    p_week_num = int(p_week_str.split()[1])
    p_user = st.radio("Select Manager Roster:", ["Wes", "Savanna"], horizontal=True)

    active_teams = st.session_state["picks"][p_user][p_week_str]

    if not active_teams:
        st.info(f"{p_user} has not locked in picks for {p_week_str} yet.")
    else:
        st.caption(f"Showing top players for **{p_user}**'s teams: **{', '.join(active_teams)}**")
        
        # Fetch directly using position loops & refreshed cache
        fp_projections = fetch_fp_projections_v3(p_week_num)

        team_players = []
        for pid, pdata in players_db.items():
            team_code = pdata.get("team")
            if team_code in active_teams and pdata.get("active"):
                raw_full_name = f"{pdata.get('first_name')} {pdata.get('last_name')}"
                norm_full_name = clean_name(raw_full_name)
                rank_val = pdata.get("search_rank")
                
                p_proj = 0.0
                p_avg = 0.0
                
                if isinstance(fp_projections, list):
                    match = next(
                        (item for item in fp_projections if clean_name(item.get("name")) == norm_full_name or clean_name(item.get("player_name")) == norm_full_name),
                        None
                    )
                    if match:
                        stats = match.get("stats", {})
                        if isinstance(stats, dict):
                            raw_pts = stats.get("points_ppr") or stats.get("points") or match.get("fpts") or 0.0
                            try:
                                p_proj = float(raw_pts)
                            except (ValueError, TypeError):
                                p_proj = 0.0

                headshot_url = f"https://sleepercdn.com/content/nfl/players/{pid}.jpg"
                if pdata.get("position") == "DEF":
                    headshot_url = f"https://sleepercdn.com/images/team_logos/nfl/{team_code.lower()}.png"

                depth_order = pdata.get("depth_chart_order")
                depth_str = f"{pdata.get('position')}{depth_order}" if depth_order else pdata.get("position")

                opp_matchup = WEEK_1_MATCHUPS.get(team_code, "")
                team_opp_str = f"{team_code} {opp_matchup}".strip()

                injury_status = pdata.get("injury_status")
                status_str = "Healthy" if not injury_status else str(injury_status).capitalize()

                team_players.append({
                    "ID": pid,
                    "Name": raw_full_name,
                    "Position": pdata.get("position"),
                    "DepthRole": depth_str,
                    "TeamMatchup": team_opp_str,
                    "Team": team_code,
                    "Rank": rank_val if rank_val is not None else 999999,
                    "ProjPPR": p_proj,
                    "AvgPPR": p_avg,
                    "Headshot": headshot_url,
                    "Status": status_str
                })

        team_players = sorted(team_players, key=lambda x: x["Rank"])

        pos_tabs = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
        positions = ["QB", "RB", "WR", "TE", "K", "DEF"]

        for idx, pos in enumerate(positions):
            with pos_tabs[idx]:
                filtered = [p for p in team_players if p["Position"] == pos][:12]
                if filtered:
                    p_cols = st.columns(3)
                    for i, p in enumerate(filtered):
                        with p_cols[i % 3]:
                            with st.container(border=True):
                                col_img, col_info = st.columns([1, 1.4])
                                with col_img:
                                    st.image(p["Headshot"], width=115)
                                    
                                    if p["Status"] == "Healthy":
                                        st.caption(f"🟢 **{p['Status']}**")
                                    elif p["Status"] in ["Questionable", "Doubtful"]:
                                        st.caption(f"🟡 **{p['Status']}**")
                                    else:
                                        st.caption(f"🔴 **{p['Status']}**")

                                with col_info:
                                    st.markdown(f"**{p['Name']}**")
                                    st.caption(f"{p['TeamMatchup']} | **{p['DepthRole']}**")
                                    
                                    m1, m2 = st.columns(2)
                                    with m1:
                                        st.metric(
                                            label="Proj PPR",
                                            value=f"{p['ProjPPR']:.2f}" if p['ProjPPR'] > 0 else "0.00"
                                        )
                                    with m2:
                                        st.metric(
                                            label="Avg PPR",
                                            value=f"{p['AvgPPR']:.2f}" if p['AvgPPR'] > 0 else "0.00"
                                        )
                else:
                    st.write(f"No active {pos} found for selected teams.")
