"""
The features. Every function here takes tables in and returns tables out.
No internet requests and no printing, so the same functions can feed a dashboard later.
"""

import pandas as pd


def sort_by_weekly(df):
    """Returns a copy of the standings sorted by this gameweek's points, highest first."""
    return df.sort_values(by="weekly_total", ascending=False).reset_index(drop=True)


def manager_of_the_week(history_df, gameweek):
    """The manager(s) with the highest net score in a gameweek. Ties return several rows."""
    week = history_df[history_df["gameweek"] == gameweek]
    if week.empty:
        return week
    best = week["net_points"].max()
    winners = week[week["net_points"] == best]
    return winners[["gameweek", "Manager", "Team", "points", "transfer_cost", "net_points"]]


def player_of_the_week(bootstrap, live_df):
    """
    The footballer(s) with the most FPL points in a gameweek. Ties return several rows.
    live_df is the table from fpl_api.fetch_gameweek_live() for that gameweek.
    """
    players = pd.DataFrame(bootstrap["elements"])[["id", "web_name", "team", "element_type"]]
    teams = pd.DataFrame(bootstrap["teams"])[["id", "name"]].rename(
        columns={"id": "team", "name": "club"}
    )
    positions = pd.DataFrame(bootstrap["element_types"])[["id", "singular_name_short"]].rename(
        columns={"id": "element_type", "singular_name_short": "position"}
    )

    best = live_df["points"].max()
    top = live_df[live_df["points"] == best]

    top = (
        top.merge(players, on="id", how="left")
        .merge(teams, on="team", how="left")
        .merge(positions, on="element_type", how="left")
    )
    return top[["web_name", "club", "position", "points", "goals", "assists", "bonus", "minutes"]]


def hall_of_fame(history_df, up_to_gameweek):
    """
    Returns two tables:
      roll_of_honour: the manager of the week for every finished gameweek
      leaderboard:    how many weeks each manager has won
    A tie counts as a win for everyone tied.
    """
    finished = history_df[history_df["gameweek"] <= up_to_gameweek].copy()

    # best score in each gameweek, written onto every row of that gameweek
    finished["week_best"] = finished.groupby("gameweek")["net_points"].transform("max")
    winners = finished[finished["net_points"] == finished["week_best"]]

    roll_of_honour = winners[["gameweek", "Manager", "Team", "net_points"]].sort_values("gameweek")

    leaderboard = (
        winners.groupby(["Manager", "Team"])
        .agg(
            wins=("gameweek", "count"),
            best_winning_score=("net_points", "max"),
            gameweeks_won=("gameweek", lambda gws: ", ".join(str(g) for g in sorted(gws))),
        )
        .reset_index()
        .sort_values(["wins", "best_winning_score"], ascending=False)
    )
    return roll_of_honour, leaderboard