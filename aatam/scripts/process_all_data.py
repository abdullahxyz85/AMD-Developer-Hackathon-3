#!/usr/bin/env python3
"""
ETL Processing Script for BoardGameGeek Raw Datasets
Consolidates repeated files, merges fragmented feature matrices into neat,
organized, and referable datasets, and outputs to processed_data/.
"""

import os
import csv
import sys
import time

RAW_DIR = "raw_data"
OUT_DIR = "processed_data"

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# ----------------------------------------------------------------------
# 1. BUILD BGG_GAMES_MASTER.CSV & BGG_GAMES_WIDE_ALL_COLUMNS.CSV
# ----------------------------------------------------------------------
def process_games_datasets():
    log("Starting consolidation of 8-table game feature datasets...")
    
    files = {
        'games': os.path.join(RAW_DIR, 'games.csv'),
        'mechanics': os.path.join(RAW_DIR, 'mechanics.csv'),
        'themes': os.path.join(RAW_DIR, 'themes.csv'),
        'subcategories': os.path.join(RAW_DIR, 'subcategories.csv'),
        'artists': os.path.join(RAW_DIR, 'artists_reduced.csv'),
        'designers': os.path.join(RAW_DIR, 'designers_reduced.csv'),
        'publishers': os.path.join(RAW_DIR, 'publishers_reduced.csv'),
        'ratings': os.path.join(RAW_DIR, 'ratings_distribution.csv'),
    }

    # Open all file handles
    handles = {k: open(v, 'r', encoding='utf-8', errors='ignore') for k, v in files.items()}
    readers = {k: csv.reader(handles[k]) for k in files}
    headers = {k: next(readers[k]) for k in files}

    # Indices and column lists for extraction
    # games
    games_header = headers['games']
    bgg_id_idx = games_header.index('BGGId')
    
    # Category columns in games.csv
    cat_cols = [c for c in games_header if c.startswith('Cat:')]

    # mechanics
    mech_cols = [(i, col) for i, col in enumerate(headers['mechanics']) if col != 'BGGId']
    
    # themes
    theme_cols = [(i, col.replace('Theme_', '')) for i, col in enumerate(headers['themes']) if col != 'BGGId']
    
    # subcategories
    subcat_cols = [(i, col) for i, col in enumerate(headers['subcategories']) if col != 'BGGId']
    
    # artists
    art_bgg_idx = headers['artists'].index('BGGId')
    art_low_idx = headers['artists'].index('Low-Exp Artist')
    art_cols = [(i, col) for i, col in enumerate(headers['artists']) if i not in (art_bgg_idx, art_low_idx)]
    
    # designers
    des_bgg_idx = headers['designers'].index('BGGId')
    des_low_idx = headers['designers'].index('Low-Exp Designer')
    des_cols = [(i, col) for i, col in enumerate(headers['designers']) if i not in (des_bgg_idx, des_low_idx)]
    
    # publishers
    pub_bgg_idx = headers['publishers'].index('BGGId')
    pub_low_idx = headers['publishers'].index('Low-Exp Publisher')
    pub_cols = [(i, col) for i, col in enumerate(headers['publishers']) if i not in (pub_bgg_idx, pub_low_idx)]
    
    # ratings distribution
    rat_bgg_idx = headers['ratings'].index('BGGId')
    rat_total_idx = headers['ratings'].index('total_ratings')
    rat_dist_cols = [(i, col) for i, col in enumerate(headers['ratings']) if i not in (rat_bgg_idx, rat_total_idx)]

    # Define headers for bgg_games_master.csv
    # Reorganize for maximum clarity and referability
    master_header = [
        'BGGId', 'Name', 'YearPublished', 'Description', 'ImagePath', 'Family',
        'GameWeight', 'MinPlayers', 'MaxPlayers', 'BestPlayers', 'GoodPlayers',
        'ComAgeRec', 'MfgAgeRec', 'LanguageEase',
        'MfgPlaytime', 'ComMinPlaytime', 'ComMaxPlaytime',
        'AvgRating', 'BayesAvgRating', 'StdDev', 'NumUserRatings', 'NumComments',
        'NumOwned', 'NumWant', 'NumWish', 'NumWeightVotes', 'TotalRatingsDistribution', 'PeakRatingBucket',
        'Rank:boardgame', 'Rank:strategygames', 'Rank:abstracts', 'Rank:familygames',
        'Rank:thematic', 'Rank:cgs', 'Rank:wargames', 'Rank:partygames', 'Rank:childrensgames',
        'Categories', 'Cat:Thematic', 'Cat:Strategy', 'Cat:War', 'Cat:Family', 'Cat:CGS', 'Cat:Abstract', 'Cat:Party', 'Cat:Childrens',
        'NumAlternates', 'NumExpansions', 'NumImplementations', 'IsReimplementation', 'Kickstarted',
        'Mechanics', 'MechanicsCount',
        'Themes', 'ThemesCount',
        'Subcategories', 'SubcategoriesCount',
        'Artists', 'ArtistsCount', 'LowExpArtist',
        'Designers', 'DesignersCount', 'LowExpDesigner',
        'Publishers', 'PublishersCount', 'LowExpPublisher'
    ]

    out_master_path = os.path.join(OUT_DIR, 'bgg_games_master.csv')
    out_master_file = open(out_master_path, 'w', encoding='utf-8', newline='')
    master_writer = csv.writer(out_master_file)
    master_writer.writerow(master_header)

    # Wide matrix header setup:
    # 1. games columns
    # 2. mechanics columns (excluding BGGId)
    # 3. themes columns (excluding BGGId)
    # 4. subcategories columns (excluding BGGId)
    # 5. Low-Exp Artist + artists columns
    # 6. Low-Exp Designer + designers columns
    # 7. Low-Exp Publisher + publishers columns
    # 8. ratings distribution columns + total_ratings
    wide_header = list(games_header) # Starts with BGGId, Name, ...
    wide_header += [f"Mech:{c}" for _, c in mech_cols]
    wide_header += [f"Theme:{c}" for _, c in theme_cols]
    wide_header += [f"Subcat:{c}" for _, c in subcat_cols]
    wide_header += ['Low-Exp Artist'] + [f"Artist:{c}" for _, c in art_cols]
    wide_header += ['Low-Exp Designer'] + [f"Designer:{c}" for _, c in des_cols]
    wide_header += ['Low-Exp Publisher'] + [f"Publisher:{c}" for _, c in pub_cols]
    wide_header += [f"RatingCount:{c}" for _, c in rat_dist_cols] + ['total_ratings']

    out_wide_path = os.path.join(OUT_DIR, 'bgg_games_wide_all_columns.csv')
    out_wide_file = open(out_wide_path, 'w', encoding='utf-8', newline='')
    wide_writer = csv.writer(out_wide_file)
    wide_writer.writerow(wide_header)

    t0 = time.time()
    row_count = 0

    while True:
        # Read next row from all 8 files
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

        row_count += 1
        bgg_id = row_games[bgg_id_idx]

        # 1. Extract active categories from games.csv
        active_cats = [c.replace('Cat:', '') for c in cat_cols if row_games[games_header.index(c)] == '1']
        cat_str = '; '.join(active_cats)

        # 2. Extract active mechanics
        active_mechs = [name for i, name in mech_cols if row_mech[i] == '1']
        mech_str = '; '.join(active_mechs)

        # 3. Extract active themes
        active_themes = [name for i, name in theme_cols if row_theme[i] == '1']
        theme_str = '; '.join(active_themes)

        # 4. Extract active subcategories
        active_subcats = [name for i, name in subcat_cols if row_subcat[i] == '1']
        subcat_str = '; '.join(active_subcats)

        # 5. Extract active artists
        active_arts = [name for i, name in art_cols if row_art[i] == '1']
        art_str = '; '.join(active_arts)
        low_art = row_art[art_low_idx]

        # 6. Extract active designers
        active_dess = [name for i, name in des_cols if row_des[i] == '1']
        des_str = '; '.join(active_dess)
        low_des = row_des[des_low_idx]

        # 7. Extract active publishers
        active_pubs = [name for i, name in pub_cols if row_pub[i] == '1']
        pub_str = '; '.join(active_pubs)
        low_pub = row_pub[pub_low_idx]

        # 8. Ratings peak bucket & total
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

        # Build master row
        # Map games columns by name
        def g(col_name):
            return row_games[games_header.index(col_name)]

        master_row = [
            bgg_id, g('Name'), g('YearPublished'), g('Description'), g('ImagePath'), g('Family'),
            g('GameWeight'), g('MinPlayers'), g('MaxPlayers'), g('BestPlayers'), g('GoodPlayers'),
            g('ComAgeRec'), g('MfgAgeRec'), g('LanguageEase'),
            g('MfgPlaytime'), g('ComMinPlaytime'), g('ComMaxPlaytime'),
            g('AvgRating'), g('BayesAvgRating'), g('StdDev'), g('NumUserRatings'), g('NumComments'),
            g('NumOwned'), g('NumWant'), g('NumWish'), g('NumWeightVotes'), tot_rat, peak_bucket,
            g('Rank:boardgame'), g('Rank:strategygames'), g('Rank:abstracts'), g('Rank:familygames'),
            g('Rank:thematic'), g('Rank:cgs'), g('Rank:wargames'), g('Rank:partygames'), g('Rank:childrensgames'),
            cat_str, g('Cat:Thematic'), g('Cat:Strategy'), g('Cat:War'), g('Cat:Family'), g('Cat:CGS'), g('Cat:Abstract'), g('Cat:Party'), g('Cat:Childrens'),
            g('NumAlternates'), g('NumExpansions'), g('NumImplementations'), g('IsReimplementation'), g('Kickstarted'),
            mech_str, len(active_mechs),
            theme_str, len(active_themes),
            subcat_str, len(active_subcats),
            art_str, len(active_arts), low_art,
            des_str, len(active_dess), low_des,
            pub_str, len(active_pubs), low_pub
        ]
        master_writer.writerow(master_row)

        # Build wide row
        wide_row = list(row_games)
        wide_row += [row_mech[i] for i, _ in mech_cols]
        wide_row += [row_theme[i] for i, _ in theme_cols]
        wide_row += [row_subcat[i] for i, _ in subcat_cols]
        wide_row += [low_art] + [row_art[i] for i, _ in art_cols]
        wide_row += [low_des] + [row_des[i] for i, _ in des_cols]
        wide_row += [low_pub] + [row_pub[i] for i, _ in pub_cols]
        wide_row += [row_rat[i] for i, _ in rat_dist_cols] + [tot_rat]
        wide_writer.writerow(wide_row)

        if row_count % 5000 == 0:
            log(f"Processed {row_count} games...")

    # Close all files
    for h in handles.values():
        h.close()
    out_master_file.close()
    out_wide_file.close()

    elapsed = time.time() - t0
    log(f"Completed {row_count} games consolidation in {elapsed:.2f}s.")
    log(f"  Master output: {out_master_path} ({os.path.getsize(out_master_path)/1024/1024:.2f} MB, {len(master_header)} cols)")
    log(f"  Wide matrix output: {out_wide_path} ({os.path.getsize(out_wide_path)/1024/1024:.2f} MB, {len(wide_header)} cols)")

