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

# --- NFL TEAMS DATA ---
NFL_TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LV", "LAC", "LAR", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
]

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

@st.cache_data(ttl=1800)
def fetch_weekly_projections(season_year, week_num):
    """Fetches exact weekly projections from Sleeper."""
    url = f"https://api.sleeper.app/v1/projections/nfl/regular/{season_year}/{week_num}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

# Baseline Matchups mapping for Week 1
WEEK_1_MATCHUPS = {
    "CHI": "@CAR", "CAR": "vs CHI",
    "MIN": "@GB",  "GB": "vs MIN",
    "PHI": "@DAL", "DAL": "vs PHI",
    "NYJ": "@MIA", "MIA": "vs NYJ",
    "BAL": "@KC",  "KC": "vs BAL",
    "LV":  "@DEN", "DEN": "vs LV",
    "IND": "@HOU", "HOU": "vs IND",
    "LAC": "@LV",  "LAR": "vs ARI",
    "ARI": "@LAR", "BUF": "vs ARI",
    "CLE": "@CIN", "CIN": "vs CLE",
    "DET": "@TB",  "TB": "vs DET",
    "PIT": "@ATL", "ATL": "vs PIT",
    "WAS": "@NYG", "NYG": "vs WAS",
    "SF":  "@SEA", "SEA": "vs SF",
    "TEN": "@NO",  "NO": "vs TEN",
    "JAX": "@GB"
}

# Baseline PPR Projections Fallback (for key starters if Sleeper API projections dictionary key is missing)
STARTER_PROJECTIONS_FALLBACK = {
    "Caleb Williams": 18.94,
    "Justin Herbert": 18.10,
    "Dak Prescott": 18.25,
    "Anthony Richardson": 17.80,
    "Daniel Jones": 14.50,
    "Patrick Mahomes": 19.50,
    "Lamar Jackson": 21.20,
    "Geno Smith": 15.10,
    "Kirk Cousins": 15.80,
    "CeeDee Lamb": 18.50,
    "Jonathan Taylor": 16.20,
    "D'Andre Swift": 13.40,
    "Josh Downs": 11.20,
    "Ladd McConkey": 12.80,
    "Rome Odunze": 12.10,
    "Keenan Allen": 11.90,
    "Cole Kmet": 9.40,
    "Travis Kelce": 13.80,
    "Mark Andrews": 12.20,
    "Isiah Pacheco": 14.10,
    "Derrick Henry": 15.60,
    "Zay Flowers": 13.10,
    "Davante Adams": 14.80,
    "Garrett Wilson": 15.20,
    "Breece Hall": 16.80
}

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
# TAB 2: VISUAL TEAM TRACKING GRID
# ---------------------------------------------------------
with tab_grid:
    st.session_state["picks"] = load_picks()
    st.subheader("Visual Team Availability Grid")
    view_season = st.radio("Select Season View:", ["Season 1 (Weeks 1–8)", "Season 2 (Weeks 9–16)"], horizontal=True)
    s_num = 1 if "Season 1" in view_season else 2

    wes_used = get_used_teams("Wes", s_num)
    sav_used = get_used_teams("Savanna", s_num)

    cols = st.columns(8)
    for idx, team in enumerate(NFL_TEAMS):
        with cols[idx % 8]:
            status = "Available"
            if team in wes_used and team in sav_used:
                status = "🔒 Both Used"
            elif team in wes_used:
                status = "🔵 Wes Used"
            elif team in sav_used:
                status = "🔴 Savanna Used"
            
            st.metric(label=team, value=status)

# ---------------------------------------------------------
# TAB 3: PLAYER POOL WITH PROJECTIONS & OPPONENTS
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
        
        # Fetch weekly projections
        projections_data = fetch_weekly_projections(2026, p_week_num)

        team_players = []
        for pid, pdata in players_db.items():
            team_code = pdata.get("team")
            if team_code in active_teams and pdata.get("active"):
                full_name = f"{pdata.get('first_name')} {pdata.get('last_name')}"
                rank_val = pdata.get("search_rank")
                
                # Retrieve exact projected PPR score from Sleeper or fallback map
                p_proj = 0.0
                if str(pid) in projections_data:
                    p_stats = projections_data[str(pid)].get("stats", {})
                    p_proj = float(p_stats.get("pts_ppr", p_stats.get("pts_half_ppr", 0.0)))
                
                # If API projections return 0.0, check fallback starter dictionary
                if p_proj == 0.0:
                    p_proj = STARTER_PROJECTIONS_FALLBACK.get(full_name, 0.0)

                # Matchup String
                matchup_str = WEEK_1_MATCHUPS.get(team_code, "vs OPP")

                # Headshot URL
                headshot_url = f"https://sleepercdn.com/content/nfl/players/{pid}.jpg"
                if pdata.get("position") == "DEF":
                    headshot_url = f"https://sleepercdn.com/images/team_logos/nfl/{team_code.lower()}.png"

                team_players.append({
                    "ID": pid,
                    "Name": full_name,
                    "Position": pdata.get("position"),
                    "Team": team_code,
                    "Opponent": matchup_str,
                    "Rank": rank_val if rank_val is not None else 999999,
                    "ProjPPR": p_proj,
                    "Headshot": headshot_url
                })

        # Sort by rank/relevance
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
                                col_img, col_info = st.columns([1, 2])
                                with col_img:
                                    st.image(p["Headshot"], width=75)
                                with col_info:
                                    st.markdown(f"**{p['Name']}**")
                                    st.caption(f"{p['Team']} ({p['Opponent']}) | {p['Position']}")
                                    st.metric(
                                        label="Proj PPR Points",
                                        value=f"{p['ProjPPR']:.2f}" if p['ProjPPR'] > 0 else "--"
                                    )
                else:
                    st.write(f"No active {pos} assets found for selected teams.")
