"""Everything that talks to the FPL website: requests, JSON, and turning responses into tables."""

import requests
import pandas as pd


BASE_URL = "https://fantasy.premierleague.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# Build URL + headers
def fetch_league_standings(league_id):

    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Pagination: the API returns 50 managers per page, so keep requesting
    # pages until the response says there is no next page
    all_standings = []
    page = 1

    while True:
        # send GET request (with page number and a 10-second timeout)
        response = requests.get(
            url,
            headers=headers,
            params={"page_standings": page},
            timeout=10,
        )

        # check status code 200?
        if response.status_code == 200:
            # parse JSON to dict
            data = response.json()
            league_name = data["league"]["name"]
            all_standings.extend(data["standings"]["results"])

            # stop when there are no more pages
            if not data["standings"]["has_next"]:
                break
            page += 1
        else:
            raise Exception(
                f"Failed to fetch league data (page {page}): HTTP {response.status_code}"
            )

    # build DataFrame (one row per manager)
    df = pd.DataFrame(all_standings)

    # columns to keep
    columns_to_keep = [
        "rank",
        "player_name",
        "entry_name",
        "event_total",
        "total",
        "entry",
    ]

    df = df[columns_to_keep]

    # rename columns to friendlier names
    df = df.rename(
        columns={
            "player_name": "Manager",
            "entry_name": "Team",
            "event_total": "weekly_total",
            "total": "Total",
            "entry": "player_id",
        }
    )

    return league_name, df


def fetch_manager_gameweek_picks(entry_id, gameweek):

    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gameweek}/picks/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"Couldn't fetch the picks for {entry_id} on GW{gameweek}: HTTP {response.status_code}"
        )
        return None


def fetch_json(url):
    """GET a URL and return the parsed JSON, or raise an error with the status code."""
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Request failed: HTTP {response.status_code} for {url}")
    return response.json()


def fetch_bootstrap():
    """Season-wide data: every gameweek (events), every player (elements), every club (teams)."""
    return fetch_json(f"{BASE_URL}/bootstrap-static/")


def latest_finished_gameweek(bootstrap):
    """The highest gameweek number marked as finished, or None before the season starts."""
    finished = [event["id"] for event in bootstrap["events"] if event["finished"]]
    return max(finished) if finished else None


def fetch_manager_history(entry_id):
    """One manager's score for every gameweek they've played this season."""
    return fetch_json(f"{BASE_URL}/entry/{entry_id}/history/")["current"]


def build_league_history(standings_df):
    """One row per manager per gameweek, for everyone in the league."""
    rows = []
    for _, manager in standings_df.iterrows():
        for gw in fetch_manager_history(manager["player_id"]):
            rows.append(
                {
                    "gameweek": gw["event"],
                    "Manager": manager["Manager"],
                    "Team": manager["Team"],
                    "points": gw["points"],                     # gameweek score
                    "transfer_cost": gw["event_transfers_cost"],  # points lost to hits
                    "bench_points": gw["points_on_bench"],
                }
            )

    history = pd.DataFrame(rows)
    # what actually counted towards the season total
    history["net_points"] = history["points"] - history["transfer_cost"]
    return history


def fetch_gameweek_live(gameweek):
    """Every footballer's FPL points for one gameweek."""
    elements = fetch_json(f"{BASE_URL}/event/{gameweek}/live/")["elements"]
    rows = []
    for element in elements:
        stats = element["stats"]
        rows.append(
            {
                "id": element["id"],
                "points": stats["total_points"],
                "minutes": stats["minutes"],
                "goals": stats["goals_scored"],
                "assists": stats["assists"],
                "bonus": stats["bonus"],
            }
        )
    return pd.DataFrame(rows)
