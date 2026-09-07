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
    url = f"https://api.sleeper.app/v1/projections/nfl/regular/{season_year}/{week_num}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

@st.cache_data(ttl=3600)
def fetch_season_stats(season_year):
    url = f"https://api.sleeper.app/v1/stats/nfl/regular/{season_year}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

def calculate_ppr_points(stats_dict):
    """Calculates PPR points manually if precomputed pts_ppr is absent."""
    if not stats_dict:
        return 0.0
    if "pts_ppr" in stats_dict:
        return float(stats_dict["pts_ppr"])
    
    # Manual PPR calculation
    pts = 0.0
    pts += float(stats_dict.get("pass_yd", 0)) * 0.04
    pts += float(stats_dict.get("pass_td", 0)) * 4.0
    pts -= float(stats_dict.get("pass_int", 0)) * 2.0
    pts += float(stats_dict.get("rush_yd", 0)) * 0.1
    pts += float(stats_dict.get("rush_td", 0)) * 6.0
    pts += float(stats_dict.get("rec", 0)) * 1.0
    pts += float(stats_dict.get("rec_yd", 0)) * 0.1
    pts += float(stats_dict.get("rec_td", 0)) * 6.0
    return round(pts, 1)

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

        # Alternating First Pick
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
# TAB 3: PLAYER POOL WITH PROJECTIONS & APPG
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
        
        # Fetch weekly projections & season stats
        projections_data = fetch_weekly_projections(2026, p_week_num)
        season_stats_data = fetch_season_stats(2025) # Default/Prior baseline stats

        team_players = []
        for pid, pdata in players_db.items():
            if pdata.get("team") in active_teams and pdata.get("active"):
                rank_val = pdata.get("search_rank")
                
                # Projections Calculation
                proj_dict = projections_data.get(pid, {}).get("stats", {})
                proj_ppr = calculate_ppr_points(proj_dict)

                # Average Points Per Game (APPG) Calculation
                season_dict = season_stats_data.get(pid, {}).get("stats", {})
                total_season_pts = calculate_ppr_points(season_dict)
                games_played = float(season_dict.get("gp", 1.0))
                appg = round(total_season_pts / games_played, 1) if games_played > 0 else 0.0

                # Headshot Image URL
                headshot_url = f"https://sleepercdn.com/content/nfl/players/{pid}.jpg"
                if pdata.get("position") == "DEF":
                    headshot_url = f"https://sleepercdn.com/images/team_logos/nfl/{pdata.get('team').lower()}.png"

                team_players.append({
                    "ID": pid,
                    "Name": f"{pdata.get('first_name')} {pdata.get('last_name')}",
                    "Position": pdata.get("position"),
                    "Team": pdata.get("team"),
                    "Rank": rank_val if rank_val is not None else 999999,
                    "ProjPPR": proj_ppr,
                    "APPG": appg,
                    "Headshot": headshot_url
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
                                col_img, col_info = st.columns([1, 2])
                                with col_img:
                                    st.image(p["Headshot"], width=75)
                                with col_info:
                                    st.markdown(f"**{p['Name']}**")
                                    st.caption(f"{p['Team']} | {p['Position']}")
                                    
                                    m_col1, m_col2 = st.columns(2)
                                    with m_col1:
                                        st.metric(
                                            label="Proj PPR",
                                            value=f"{p['ProjPPR']:.1f}" if p['ProjPPR'] > 0 else "--"
                                        )
                                    with m_col2:
                                        st.metric(
                                            label="APPG",
                                            value=f"{p['APPG']:.1f}" if p['APPG'] > 0 else "--"
                                        )
                else:
                    st.write(f"No active {pos} assets found for selected teams.")
