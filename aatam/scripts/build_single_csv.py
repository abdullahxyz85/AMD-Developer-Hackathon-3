#!/usr/bin/env python3
"""
Single Master CSV Generator for BoardGameGeek Datasets
Consolidates all files in raw_data into EXACTLY ONE comprehensive CSV file in processed_data/.
"""

import os
import csv
import sqlite3
import time

RAW_DIR = "raw_data"
OUT_DIR = "processed_data"
OUT_FILE = os.path.join(OUT_DIR, "bgg_master_dataset.csv")

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    log("=== Step 1: Aggregating user_ratings.csv (18.9M records) ===")
    t0 = time.time()
    user_ratings_stats = {} # BGGId -> [count, sum, min, max]
    with open(os.path.join(RAW_DIR, "user_ratings.csv"), "r", encoding="utf-8", errors="ignore") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            bgg_id = row[0]
            try:
                val = float(row[1])
            except ValueError:
                continue
            if bgg_id not in user_ratings_stats:
                user_ratings_stats[bgg_id] = [1, val, val, val]
            else:
                s = user_ratings_stats[bgg_id]
                s[0] += 1
                s[1] += val
                if val < s[2]: s[2] = val
                if val > s[3]: s[3] = val
    log(f"Aggregated user ratings for {len(user_ratings_stats):,} games in {time.time()-t0:.2f}s.")

    log("=== Step 2: Extracting snapshots (bgg_db_*.csv) ===")
    snapshots_data = {} # game_id -> { 'Rank_2017_04': ..., 'Rank_2018_01': ..., 'Rank_2018_06': ..., 'GeekRating_Snapshot': ..., 'BGG_URL': ... }
    for sn_date, sn_file in [
        ('2017_04', 'bgg_db_2017_04.csv'),
        ('2018_01', 'bgg_db_2018_01.csv'),
        ('2018_06', 'bgg_db_1806.csv')
    ]:
        with open(os.path.join(RAW_DIR, sn_file), "r", encoding="latin-1") as f:
            r = csv.reader(f)
            h = next(r)
            id_idx = h.index("game_id")
            rank_idx = h.index("rank")
            url_idx = h.index("bgg_url")
            geek_idx = h.index("geek_rating")
            
            for row in r:
                gid = row[id_idx]
                if gid not in snapshots_data:
                    snapshots_data[gid] = {}
                snapshots_data[gid][f'Rank_{sn_date}'] = row[rank_idx]
                snapshots_data[gid]['BGG_URL'] = row[url_idx]
                snapshots_data[gid]['GeekRating_Snapshot'] = row[geek_idx]
    log(f"Extracted snapshots data for {len(snapshots_data):,} games.")

    log("=== Step 3: Extracting BGG_Data_Set.csv / bgg_dataset.csv ===")
    bgg_dataset_data = {} # ID -> row dict
    with open(os.path.join(RAW_DIR, "BGG_Data_Set.csv"), "r", encoding="latin-1") as f:
        r = csv.reader(f)
        h = next(r)
        for row in r:
            if not row or not any(row):
                continue
            gid = row[0].strip()
            if gid:
                bgg_dataset_data[gid] = {
                    'Name': row[1].strip(),
                    'YearPublished': row[2].strip(),
                    'MinPlayers': row[3].strip(),
                    'MaxPlayers': row[4].strip(),
                    'PlayTime': row[5].strip(),
                    'MinAge': row[6].strip(),
                    'UsersRated': row[7].strip(),
                    'RatingAverage': row[8].strip(),
                    'BGGRank_2021': row[9].strip(),
                    'ComplexityAverage': row[10].strip(),
                    'OwnedUsers': row[11].strip(),
                    'Mechanics': row[12].strip(),
                    'Domains': row[13].strip()
                }
    log(f"Extracted BGG_Data_Set data for {len(bgg_dataset_data):,} games.")

    log("=== Step 4: Extracting sqlite BoardGames table (90,400 games) ===")
    conn = sqlite3.connect(os.path.join(RAW_DIR, "database.sqlite"))
    cur = conn.cursor()
    cur.execute("""
        SELECT [game.id], [game.type], [details.name], [details.yearpublished], [details.description],
               [details.image], [details.minplayers], [details.maxplayers], [details.playingtime],
               [details.minage], [stats.average], [stats.bayesaverage], [stats.usersrated],
               [stats.owned], [stats.wanting], [stats.wishing], [stats.averageweight],
               [attributes.boardgamedesigner], [attributes.boardgameartist], [attributes.boardgamepublisher],
               [attributes.boardgamemechanic], [attributes.boardgamecategory], [attributes.boardgamefamily]
        FROM BoardGames
    """)
    sqlite_games = {}
    for r in cur.fetchall():
        gid = str(r[0])
        sqlite_games[gid] = {
            'GameType': r[1] or '',
            'Name': r[2] or '',
            'YearPublished': str(r[3] or ''),
            'Description': r[4] or '',
            'ImagePath': r[5] or '',
            'MinPlayers': str(r[6] or ''),
            'MaxPlayers': str(r[7] or ''),
            'PlayingTime': str(r[8] or ''),
            'MinAge': str(r[9] or ''),
            'AvgRating': str(r[10] or ''),
            'BayesAvgRating': str(r[11] or ''),
            'NumUserRatings': str(r[12] or ''),
            'NumOwned': str(r[13] or ''),
            'NumWant': str(r[14] or ''),
            'NumWish': str(r[15] or ''),
            'GameWeight': str(r[16] or ''),
            'Designers': r[17] or '',
            'Artists': r[18] or '',
            'Publishers': r[19] or '',
            'Mechanics': r[20] or '',
            'Categories': r[21] or '',
            'Family': r[22] or ''
        }
    conn.close()
    log(f"Extracted {len(sqlite_games):,} games from SQLite.")

    log("=== Step 5: Streaming & joining core 21,925 games with all 8 feature tables ===")
    core_files = {
        'games': os.path.join(RAW_DIR, 'games.csv'),
        'mechanics': os.path.join(RAW_DIR, 'mechanics.csv'),
        'themes': os.path.join(RAW_DIR, 'themes.csv'),
        'subcategories': os.path.join(RAW_DIR, 'subcategories.csv'),
        'artists': os.path.join(RAW_DIR, 'artists_reduced.csv'),
        'designers': os.path.join(RAW_DIR, 'designers_reduced.csv'),
        'publishers': os.path.join(RAW_DIR, 'publishers_reduced.csv'),
        'ratings': os.path.join(RAW_DIR, 'ratings_distribution.csv'),
    }
    handles = {k: open(v, 'r', encoding='utf-8', errors='ignore') for k, v in core_files.items()}
    readers = {k: csv.reader(handles[k]) for k in core_files}
    headers = {k: next(readers[k]) for k in core_files}

    games_header = headers['games']
    cat_cols = [c for c in games_header if c.startswith('Cat:')]
    mech_cols = [(i, col) for i, col in enumerate(headers['mechanics']) if col != 'BGGId']
    theme_cols = [(i, col.replace('Theme_', '')) for i, col in enumerate(headers['themes']) if col != 'BGGId']
    subcat_cols = [(i, col) for i, col in enumerate(headers['subcategories']) if col != 'BGGId']
    art_bgg_idx = headers['artists'].index('BGGId')
    art_low_idx = headers['artists'].index('Low-Exp Artist')
    art_cols = [(i, col) for i, col in enumerate(headers['artists']) if i not in (art_bgg_idx, art_low_idx)]
    des_bgg_idx = headers['designers'].index('BGGId')
    des_low_idx = headers['designers'].index('Low-Exp Designer')
    des_cols = [(i, col) for i, col in enumerate(headers['designers']) if i not in (des_bgg_idx, des_low_idx)]
    pub_bgg_idx = headers['publishers'].index('BGGId')
    pub_low_idx = headers['publishers'].index('Low-Exp Publisher')
    pub_cols = [(i, col) for i, col in enumerate(headers['publishers']) if i not in (pub_bgg_idx, pub_low_idx)]
    rat_bgg_idx = headers['ratings'].index('BGGId')
    rat_total_idx = headers['ratings'].index('total_ratings')
    rat_dist_cols = [(i, col) for i, col in enumerate(headers['ratings']) if i not in (rat_bgg_idx, rat_total_idx)]

    # Final Master Columns List
    master_columns = [
        'BGGId', 'Name', 'GameType', 'YearPublished', 'Description', 'ImagePath', 'Family',
        'GameWeight', 'MinPlayers', 'MaxPlayers', 'BestPlayers', 'GoodPlayers',
        'ComAgeRec', 'MfgAgeRec', 'LanguageEase',
        'MfgPlaytime', 'ComMinPlaytime', 'ComMaxPlaytime',
        'AvgRating', 'BayesAvgRating', 'StdDev', 'NumUserRatings', 'NumComments',
        'NumOwned', 'NumWant', 'NumWish', 'NumWeightVotes',
        'Rank:boardgame', 'Rank:strategygames', 'Rank:abstracts', 'Rank:familygames',
        'Rank:thematic', 'Rank:cgs', 'Rank:wargames', 'Rank:partygames', 'Rank:childrensgames',
        'Rank_2017_04', 'Rank_2018_01', 'Rank_2018_06', 'BGGRank_2021',
        'Categories', 'Domains',
        'Cat:Thematic', 'Cat:Strategy', 'Cat:War', 'Cat:Family', 'Cat:CGS', 'Cat:Abstract', 'Cat:Party', 'Cat:Childrens',
        'NumAlternates', 'NumExpansions', 'NumImplementations', 'IsReimplementation', 'Kickstarted',
        'Mechanics', 'MechanicsCount',
        'Themes', 'ThemesCount',
        'Subcategories', 'SubcategoriesCount',
        'Artists', 'ArtistsCount', 'LowExpArtist',
        'Designers', 'DesignersCount', 'LowExpDesigner',
        'Publishers', 'PublishersCount', 'LowExpPublisher',
        'TotalRatingsDistribution', 'PeakRatingBucket',
        'UserRatings_LoggedCount', 'UserRatings_LoggedMean', 'UserRatings_LoggedMin', 'UserRatings_LoggedMax',
        'BGG_URL'
    ]

    out_file = open(OUT_FILE, 'w', encoding='utf-8', newline='')
    writer = csv.writer(out_file)
    writer.writerow(master_columns)

    processed_ids = set()

    # Step 5A: Process the 21,925 core games
    while True:
        row_games = next(readers['games'], None)
        if row_games is None:
            break
        row_mech = next(readers['mechanics'])
        row_theme = next(readers['themes'])
        row_subcat = next(readers['subcategories'])
        row_art = next(readers['artists'])
        row_des = next(readers['designers'])
        row_pub = next(readers['publishers'])
        row_rat = next(readers['ratings'])

        bgg_id = row_games[0]
        processed_ids.add(bgg_id)

        def g(col_name):
            return row_games[games_header.index(col_name)]

        active_cats = [c.replace('Cat:', '') for c in cat_cols if row_games[games_header.index(c)] == '1']
        cat_str = '; '.join(active_cats)
        active_mechs = [name for i, name in mech_cols if row_mech[i] == '1']
        active_themes = [name for i, name in theme_cols if row_theme[i] == '1']
        active_subcats = [name for i, name in subcat_cols if row_subcat[i] == '1']
        active_arts = [name for i, name in art_cols if row_art[i] == '1']
        active_dess = [name for i, name in des_cols if row_des[i] == '1']
        active_pubs = [name for i, name in pub_cols if row_pub[i] == '1']

        tot_rat = row_rat[rat_total_idx]
        max_votes = -1.0
        peak_bucket = ""
        for i, col in rat_dist_cols:
            try:
                v = float(row_rat[i])
                if v > max_votes:
                    max_votes = v
                    peak_bucket = col
            except ValueError:
                pass

        # User ratings logged stats
        ur_stat = user_ratings_stats.get(bgg_id)
        ur_count = ur_stat[0] if ur_stat else ''
        ur_mean = f"{ur_stat[1]/ur_stat[0]:.2f}" if ur_stat else ''
        ur_min = ur_stat[2] if ur_stat else ''
        ur_max = ur_stat[3] if ur_stat else ''

        # Snapshot data
        sn_info = snapshots_data.get(bgg_id, {})
        rank_17 = sn_info.get('Rank_2017_04', '')
        rank_18_01 = sn_info.get('Rank_2018_01', '')
        rank_18_06 = sn_info.get('Rank_2018_06', '')
        bgg_url = sn_info.get('BGG_URL', f"https://boardgamegeek.com/boardgame/{bgg_id}")

        # BGG dataset data
        bgg_ds = bgg_dataset_data.get(bgg_id, {})
        bgg_rank_21 = bgg_ds.get('BGGRank_2021', '')
        domains = bgg_ds.get('Domains', '')

        # SQLite game type
        sq_info = sqlite_games.get(bgg_id, {})
        game_type = sq_info.get('GameType', 'boardgame')

        master_row = [
            bgg_id, g('Name'), game_type, g('YearPublished'), g('Description'), g('ImagePath'), g('Family'),
            g('GameWeight'), g('MinPlayers'), g('MaxPlayers'), g('BestPlayers'), g('GoodPlayers'),
            g('ComAgeRec'), g('MfgAgeRec'), g('LanguageEase'),
            g('MfgPlaytime'), g('ComMinPlaytime'), g('ComMaxPlaytime'),
            g('AvgRating'), g('BayesAvgRating'), g('StdDev'), g('NumUserRatings'), g('NumComments'),
            g('NumOwned'), g('NumWant'), g('NumWish'), g('NumWeightVotes'),
            g('Rank:boardgame'), g('Rank:strategygames'), g('Rank:abstracts'), g('Rank:familygames'),
            g('Rank:thematic'), g('Rank:cgs'), g('Rank:wargames'), g('Rank:partygames'), g('Rank:childrensgames'),
            rank_17, rank_18_01, rank_18_06, bgg_rank_21,
            cat_str, domains,
            g('Cat:Thematic'), g('Cat:Strategy'), g('Cat:War'), g('Cat:Family'), g('Cat:CGS'), g('Cat:Abstract'), g('Cat:Party'), g('Cat:Childrens'),
            g('NumAlternates'), g('NumExpansions'), g('NumImplementations'), g('IsReimplementation'), g('Kickstarted'),
            '; '.join(active_mechs), len(active_mechs),
            '; '.join(active_themes), len(active_themes),
            '; '.join(active_subcats), len(active_subcats),
            '; '.join(active_arts), len(active_arts), row_art[art_low_idx],
            '; '.join(active_dess), len(active_dess), row_des[des_low_idx],
            '; '.join(active_pubs), len(active_pubs), row_pub[pub_low_idx],
            tot_rat, peak_bucket,
            ur_count, ur_mean, ur_min, ur_max,
            bgg_url
        ]
        writer.writerow(master_row)

    for h in handles.values():
        h.close()
    log(f"Wrote {len(processed_ids):,} core games to master file.")

    # Step 5B: Append remaining games from SQLite (covers all other games & expansions across the database)
    sqlite_added = 0
    for gid, sq in sqlite_games.items():
        if gid in processed_ids:
            continue
        processed_ids.add(gid)
        sqlite_added += 1

        sn_info = snapshots_data.get(gid, {})
        rank_17 = sn_info.get('Rank_2017_04', '')
        rank_18_01 = sn_info.get('Rank_2018_01', '')
        rank_18_06 = sn_info.get('Rank_2018_06', '')
        bgg_url = sn_info.get('BGG_URL', f"https://boardgamegeek.com/boardgame/{gid}")

        bgg_ds = bgg_dataset_data.get(gid, {})
        bgg_rank_21 = bgg_ds.get('BGGRank_2021', '')
        domains = bgg_ds.get('Domains', '')

        ur_stat = user_ratings_stats.get(gid)
        ur_count = ur_stat[0] if ur_stat else ''
        ur_mean = f"{ur_stat[1]/ur_stat[0]:.2f}" if ur_stat else ''
        ur_min = ur_stat[2] if ur_stat else ''
        ur_max = ur_stat[3] if ur_stat else ''

        row = [
            gid, sq['Name'], sq['GameType'], sq['YearPublished'], sq['Description'], sq['ImagePath'], sq['Family'],
            sq['GameWeight'], sq['MinPlayers'], sq['MaxPlayers'], '', '',
            sq['MinAge'], sq['MinAge'], '',
            sq['PlayingTime'], sq['PlayingTime'], sq['PlayingTime'],
            sq['AvgRating'], sq['BayesAvgRating'], '', sq['NumUserRatings'], '',
            sq['NumOwned'], sq['NumWant'], sq['NumWish'], '',
            '', '', '', '', '', '', '', '', '',
            rank_17, rank_18_01, rank_18_06, bgg_rank_21,
            sq['Categories'], domains,
            '', '', '', '', '', '', '', '',
            '', '', '', '', '',
            sq['Mechanics'], len(sq['Mechanics'].split(',')) if sq['Mechanics'] else 0,
            '', 0,
            '', 0,
            sq['Artists'], len(sq['Artists'].split(',')) if sq['Artists'] else 0, '',
            sq['Designers'], len(sq['Designers'].split(',')) if sq['Designers'] else 0, '',
            sq['Publishers'], len(sq['Publishers'].split(',')) if sq['Publishers'] else 0, '',
            '', '',
            ur_count, ur_mean, ur_min, ur_max,
            bgg_url
        ]
        writer.writerow(row)

    # Step 5C: Append any remaining games from BGG_Data_Set
    ds_added = 0
    for gid, ds in bgg_dataset_data.items():
        if gid in processed_ids:
            continue
        processed_ids.add(gid)
        ds_added += 1

        sn_info = snapshots_data.get(gid, {})
        rank_17 = sn_info.get('Rank_2017_04', '')
        rank_18_01 = sn_info.get('Rank_2018_01', '')
        rank_18_06 = sn_info.get('Rank_2018_06', '')
        bgg_url = sn_info.get('BGG_URL', f"https://boardgamegeek.com/boardgame/{gid}")

        row = [
            gid, ds['Name'], 'boardgame', ds['YearPublished'], '', '', '',
            ds['ComplexityAverage'], ds['MinPlayers'], ds['MaxPlayers'], '', '',
            ds['MinAge'], ds['MinAge'], '',
            ds['PlayTime'], ds['PlayTime'], ds['PlayTime'],
            ds['RatingAverage'], '', '', ds['UsersRated'], '',
            ds['OwnedUsers'], '', '', '',
            '', '', '', '', '', '', '', '', '',
            rank_17, rank_18_01, rank_18_06, ds['BGGRank_2021'],
            '', ds['Domains'],
            '', '', '', '', '', '', '', '',
            '', '', '', '', '',
            ds['Mechanics'], len(ds['Mechanics'].split(',')) if ds['Mechanics'] else 0,
            '', 0,
            '', 0,
            '', 0, '',
            '', 0, '',
            '', 0, '',
            '', '',
            '', '', '', '',
            bgg_url
        ]
        writer.writerow(row)

    out_file.close()

    log(f"Master file complete! Total games written: {len(processed_ids):,} (Core: 21,925, SQLite additional: {sqlite_added:,}, BGG_Data_Set additional: {ds_added:,})")
    log(f"Master output: {OUT_FILE} ({os.path.getsize(OUT_FILE)/1024/1024:.2f} MB, {len(master_columns)} columns)")

    # Clean up any other CSV files in processed_data to ensure STRICTLY ONE CSV file exists
    log("Ensuring exactly ONE CSV file exists in processed_data/...")
    for f in os.listdir(OUT_DIR):
        if f.endswith(".csv") and f != "bgg_master_dataset.csv":
            os.remove(os.path.join(OUT_DIR, f))
            log(f"Removed extra CSV: {f}")

    log("=== Single Master CSV generation finished successfully! ===")

if __name__ == '__main__':
    main()