# ----------------------------------------------------------------------
# 2. DEDUPLICATE & CONSOLIDATE BGG_DATA_SET.CSV / BGG_DATASET.CSV
# ----------------------------------------------------------------------
def process_bgg_dataset():
    log("Consolidating repeated BGG_Data_Set.csv / bgg_dataset.csv...")
    
    # Build name-to-id mapping from games.csv for missing IDs
    name_to_id = {}
    with open(os.path.join(RAW_DIR, 'games.csv'), 'r', encoding='utf-8', errors='ignore') as f:
        r = csv.reader(f)
        h = next(r)
        id_i, name_i = h.index('BGGId'), h.index('Name')
        for row in r:
            name_to_id[row[name_i].strip().lower()] = row[id_i]

    # Process BGG_Data_Set.csv
    in_path = os.path.join(RAW_DIR, 'BGG_Data_Set.csv')
    out_path = os.path.join(OUT_DIR, 'bgg_dataset_deduped.csv')
    
    seen_ids = set()
    rows_out = []
    recovered_count = 0
    dup_count = 0

    with open(in_path, 'r', encoding='latin-1') as f:
        r = csv.reader(f)
        header = next(r)
        
        # Standardize header names
        clean_header = [
            'BGGId', 'Name', 'YearPublished', 'MinPlayers', 'MaxPlayers',
            'PlayTime', 'MinAge', 'UsersRated', 'RatingAverage', 'BGGRank',
            'ComplexityAverage', 'OwnedUsers', 'Mechanics', 'Domains'
        ]

        for row in r:
            if not row or not any(row):
                continue
            bgg_id = row[0].strip()
            name = row[1].strip()
            
            # Fill missing ID if empty
            if not bgg_id:
                lookup_id = name_to_id.get(name.lower())
                if lookup_id:
                    bgg_id = lookup_id
                    recovered_count += 1
                else:
                    bgg_id = f"UNKNOWN_{name[:10]}"
            
            # Check for duplicate
            if bgg_id in seen_ids:
                dup_count += 1
                continue
            seen_ids.add(bgg_id)
            
            # Clean row values (normalize numbers)
            cleaned_row = [bgg_id] + [col.strip() for col in row[1:]]
            rows_out.append(cleaned_row)

    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(clean_header)
        w.writerows(rows_out)

    log(f"BGG dataset deduplicated: {len(rows_out)} rows saved to {out_path}.")
    log(f"  Recovered {recovered_count} missing IDs, removed {dup_count} duplicates.")

