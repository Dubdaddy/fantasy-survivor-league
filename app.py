import streamlit as st
import json
import os
import random
import time
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="2-Player Team Survivor League",
    layout="wide",
    page_icon="🏈"
)

# --- INJECT CUSTOM CSS FOR CARD HEADSHOTS ---
st.markdown("""
    <style>
    .player-card {
        display: flex;
        background-color: #f9f9fb;
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 12px;
        height: 110px;
    }
    .player-img-container {
        width: 35%;
        background-color: #eef2f5;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .player-img-container img {
        height: 100%;
        width: 100%;
        object-fit: cover;
    }
    .player-info-container {
        width: 65%;
        padding: 10px 14px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .player-name {
        font-weight: 700;
        font-size: 15px;
        color: #1f2937;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .player-meta {
        font-size: 12px;
        color: #6b7280;
        margin-bottom: 4px;
    }
    .player-stat-val {
        font-size: 20px;
        font-weight: 800;
        color: #111827;
        line-height: 1;
    }
    .player-stat-lbl {
        font-size: 10px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- ESPN LOGO MAPPING ---
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

# --- BASELINE PROJECTIONS MAP ---
DEFAULT_PROJECTIONS = {
    "Caleb Williams": 18.94,
    "Justin Herbert": 18.10,
    "Dak Prescott": 18.25,
    "Anthony Richardson": 17.80,
    "Daniel Jones": 14.50,
    "Joe Milton": 5.20,
    "Tyson Bagent": 4.10,
    "Riley Leonard": 6.30,
    "DJ Uiagalelei": 5.00,
    "Patrick Mahomes": 19.80,
    "Lamar Jackson": 21.20,
    "Geno Smith": 15.10,
    "Kirk Cousins": 15.80,
    "Jonathan Taylor": 18.70,
    "D'Andre Swift": 13.40,
    "Omarion Hampton": 11.20,
    "Javonte Williams": 12.10,
    "CeeDee Lamb": 18.50,
    "Amon-Ra St. Brown": 16.30,
    "Josh Downs": 11.20,
    "Ladd McConkey": 12.80,
    "Rome Odunze": 12.10,
    "Keenan Allen": 11.90,
    "Cole Kmet": 9.40,
    "Travis Kelce": 13.80,
    "Mark Andrews": 12.20
}

# --- LOGIN CREDENTIALS ---
USERS = {
    "Wes": "wes123",        
    "Savanna": "sav123"
}

# --- PERSISTENT FILE STORAGE ---
DATA_FILE = "picks.json"

def load_picks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "Wes": {f"Week {w}": [] for w in range(1, 17)},
        "Savanna": {f"Week {w}": [] for w in range(1, 17)}
    }

def save_picks(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- INITIALIZE SESSION STATE ---
if "user" not in st.session_state:
    st.session_state["user"] = None

if "picks" not in st.session_state:
    st.session_state["picks"] = load_picks()

# --- HELPER FUNCTIONS ---
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
# TAB 3: SORTED PLAYER POOL WITH FULL-BLEED HEADSHOTS
# ---------------------------------------------------------
with tab_players:
    st.session_state["picks"] = load_picks()
    st.subheader("Active Weekly Player Pool")
    p_week_str = st.selectbox("View Player Pool for Week:", [f"Week {w}" for w in range(1, 17)], key="p_week")
    p_user = st.radio("Select Manager Roster:", ["Wes", "Savanna"], horizontal=True)

    active_teams = st.session_state["picks"][p_user][p_week_str]

    if not active_teams:
        st.info(f"{p_user} has not locked in picks for {p_week_str} yet.")
    else:
        st.caption(f"Showing top players for **{p_user}**'s teams: **{', '.join(active_teams)}**")

        team_players = []
        for pid, pdata in players_db.items():
            team_code = pdata.get("team")
            if team_code in active_teams and pdata.get("active"):
                full_name = f"{pdata.get('first_name')} {pdata.get('last_name')}".strip()
                
                # Projection calculation
                p_proj = DEFAULT_PROJECTIONS.get(full_name, 0.00)

                headshot_url = f"https://sleepercdn.com/content/nfl/players/{pid}.jpg"
                if pdata.get("position") == "DEF":
                    headshot_url = f"https://sleepercdn.com/images/team_logos/nfl/{team_code.lower()}.png"

                team_players.append({
                    "ID": pid,
                    "Name": full_name,
                    "Position": pdata.get("position"),
                    "Team": team_code,
                    "ProjPPR": p_proj,
                    "Headshot": headshot_url
                })

        # --- SORT BY PROJECTED PPR POINTS DESCENDING ---
        team_players = sorted(team_players, key=lambda x: x["ProjPPR"], reverse=True)

        # Calculate Total Team Top Projections
        total_top_proj = sum(p["ProjPPR"] for p in team_players[:10])
        st.metric(label=f"Total Top 10 Projected Starters ({p_user})", value=f"{total_top_proj:.2f} PPR pts")

        pos_tabs = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
        positions = ["QB", "RB", "WR", "TE", "K", "DEF"]

        for idx, pos in enumerate(positions):
            with pos_tabs[idx]:
                filtered = [p for p in team_players if p["Position"] == pos][:12]
                if filtered:
                    p_cols = st.columns(3)
                    for i, p in enumerate(filtered):
                        with p_cols[i % 3]:
                            # Render Full-Bleed Headshot Card
                            val_display = f"{p['ProjPPR']:.2f}" if p['ProjPPR'] > 0 else "--"
                            card_html = f"""
                            <div class="player-card">
                                <div class="player-img-container">
                                    <img src="{p['Headshot']}" alt="{p['Name']}">
                                </div>
                                <div class="player-info-container">
                                    <div class="player-name">{p['Name']}</div>
                                    <div class="player-meta">{p['Team']} ({p_week_str}) | {p['Position']}</div>
                                    <div class="player-stat-val">{val_display}</div>
                                    <div class="player-stat-lbl">Proj PPR Points</div>
                                </div>
                            </div>
                            """
                            st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.write(f"No active {pos} assets found for selected teams.")
