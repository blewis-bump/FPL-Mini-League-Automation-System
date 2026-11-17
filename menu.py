#!/usr/bin/env python3
"""The terminal menu. Run this file to start the app: python menu.py"""

import argparse

import fpl_api
import fpl_stats as stats


def ask_gameweek(latest):
    """Ask for a finished gameweek; pressing Enter picks the latest one."""
    while True:
        typed = input(f"Gameweek (1-{latest}, press Enter for {latest}): ").strip()
        if typed == "":
            return latest
        if typed.isdigit() and 1 <= int(typed) <= latest:
            return int(typed)
        print(f"Please enter a number from 1 to {latest}.")


def print_table(title, df):
    print(f"\n=== {title} ===")
    if df.empty:
        print("No data.")
    else:
        print(df.to_string(index=False))


def run_menu(league_name, standings_df, bootstrap):
    latest = fpl_api.latest_finished_gameweek(bootstrap)
    history_df = None  # fetched the first time a feature needs it, then reused

    menu = """
========== FPL MENU ==========
1. League standings
2. This gameweek's scores
3. Manager of the week
4. Player of the week
5. Hall of fame
6. 1st place manager's GW1 picks
0. Exit
"""

    while True:
        print(menu)
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        if choice in ("3", "4", "5") and latest is None:
            print("No gameweek has finished yet.")
            continue

        try:
            # manager of the week and hall of fame both need every manager's history
            if choice in ("3", "5") and history_df is None:
                print(f"Fetching gameweek history for {len(standings_df)} managers...")
                history_df = fpl_api.build_league_history(standings_df)

            if choice == "1":
                print_table(f"{league_name.upper()} STANDINGS", standings_df)

            elif choice == "2":
                print_table(f"{league_name.upper()} - THIS GAMEWEEK", stats.sort_by_weekly(standings_df))

            elif choice == "3":
                gw = ask_gameweek(latest)
                print_table(f"MANAGER OF THE WEEK - GW{gw}", stats.manager_of_the_week(history_df, gw))

            elif choice == "4":
                gw = ask_gameweek(latest)
                live_df = fpl_api.fetch_gameweek_live(gw)
                print_table(f"PLAYER OF THE WEEK - GW{gw}", stats.player_of_the_week(bootstrap, live_df))

            elif choice == "5":
                roll, leaderboard = stats.hall_of_fame(history_df, latest)
                print_table(f"HALL OF FAME - GW1 to GW{latest}", leaderboard)
                print_table("ROLL OF HONOUR", roll)

            elif choice == "6":
                top_manager_entry_id = standings_df.iloc[0]["player_id"]
                top_manager_name = standings_df.iloc[0]["Manager"]
                print(
                    f"\nFetching GW1 picks for 1st place manager: {top_manager_name} (ID: {top_manager_entry_id})..."
                )
                gw1_picks = fpl_api.fetch_manager_gameweek_picks(
                    entry_id=top_manager_entry_id, gameweek=1
                )
                if gw1_picks:
                    print(f"Active Chip Used in GW1: {gw1_picks.get('active_chip')}")
                    print(f"Total Team Picks Fetched: {len(gw1_picks.get('picks', []))}")

            else:
                print("Please choose one of the numbers in the menu.")

        except Exception as error:
            # one failed request shouldn't close the whole menu
            print(f"Something went wrong: {error}")

        input("\nPress Enter to go back to the menu...")


if __name__ == "__main__":
    # Let the user pass a league ID when running the script;
    # if none is given, ask for it from the keyboard
    DEFAULT_LEAGUE_ID = 912144
    parser = argparse.ArgumentParser(description="Show FPL classic league standings.")
    parser.add_argument("league_id", nargs="?", type=int, default=None,
                        help="League ID (the number in the league's URL)")
    LEAGUE_ID = parser.parse_args().league_id

    while LEAGUE_ID is None:
        typed = input(f"Enter your league ID (press Enter for {DEFAULT_LEAGUE_ID}): ").strip()
        if typed == "":
            LEAGUE_ID = DEFAULT_LEAGUE_ID
        elif typed.isdigit():
            LEAGUE_ID = int(typed)
        else:
            print("Please enter numbers only.")

    print("Loading league...")
    league_name, standings_df = fpl_api.fetch_league_standings(LEAGUE_ID)
    bootstrap = fpl_api.fetch_bootstrap()

    run_menu(league_name, standings_df, bootstrap)