# ----------------------------------------------------------------------
# 3. CONSOLIDATE HISTORICAL RANKINGS (BGG_DB_*.CSV)
# ----------------------------------------------------------------------
def process_ranking_snapshots():
    log("Consolidating repeated ranking snapshots (bgg_db_2017_04, 2018_01, 1806)...")
    
    snapshots = [
        ('2017-04', os.path.join(RAW_DIR, 'bgg_db_2017_04.csv')),
        ('2018-01', os.path.join(RAW_DIR, 'bgg_db_2018_01.csv')),
        ('2018-06', os.path.join(RAW_DIR, 'bgg_db_1806.csv')),
    ]

    out_hist_path = os.path.join(OUT_DIR, 'bgg_rankings_historical.csv')
    out_latest_path = os.path.join(OUT_DIR, 'bgg_rankings_latest.csv')

    all_rows = []
    latest_by_game = {}

    for date_label, file_path in snapshots:
        with open(file_path, 'r', encoding='latin-1') as f:
            r = csv.reader(f)
            header = next(r)
            game_id_idx = header.index('game_id')
            
            for row in r:
                row_with_date = [date_label] + row
                all_rows.append(row_with_date)
                # Keep latest snapshot (chronological order)
                latest_by_game[row[game_id_idx]] = row

    # Save historical time-series
    hist_header = ['snapshot_date'] + header
    with open(out_hist_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(hist_header)
        w.writerows(all_rows)

    # Save latest deduplicated ranking
    with open(out_latest_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(latest_by_game.values())

    log(f"Historical rankings: {len(all_rows)} total snapshot records saved to {out_hist_path}.")
    log(f"Latest rankings deduplicated: {len(latest_by_game)} unique games saved to {out_latest_path}.")

# ----------------------------------------------------------------------
# 4. DEDUPLICATE USER_RATINGS.CSV
# ----------------------------------------------------------------------
def process_user_ratings():
    log("Deduplicating user_ratings.csv (18.9M records)...")
    t0 = time.time()
    
    in_path = os.path.join(RAW_DIR, 'user_ratings.csv')
    out_path = os.path.join(OUT_DIR, 'user_ratings_deduped.csv')

    seen = set()
    total = 0
    dups = 0

    with open(in_path, 'r', encoding='utf-8', errors='ignore') as f_in, \
         open(out_path, 'w', encoding='utf-8', newline='') as f_out:
        
        r = csv.reader(f_in)
        w = csv.writer(f_out)
        
        header = next(r)
        w.writerow(header)
        
        for row in r:
            total += 1
            # Key: (BGGId, Username)
            key = (row[0], row[2])
            if key in seen:
                dups += 1
                continue
            seen.add(key)
            w.writerow(row)
            
            if total % 5000000 == 0:
                log(f"Processed {total:,} user ratings ({dups:,} duplicates skipped)...")

    elapsed = time.time() - t0
    log(f"Completed user ratings in {elapsed:.2f}s.")
    log(f"  Total read: {total:,}, Duplicates removed: {dups:,}, Unique saved: {len(seen):,}")
    log(f"  Output: {out_path} ({os.path.getsize(out_path)/1024/1024:.2f} MB)")

# ----------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------
def main():
    ensure_dir(OUT_DIR)
    log("=== Starting Data Processing Pipeline ===")
    
    # Step 1: Consolidate games feature matrix into Master CSV and Wide Matrix CSV
    process_games_datasets()
    
    # Step 2: Deduplicate repeated BGG_Data_Set / bgg_dataset
    process_bgg_dataset()
    
    # Step 3: Consolidate ranking snapshots
    process_ranking_snapshots()
    
    # Step 4: Deduplicate user_ratings.csv
    process_user_ratings()
    
    log("=== All Processing Finished Successfully ===")

if __name__ == '__main__':
    main()
