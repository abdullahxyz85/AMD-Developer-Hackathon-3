import os
import sqlite3
import pandas as pd
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "aatam.db")
MASTER_CSV = os.path.join(os.path.dirname(__file__), "..", "processed_data", "bgg_master_dataset.csv")
USER_RATINGS_CSV = os.path.join(os.path.dirname(__file__), "..", "raw_data", "user_ratings.csv")

def build_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        print(f"Removing existing database at {DB_PATH}")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating tables...")
    cursor.execute("""
    CREATE TABLE games (
        bgg_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        year_published INTEGER,
        description TEXT,
        image_path TEXT,
        game_weight REAL,
        min_players INTEGER,
        max_players INTEGER,
        best_players TEXT,
        good_players TEXT,
        mfg_playtime INTEGER,
        avg_rating REAL,
        bayes_avg_rating REAL,
        num_ratings INTEGER,
        rank_overall INTEGER,
        categories TEXT,
        domains TEXT,
        mechanics TEXT,
        themes TEXT,
        designers TEXT,
        artists TEXT,
        publishers TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE user_ratings (
        username TEXT NOT NULL,
        bgg_id INTEGER NOT NULL,
        rating REAL,
        played INTEGER DEFAULT 1,
        notes TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (username, bgg_id),
        FOREIGN KEY (bgg_id) REFERENCES games(bgg_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE users (
        username TEXT PRIMARY KEY,
        display_name TEXT,
        bio TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    print(f"Loading master games dataset from {MASTER_CSV}...")
    start_time = time.time()
    
    # Read relevant columns
    cols_to_read = [
        'BGGId', 'Name', 'YearPublished', 'Description', 'ImagePath',
        'GameWeight', 'MinPlayers', 'MaxPlayers', 'BestPlayers', 'GoodPlayers',
        'MfgPlaytime', 'AvgRating', 'BayesAvgRating', 'NumUserRatings',
        'Rank:boardgame', 'Categories', 'Domains', 'Mechanics', 'Themes',
        'Designers', 'Artists', 'Publishers'
    ]
    
    df_games = pd.read_csv(MASTER_CSV, usecols=cols_to_read, low_memory=False)
    
    # Clean up data
    df_games = df_games.rename(columns={
        'BGGId': 'bgg_id',
        'Name': 'name',
        'YearPublished': 'year_published',
        'Description': 'description',
        'ImagePath': 'image_path',
        'GameWeight': 'game_weight',
        'MinPlayers': 'min_players',
        'MaxPlayers': 'max_players',
        'BestPlayers': 'best_players',
        'GoodPlayers': 'good_players',
        'MfgPlaytime': 'mfg_playtime',
        'AvgRating': 'avg_rating',
        'BayesAvgRating': 'bayes_avg_rating',
        'NumUserRatings': 'num_ratings',
        'Rank:boardgame': 'rank_overall',
        'Categories': 'categories',
        'Domains': 'domains',
        'Mechanics': 'mechanics',
        'Themes': 'themes',
        'Designers': 'designers',
        'Artists': 'artists',
        'Publishers': 'publishers'
    })

    # Fill NaNs
    df_games['name'] = df_games['name'].fillna('Unknown Title')
    df_games['description'] = df_games['description'].fillna('')
    df_games['image_path'] = df_games['image_path'].fillna('')
    df_games['mechanics'] = df_games['mechanics'].fillna('')
    df_games['themes'] = df_games['themes'].fillna('')
    df_games['categories'] = df_games['categories'].fillna('')
    df_games['domains'] = df_games['domains'].fillna('')
    df_games['designers'] = df_games['designers'].fillna('')
    df_games['artists'] = df_games['artists'].fillna('')
    df_games['publishers'] = df_games['publishers'].fillna('')
    df_games['best_players'] = df_games['best_players'].fillna('')
    df_games['good_players'] = df_games['good_players'].fillna('')

    df_games.to_sql('games', conn, if_exists='append', index=False)
    print(f"Inserted {len(df_games)} games in {time.time() - start_time:.2f}s")

    # Create indexes for blazing speed
    print("Creating indexes...")
    cursor.execute("CREATE INDEX idx_games_name ON games(name);")
    cursor.execute("CREATE INDEX idx_games_bayes_avg ON games(bayes_avg_rating DESC);")
    cursor.execute("CREATE INDEX idx_games_num_ratings ON games(num_ratings DESC);")
    cursor.execute("CREATE INDEX idx_games_weight ON games(game_weight);")
    cursor.execute("CREATE INDEX idx_user_ratings_user ON user_ratings(username);")
    cursor.execute("CREATE INDEX idx_user_ratings_game ON user_ratings(bgg_id);")

    # Load popular users from user_ratings.csv
    print("Loading active user profiles and plays...")
    # Target top 20 active users from user_ratings
    target_users = {
        'TomVasel': 'Tom Vasel (Dice Tower Founder & Legend)',
        'warta': 'Warta (Heavy Euro Specialist)',
        'oldgoat3769967': 'OldGoat (Classic & Thematic Enthusiast)',
        'loopoocat': 'LoopooCat (Strategy & Engine-Building Fan)',
        'Doel': 'Doel (Area Control & Wargames Tactician)',
        'tachyon14k': 'Tachyon14k (Sci-Fi & Card Game Buff)',
        'Tonydorrf': 'Tony Dorrf (Family & Gateway Game Curator)',
        'The Eraser': 'The Eraser (All-Round Board Game Veteran)'
    }

    # Insert users
    for u, bio in target_users.items():
        cursor.execute("INSERT OR IGNORE INTO users (username, display_name, bio) VALUES (?, ?, ?)", (u, u, bio))

    # Also add a default guest/personal profile
    cursor.execute("INSERT OR IGNORE INTO users (username, display_name, bio) VALUES (?, ?, ?)", 
                   ("PlayerOne", "Player One (You)", "Personal Collection & Game Diary"))

    # Read user ratings for target users
    chunk_size = 200000
    matched_ratings = 0
    valid_game_ids = set(df_games['bgg_id'])
    
    print("Sampling ratings for target users from user_ratings.csv...")
    if os.path.exists(USER_RATINGS_CSV):
        for chunk in pd.read_csv(USER_RATINGS_CSV, chunksize=chunk_size, nrows=2500000):
            filtered = chunk[chunk['Username'].isin(target_users.keys())]
            if not filtered.empty:
                rows_to_insert = []
                for _, row in filtered.iterrows():
                    gid = int(row['BGGId'])
                    if gid in valid_game_ids:
                        rows_to_insert.append((str(row['Username']), gid, float(row['Rating']), 1, ""))
                if rows_to_insert:
                    cursor.executemany("""
                    INSERT OR IGNORE INTO user_ratings (username, bgg_id, rating, played, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """, rows_to_insert)
                    matched_ratings += len(rows_to_insert)
        print(f"Inserted {matched_ratings} user ratings for key users.")

    # Populate some starter plays for PlayerOne
    starter_plays = [
        ("PlayerOne", 13, 9.0, 1, "Classic trading and settling with friends. Always love 8 and 6 ore!"), # Catan
        ("PlayerOne", 822, 8.5, 1, "Snatching meeples on cities never gets old."), # Carcassonne
        ("PlayerOne", 167791, 10.0, 1, "Masterpiece engine builder! Tharsis board is epic."), # Terraforming Mars
        ("PlayerOne", 148228, 8.0, 1, "Quick, snappy gem engine."), # Splendor
        ("PlayerOne", 30549, 8.5, 1, "Intense cooperative eradication! Outbreaks give heart attacks."), # Pandemic
        ("PlayerOne", 178900, 9.0, 1, "Best party word game ever made.") # Codenames
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO user_ratings (username, bgg_id, rating, played, notes)
    VALUES (?, ?, ?, ?, ?)
    """, starter_plays)

    conn.commit()
    conn.close()
    print("Database build complete and optimized!")

if __name__ == "__main__":
    build_database()
