import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from unidecode import unidecode
import os

# ====================================================================
# FILE PATHS
# ====================================================================
EVENTS_FILE_PATH = r"D:\pass net\EventData.csv"
PLAYERS_FILE_PATH = r"D:\pass net\PlayerData.csv"
# ====================================================================
# STREAMLIT APP
# ====================================================================
# ... بقية الكود كما هو ...
st.set_page_config(page_title="Football Pass Dashboard", layout="wide")
st.title("⚽ Football Pass Dashboard")

@st.cache_data
def load_data(events_path, players_path):
    if not os.path.exists(events_path) or not os.path.exists(players_path):
        st.error(f"❌ Files not found. Please check the paths:\n\n- Events: {events_path}\n- Players: {players_path}")
        return None, None, None, []

    df = pd.read_csv(events_path)
    dfp = pd.read_csv(players_path)

    passes = df[df["type"] == "Pass"].copy()
    passes["passRecipientId"] = passes["relatedPlayerId"]

    passes = passes.merge(
        dfp[["playerId", "name"]].rename(columns={"playerId": "passRecipientId", "name": "recipientName"}),
        on="passRecipientId", how="left"
    )

    teams = sorted(df["teamName"].dropna().unique())
    return df, dfp, passes, teams

df, dfp, passes, teams = load_data(EVENTS_FILE_PATH, PLAYERS_FILE_PATH)

if df is None:
    st.stop()

# Sidebar
selected_team = st.sidebar.selectbox("🏟️ Choose Team", ["Select Team"] + teams)

if selected_team != "Select Team":
    # فلترة تمريرات الفريق
    team_passes = passes[passes["teamName"] == selected_team]

    # تمريرات ناجحة فقط
    team_passes = team_passes[
        (team_passes["type"] == "Pass") &
        (team_passes["outcomeType"] == "Successful")
    ]

    players = sorted(team_passes["playerName"].dropna().unique())
    player_choice = st.sidebar.selectbox("👤 Choose Player", ["— Pass Network (Whole Team) —"] + players)

    # ========================
    # PASS NETWORK (TEAM)
    # ========================
    if player_choice == "— Pass Network (Whole Team) —":
        st.subheader(f"🔗 Pass Network — {selected_team}")

        team_passes = team_passes.sort_values(["expandedMinute", "second"]).reset_index(drop=True)

        # اللاعب المستلم (التالي)
        team_passes["recipientName"] = team_passes["playerName"].shift(-1)

        # تصفية تمريرات داخل نفس الفريق
        team_passes.loc[
            team_passes["teamName"] != team_passes["teamName"].shift(-1), "recipientName"
        ] = None

        team_passes = team_passes.dropna(subset=["recipientName"])

        # Nodes (اللاعبين)
        df_nodes = team_passes.groupby(["playerId", "playerName"], as_index=False).agg(
            x=("x", "mean"),
            y=("y", "mean")
        )

        # Edges (التمريرات)
        df_edges = team_passes.groupby(["playerName", "recipientName"], as_index=False).agg(
            n_pass=("playerId", "count")
        )

        # دمج الإحداثيات
        df_edges = df_edges.merge(df_nodes[['playerName','x','y']], on='playerName', how='left')
        df_edges = df_edges.rename(columns={'x':'x_start','y':'y_start'})
        df_edges = df_edges.merge(df_nodes[['playerName','x','y']], left_on='recipientName', right_on='playerName', how='left')
        df_edges = df_edges.rename(columns={'x':'x_end','y':'y_end'})
        df_edges = df_edges.drop(columns=['playerName_y'])
        df_edges = df_edges.dropna(subset=['x_start','y_start','x_end','y_end'])

        # رسم الملعب
        pitch = Pitch(pitch_type='opta', pitch_color="#ffffff", line_color="#000000")
        fig, ax = pitch.draw(figsize=(12, 8))

        # رسم خطوط التمرير (رمادية + سمك متغير + شفافية متغيرة)
        if not df_edges.empty:
            max_pass = df_edges['n_pass'].max()
            for _, row in df_edges.iterrows():
                lw = 2 + (row['n_pass'] / max_pass) * 6  # السمك يتغير بين 2 و8
                alpha = 0.4 + (row['n_pass'] / max_pass) * 0.6  # الشفافية تتغير بين 0.4 و1
                pitch.lines(row['x_start'], row['y_start'], row['x_end'], row['y_end'],
                            lw=lw, color='gray', ax=ax, alpha=alpha, zorder=1)

        # رسم اللاعبين
        pitch.scatter(df_nodes['x'], df_nodes['y'], s=200, color='white', edgecolors='black', linewidth=1, zorder=2, ax=ax)
        for _, row in df_nodes.iterrows():
            ax.text(row['x'], row['y'], row['playerName'].split()[-1], ha='center', va='center', fontsize=8, zorder=3)

        st.pyplot(fig)

    # ========================
    # PASS MAP (PLAYER)
    # ========================
    else:
        st.subheader(f"🎯 Pass Map — {player_choice}")

        player_passes = team_passes[team_passes["playerName"] == player_choice]

        success = player_passes[player_passes["outcomeType"] == "Successful"].dropna(subset=["x","y","endX","endY"])
        fail = player_passes[player_passes["outcomeType"] == "Unsuccessful"].dropna(subset=["x","y","endX","endY"])

        pitch = Pitch(pitch_type="opta", pitch_color="white", line_color="black")
        fig, ax = pitch.draw(figsize=(10, 7))

        pitch.arrows(success["x"], success["y"], success["endX"], success["endY"],
                      ax=ax, color="black", width=3, headwidth=6, alpha=0.8, zorder=2)
        pitch.arrows(fail["x"], fail["y"], fail["endX"], fail["endY"],
                      ax=ax, color="red", width=2.5, headwidth=5, alpha=0.8, zorder=2)

        ax.set_title(f"{player_choice} — Pass Map", fontsize=15)
        st.pyplot(fig)

else:
    st.info("👈 Choose a team from the sidebar to start.") 