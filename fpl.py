#!/usr/bin/env python3

import argparse
import requests
import pandas as pd


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


if __name__ == "__main__":
    # Let the user pass a league ID when running the script;
    # fall back to 912144 if none is given
    parser = argparse.ArgumentParser(description="Show FPL classic league standings.")
    parser.add_argument("league_id", nargs="?", type=int, default=912144,
                        help="League ID (the number in the league's URL)")
    LEAGUE_ID = parser.parse_args().league_id

    league_name, standings_df = fetch_league_standings(LEAGUE_ID)

    print(f"=== {league_name.upper()} STANDINGS ===")
    print(standings_df.to_string(index=False))

    top_manager_entry_id = standings_df.iloc[0]["entry"]
    top_manager_name = standings_df.iloc[0]["player_name"]

    print(
        f"\nFetching GW1 picks for 1st place manager: {top_manager_name} (ID: {top_manager_entry_id})..."
    )
    gw1_picks = fetch_manager_gameweek_picks(
        entry_id=top_manager_entry_id, gameweek=1
    )

    if gw1_picks:
        print(f"Active Chip Used in GW1: {gw1_picks.get('active_chip')}")
        print(f"Total Team Picks Fetched: {len(gw1_picks.get('picks', []))}")
