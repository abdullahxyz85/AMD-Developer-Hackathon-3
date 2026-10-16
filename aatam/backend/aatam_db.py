import os
import io
import re
import json
import mmap
import struct
import hashlib
import secrets
import threading
from datetime import datetime
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CUSTOM_DB_DIR = os.path.join(PROJECT_DIR, "data", "aatam_custom_db")

class AatamDB:
    """
    Custom-built, high-performance hybrid columnar & document database engine
    designed specifically for board game catalogs, taste vectors, and gamer shelves.
    """
    def __init__(self, db_dir: str = CUSTOM_DB_DIR):
        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)
        
        self.data_file_path = os.path.join(self.db_dir, "games_store.bin")
        self.index_file_path = os.path.join(self.db_dir, "games_offset.idx")
        self.columns_file_path = os.path.join(self.db_dir, "columnar_cache.npz")
        self.inverted_idx_path = os.path.join(self.db_dir, "text_inverted.json")
        self.users_file_path = os.path.join(self.db_dir, "users_shelf.json")
        self._users_file_mtime = 0

        self._lock = threading.RLock()
        
        # In-memory indices & columnar arrays
        self.offset_index: Dict[int, Tuple[int, int]] = {} # bgg_id -> (byte_offset, byte_length)
        self.inverted_index: Dict[str, List[int]] = {}     # keyword -> list of bgg_id
        self.columnar_data: Dict[str, np.ndarray] = {}     # column_name -> np.ndarray
        self.id_to_col_idx: Dict[int, int] = {}            # bgg_id -> row index in columnar arrays
        self.users_shelf: Dict[str, Any] = {}              # username -> {user_info, plays: {bgg_id: {...}}}
        
        self._data_fp = None
        self._is_loaded = False
        
        if os.path.exists(self.data_file_path) and os.path.exists(self.index_file_path):
            self.load()

    def build_from_csv(self, csv_path: str, user_ratings_csv: str = None):
        """Build the custom database from the master dataset."""
        import pandas as pd
        print(f"[AatamDB] Building custom database from {csv_path}...")

        cols_to_read = [
            'BGGId', 'Name', 'YearPublished', 'Description', 'ImagePath',
            'Components', 'HowToPlay', 'WinningStrategies',
            'GameWeight', 'MinPlayers', 'MaxPlayers', 'BestPlayers', 'GoodPlayers',
            'MfgPlaytime', 'AvgRating', 'BayesAvgRating', 'NumUserRatings',
            'Categories', 'Domains', 'Mechanics', 'Themes',
            'Designers', 'Artists', 'Publishers'
        ]
        # Allow missing if legacy CSV
        all_cols = pd.read_csv(csv_path, nrows=1).columns.tolist()
        cols_present = [c for c in cols_to_read if c in all_cols]
        df = pd.read_csv(csv_path, usecols=cols_present, low_memory=False)

        # Pre-process columns
        df['BGGId'] = df['BGGId'].astype(int)
        df['Name'] = df['Name'].fillna('Unknown Title')
        df['Description'] = df['Description'].fillna('')
        df['Components'] = df['Components'].fillna('') if 'Components' in df.columns else ''
        df['HowToPlay'] = df['HowToPlay'].fillna('') if 'HowToPlay' in df.columns else ''
        df['WinningStrategies'] = df['WinningStrategies'].fillna('') if 'WinningStrategies' in df.columns else ''
        df['ImagePath'] = df['ImagePath'].fillna('')
        df['Mechanics'] = df['Mechanics'].fillna('')
        df['Themes'] = df['Themes'].fillna('')
        df['Categories'] = df['Categories'].fillna('')
        df['Domains'] = df['Domains'].fillna('')
        df['Designers'] = df['Designers'].fillna('')
        df['Artists'] = df['Artists'].fillna('')
        df['Publishers'] = df['Publishers'].fillna('')
        df['BestPlayers'] = df['BestPlayers'].fillna('')
        df['YearPublished'] = df['YearPublished'].fillna(2000).astype(int)
        df['GameWeight'] = df['GameWeight'].fillna(2.5).astype(float)
        df['MinPlayers'] = df['MinPlayers'].fillna(1).astype(int)
        df['MaxPlayers'] = df['MaxPlayers'].fillna(4).astype(int)
        df['MfgPlaytime'] = df['MfgPlaytime'].fillna(45).astype(int)
        df['AvgRating'] = df['AvgRating'].fillna(6.0).astype(float)
        df['BayesAvgRating'] = df['BayesAvgRating'].fillna(5.5).astype(float)
        df['NumUserRatings'] = df['NumUserRatings'].fillna(0).astype(int)

        n_records = len(df)
        print(f"[AatamDB] Ingesting {n_records} game records into custom document storage...")

        # 1. Write binary record store & compute byte offsets
        offsets = {}
        inverted_idx = {}
        
        with open(self.data_file_path, "wb") as f_out:
            for idx, row in df.iterrows():
                bgg_id = int(row['BGGId'])
                record = {
                    "bgg_id": bgg_id,
                    "name": row['Name'],
                    "year_published": int(row['YearPublished']),
                    "description": row['Description'],
                    "components": row['Components'],
                    "how_to_play": row['HowToPlay'],
                    "winning_strategies": row['WinningStrategies'],
                    "image_path": row['ImagePath'],
                    "game_weight": float(row['GameWeight']),
                    "min_players": int(row['MinPlayers']),
                    "max_players": int(row['MaxPlayers']),
                    "best_players": str(row['BestPlayers']),
                    "mfg_playtime": int(row['MfgPlaytime']),
                    "avg_rating": float(row['AvgRating']),
                    "bayes_avg_rating": float(row['BayesAvgRating']),
                    "num_ratings": int(row['NumUserRatings']),
                    "categories": row['Categories'],
                    "domains": row['Domains'],
                    "mechanics": row['Mechanics'],
                    "themes": row['Themes'],
                    "designers": row['Designers'],
                    "artists": row['Artists'],
                    "publishers": row['Publishers']
                }
                
                raw_bytes = json.dumps(record, ensure_ascii=False).encode('utf-8')
                byte_offset = f_out.tell()
                byte_length = len(raw_bytes)
                f_out.write(raw_bytes)
                offsets[bgg_id] = (byte_offset, byte_length)

                # Tokenize for inverted index
                tokens = set(re.findall(r'[a-z0-9]{2,}', row['Name'].lower()))
                for m in row['Mechanics'].split(';'):
                    tokens.update(re.findall(r'[a-z0-9]{2,}', m.lower()))
                for t in row['Themes'].split(';'):
                    tokens.update(re.findall(r'[a-z0-9]{2,}', t.lower()))

                for tok in tokens:
                    if tok not in inverted_idx:
                        inverted_idx[tok] = []
                    inverted_idx[tok].append(bgg_id)

        # 2. Write binary index table: [bgg_id: int64, offset: int64, length: int32]
        print(f"[AatamDB] Writing primary key index file...")
        with open(self.index_file_path, "wb") as f_idx:
            f_idx.write(struct.pack("<I", len(offsets))) # count
            for bgg_id, (off, length) in offsets.items():
                f_idx.write(struct.pack("<qqi", bgg_id, off, length))

        # 3. Write columnar numpy cache
        print(f"[AatamDB] Compressing columnar arrays for vectorized queries...")
        np.savez_compressed(
            self.columns_file_path,
            bgg_ids=df['BGGId'].to_numpy(dtype=np.int64),
            bayes_avg_ratings=df['BayesAvgRating'].to_numpy(dtype=np.float32),
            avg_ratings=df['AvgRating'].to_numpy(dtype=np.float32),
            game_weights=df['GameWeight'].to_numpy(dtype=np.float32),
            num_ratings=df['NumUserRatings'].to_numpy(dtype=np.int32),
            min_players=df['MinPlayers'].to_numpy(dtype=np.int16),
            max_players=df['MaxPlayers'].to_numpy(dtype=np.int16),
            year_published=df['YearPublished'].to_numpy(dtype=np.int16)
        )

        # 4. Write inverted index
        print(f"[AatamDB] Saving inverted text index with {len(inverted_idx)} terms...")
        with open(self.inverted_idx_path, "w", encoding="utf-8") as f_inv:
            json.dump(inverted_idx, f_inv)

        # 5. Initialize user plays
        self._init_users_shelf(user_ratings_csv, df)

        print("[AatamDB] Database build complete!")
        self.load()

    def _reload_users_shelf_if_changed(self):
        """Auto-reload users_shelf if the file on disk was modified."""
        if os.path.exists(self.users_file_path):
            try:
                mtime = os.path.getmtime(self.users_file_path)
                if not hasattr(self, '_users_file_mtime') or mtime > self._users_file_mtime:
                    with open(self.users_file_path, "r", encoding="utf-8") as f_u:
                        self.users_shelf = json.load(f_u)
                    self._users_file_mtime = mtime
            except Exception:
                pass

    def _persist_users_shelf(self):
        """Write users_shelf to disk and refresh the tracked mtime."""
        with open(self.users_file_path, "w", encoding="utf-8") as f:
            json.dump(self.users_shelf, f, indent=2)
        try:
            self._users_file_mtime = os.path.getmtime(self.users_file_path)
        except OSError:
            pass

    def _resolve_username_key(self, username: str) -> Optional[str]:
        """Return the canonical shelf key for a username (case-insensitive)."""
        if not username:
            return None
        if username in self.users_shelf:
            return username
        target = username.strip().lower()
        for key in self.users_shelf:
            if key.lower() == target:
                return key
        return None

    def _safe_user_info(self, user_info: Optional[Dict[str, Any]], username: str = "") -> Dict[str, Any]:
        """Return a copy of user_info without password material."""
        safe = dict(user_info or {"username": username, "display_name": username or "Guest"})
        safe.pop("salt", None)
        safe.pop("password_hash", None)
        return safe

    def _init_users_shelf(self, user_ratings_csv: str = None, df_games: Any = None):
        default_salt = "4a8b1c2d3e4f5a6b7c8d9e0f1a2b3c4d"
        default_hash = "70a20a1e6b7d1fc7dbbd7f15c8e8278b47987833f65674ab7cef90583f9f7f8d"
        users_shelf = {
            "PlayerOne": {
                "user_info": {
                    "username": "PlayerOne",
                    "email": "playerone@tabletop.com",
                    "display_name": "Player One (You)",
                    "bio": "Personal Collection & Game Diary",
                    "salt": default_salt,
                    "password_hash": default_hash
                },
                "plays": {
                    13: {"rating": 9.0, "played": 1, "notes": "Classic trading and settling with friends. Always love 8 and 6 ore!"},
                    822: {"rating": 8.5, "played": 1, "notes": "Snatching meeples on cities never gets old."},
                    167791: {"rating": 10.0, "played": 1, "notes": "Masterpiece engine builder! Tharsis board is epic."},
                    148228: {"rating": 8.0, "played": 1, "notes": "Quick, snappy gem engine."},
                    30549: {"rating": 8.5, "played": 1, "notes": "Intense cooperative eradication!"},
                    178900: {"rating": 9.0, "played": 1, "notes": "Best party word game ever made."}
                }
            },
            "TomVasel": {
                "user_info": {
                    "username": "TomVasel",
                    "email": "tomvasel@tabletop.com",
                    "display_name": "Tom Vasel",
                    "bio": "The Dice Tower Founder & Board Game Critic",
                    "salt": default_salt,
                    "password_hash": default_hash
                },
                "plays": {
                    13: {"rating": 8.0, "played": 1, "notes": "The game that started modern hobby board gaming for many."},
                    30549: {"rating": 9.0, "played": 1, "notes": "Phenomenal co-op tension."},
                    68448: {"rating": 8.5, "played": 1, "notes": "Great simultaneous drafting."},
                    178900: {"rating": 9.5, "played": 1, "notes": "Incredible social deduction and word association."}
                }
            }
        }
        # Preserve registered accounts across DB rebuilds (do not wipe passwords).
        if os.path.exists(self.users_file_path):
            try:
                with open(self.users_file_path, "r", encoding="utf-8") as f_existing:
                    existing = json.load(f_existing)
                for key, data in existing.items():
                    u_info = (data or {}).get("user_info", {})
                    if key in ("PlayerOne", "TomVasel"):
                        continue
                    if u_info.get("password_hash") and u_info.get("salt"):
                        users_shelf[key] = data
            except Exception:
                pass
        with open(self.users_file_path, "w", encoding="utf-8") as f:
            json.dump(users_shelf, f, indent=2)
        try:
            self._users_file_mtime = os.path.getmtime(self.users_file_path)
        except OSError:
            pass

    def load(self):
        """Loads memory indices, columnar vectors, and opens memory-mapped store."""
        with self._lock:
            # 1. Read primary offset index
            self.offset_index = {}
            with open(self.index_file_path, "rb") as f_idx:
                count_bytes = f_idx.read(4)
                if count_bytes:
                    count = struct.unpack("<I", count_bytes)[0]
                    for _ in range(count):
                        bgg_id, off, length = struct.unpack("<qqi", f_idx.read(20))
                        self.offset_index[bgg_id] = (off, length)

            # 2. Open data file
            if self._data_fp:
                self._data_fp.close()
            self._data_fp = open(self.data_file_path, "rb")

            # 3. Load columnar data
            if os.path.exists(self.columns_file_path):
                npz = np.load(self.columns_file_path)
                self.columnar_data = {k: npz[k] for k in npz.files}
                bgg_ids = self.columnar_data["bgg_ids"]
                self.id_to_col_idx = {bgg_ids[i]: i for i in range(len(bgg_ids))}

            # 4. Load inverted index
            if os.path.exists(self.inverted_idx_path):
                with open(self.inverted_idx_path, "r", encoding="utf-8") as f_inv:
                    self.inverted_index = json.load(f_inv)

            # 5. Load users shelf
            if os.path.exists(self.users_file_path):
                with open(self.users_file_path, "r", encoding="utf-8") as f_u:
                    self.users_shelf = json.load(f_u)
                self._users_file_mtime = os.path.getmtime(self.users_file_path)

            self._is_loaded = True
            print(f"[AatamDB] Engine online: {len(self.offset_index):,} records mapped.")

    def find_one(self, bgg_id: int) -> Optional[Dict[str, Any]]:
        """Fast $O(1)$ random seek by BGG ID, with fallback to community submissions."""
        with self._lock:
            if bgg_id in self.offset_index:
                off, length = self.offset_index[bgg_id]
                self._data_fp.seek(off)
                raw = self._data_fp.read(length)
                return json.loads(raw.decode('utf-8'))
            
            # Check community submissions
            subs = self.get_all_submissions()
            for s in subs:
                if s.get("bgg_id") == bgg_id:
                    return dict(s)
            return None

    def query(self,
              q: Optional[str] = None,
              category: Optional[str] = None,
              mechanic: Optional[str] = None,
              min_weight: Optional[float] = None,
              max_weight: Optional[float] = None,
              players: Optional[int] = None,
              sort_by: str = "bayes_avg_rating",
              order: str = "desc",
              limit: int = 24,
              offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        High-performance hybrid query combining inverted index lookup
        with vectorized columnar boolean masks.
        """
        with self._lock:
            if not self._is_loaded:
                return [], 0

            # 1. Base candidate set
            candidates: Optional[Set[int]] = None

            # Inverted text search for query tokens
            if q:
                tokens = re.findall(r'[a-z0-9]{2,}', q.lower())
                for tok in tokens:
                    matching = set(self.inverted_index.get(tok, []))
                    if candidates is None:
                        candidates = matching
                    else:
                        candidates = candidates.intersection(matching)
                if candidates is not None and len(candidates) == 0:
                    return [], 0

            # Vectorized columnar filtering using NumPy
            mask = np.ones(len(self.columnar_data["bgg_ids"]), dtype=bool)

            if min_weight is not None:
                mask &= (self.columnar_data["game_weights"] >= min_weight)
            if max_weight is not None:
                mask &= (self.columnar_data["game_weights"] <= max_weight)
            if players is not None:
                mask &= (self.columnar_data["min_players"] <= players) & (self.columnar_data["max_players"] >= players)

            # If candidates set exists from text query, apply mask
            if candidates is not None:
                cand_indices = [self.id_to_col_idx[gid] for gid in candidates if gid in self.id_to_col_idx]
                cand_mask = np.zeros(len(mask), dtype=bool)
                cand_mask[cand_indices] = True
                mask &= cand_mask

            valid_indices = np.where(mask)[0]
            if len(valid_indices) == 0:
                return [], 0

            # Vectorized sorting
            col_map = {
                "bayes_avg_rating": "bayes_avg_ratings",
                "avg_rating": "avg_ratings",
                "num_ratings": "num_ratings",
                "year_published": "year_published"
            }
            sort_col = col_map.get(sort_by, "bayes_avg_ratings")
            sort_vals = self.columnar_data[sort_col][valid_indices]
            
            sorted_sub_indices = np.argsort(sort_vals)
            if order.lower() == "desc":
                sorted_sub_indices = sorted_sub_indices[::-1]

            sorted_indices = valid_indices[sorted_sub_indices]

            # Category / Mechanic sub-filtering (applied on sorted candidates)
            final_bgg_ids = []
            bgg_id_arr = self.columnar_data["bgg_ids"]

            cat_lower = category.lower() if category else None
            mech_lower = mechanic.lower() if mechanic else None

            for idx in sorted_indices:
                gid = int(bgg_id_arr[idx])
                if cat_lower or mech_lower:
                    rec = self.find_one(gid)
                    if not rec:
                        continue
                    if cat_lower and cat_lower not in (rec.get("categories", "") + rec.get("domains", "")).lower():
                        continue
                    if mech_lower and mech_lower not in rec.get("mechanics", "").lower():
                        continue
                final_bgg_ids.append(gid)

            total_count = len(final_bgg_ids)
            paged_ids = final_bgg_ids[offset : offset + limit]

            # Fetch document records
            results = [self.find_one(gid) for gid in paged_ids]
            return [r for r in results if r], total_count

    # ---------------------------------------------
    # USER SHELF & PLAYS MANAGEMENT
    # ---------------------------------------------
    def get_users(self) -> List[Dict[str, Any]]:
        with self._lock:
            self._reload_users_shelf_if_changed()
            result = []
            for username, data in self.users_shelf.items():
                u_info = data.get("user_info", {})
                result.append({
                    "username": username,
                    "display_name": u_info.get("display_name", username),
                    "bio": u_info.get("bio", "Board Game Enthusiast"),
                    "total_ratings": len(data.get("plays", {}))
                })
            return sorted(result, key=lambda x: x["total_ratings"], reverse=True)

    def get_user_shelf(self, username: str) -> Dict[str, Any]:
        with self._lock:
            self._reload_users_shelf_if_changed()
            key = self._resolve_username_key(username)
            user_data = self.users_shelf.get(key) if key else None
            if not user_data:
                # Default guest
                user_data = {
                    "user_info": {"username": username, "display_name": username, "bio": "Gamer Explorer"},
                    "plays": {}
                }

            plays_dict = user_data.get("plays", {})
            full_plays = []
            for gid_str, play_info in plays_dict.items():
                gid = int(gid_str)
                game = self.find_one(gid)
                if game:
                    merged = dict(game)
                    merged["rating"] = play_info.get("rating")
                    merged["played"] = play_info.get("played", 1)
                    merged["notes"] = play_info.get("notes", "")
                    full_plays.append(merged)

            full_plays.sort(key=lambda x: (x.get("rating") or 0, x.get("bayes_avg_rating") or 0), reverse=True)
            return {
                "user": self._safe_user_info(user_data.get("user_info"), username),
                "plays": full_plays
            }

    def save_user_play(self, username: str, bgg_id: int, rating: float, played: int = 1, notes: str = ""):
        with self._lock:
            self._reload_users_shelf_if_changed()
            key = self._resolve_username_key(username) or username.strip()
            if key not in self.users_shelf:
                self.users_shelf[key] = {
                    "user_info": {"username": key, "display_name": key, "bio": "Gamer Explorer"},
                    "plays": {}
                }
            self.users_shelf[key]["plays"][str(bgg_id)] = {
                "rating": float(rating),
                "played": int(played),
                "notes": notes
            }
            self._persist_users_shelf()

    def delete_user_play(self, username: str, bgg_id: int):
        with self._lock:
            self._reload_users_shelf_if_changed()
            key = self._resolve_username_key(username)
            if key and str(bgg_id) in self.users_shelf[key].get("plays", {}):
                del self.users_shelf[key]["plays"][str(bgg_id)]
                self._persist_users_shelf()

    # ---------------------------------------------
    # AUTHENTICATION & USER ACCOUNTS (EMAIL SIGNUP)
    # ---------------------------------------------
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if not salt:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            bytes.fromhex(salt),
            100000
        ).hex()
        return salt, pwd_hash

    def _verify_password(self, password: str, salt: str, expected_hash: str) -> bool:
        if not password or not salt or not expected_hash:
            return False
        try:
            _, computed = self._hash_password(password, salt)
            return secrets.compare_digest(computed, expected_hash)
        except (ValueError, TypeError):
            return False

    def create_account(self, email: str, username: str, password: str, display_name: Optional[str] = None, bio: Optional[str] = None, played_games: Optional[List[int]] = None) -> Dict[str, Any]:
        """Create a new user account with validated email, username, salted password, and optional onboarding played games."""
        email = email.strip().lower()
        username = username.strip()

        # Validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Please provide a valid email address.")
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        with self._lock:
            self._reload_users_shelf_if_changed()
            # Check if username or email exists
            for u, data in self.users_shelf.items():
                u_info = data.get("user_info", {})
                if u.lower() == username.lower():
                    raise ValueError(f"Username '{username}' is already taken.")
                if u_info.get("email", "").lower() == email:
                    raise ValueError(f"An account with email '{email}' already exists.")

            salt, pwd_hash = self._hash_password(password)
            user_info = {
                "username": username,
                "email": email,
                "display_name": display_name or username,
                "bio": bio or "Passionate board gamer exploring new tabletop horizons.",
                "salt": salt,
                "password_hash": pwd_hash,
                "created_at": datetime.utcnow().isoformat()
            }

            plays = {}
            if played_games:
                for gid in played_games:
                    gid_int = int(gid)
                    plays[str(gid_int)] = {
                        "rating": 8.5,
                        "played": 1,
                        "notes": "Added during onboarding."
                    }

            self.users_shelf[username] = {
                "user_info": user_info,
                "plays": plays
            }

            self._persist_users_shelf()

            token = self._create_session(username)
            return {
                "user": self._safe_user_info(user_info, username),
                "token": token
            }

    def login(self, login_id: str, password: str) -> Dict[str, Any]:
        """Authenticate user by email or username."""
        login_id_clean = login_id.strip().lower()
        with self._lock:
            self._reload_users_shelf_if_changed()
            matches = []

            for u, data in self.users_shelf.items():
                u_info = data.get("user_info", {})
                if u.lower() == login_id_clean or u_info.get("email", "").lower() == login_id_clean:
                    matches.append((u, data))

            if not matches:
                raise ValueError("No account found with this email or username. Please sign up to create an account.")

            # Prefer the record that actually has password credentials (avoids
            # case-variant shelf duplicates created by play logging).
            matches.sort(
                key=lambda item: (
                    0 if item[1].get("user_info", {}).get("password_hash") else 1,
                    0 if item[1].get("user_info", {}).get("salt") else 1,
                )
            )
            target_username, target_data = matches[0]

            u_info = target_data.get("user_info", {})
            salt = u_info.get("salt")
            pwd_hash = u_info.get("password_hash")

            if not salt or not pwd_hash:
                raise ValueError(
                    "This username has not been registered as an account yet. Please sign up with your email."
                )

            if not self._verify_password(password, salt, pwd_hash):
                raise ValueError("Incorrect password. Please verify your credentials.")

            # Drop password-less case-variant duplicates that would shadow this account.
            for dup_key, _ in matches[1:]:
                dup_info = self.users_shelf.get(dup_key, {}).get("user_info", {})
                if not dup_info.get("password_hash"):
                    dup_plays = self.users_shelf.get(dup_key, {}).get("plays", {})
                    if dup_plays:
                        target_plays = self.users_shelf[target_username].setdefault("plays", {})
                        for gid, play in dup_plays.items():
                            if gid not in target_plays:
                                target_plays[gid] = play
                    del self.users_shelf[dup_key]
                    self._persist_users_shelf()

            token = self._create_session(target_username)
            return {
                "user": self._safe_user_info(u_info, target_username),
                "token": token
            }

    def _create_session(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        sessions_path = os.path.join(self.db_dir, "sessions.json")
        sessions = {}
        if os.path.exists(sessions_path):
            try:
                with open(sessions_path, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
            except Exception:
                sessions = {}
        sessions[token] = {
            "username": username,
            "created_at": datetime.utcnow().isoformat()
        }
        with open(sessions_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)
        return token

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        sessions_path = os.path.join(self.db_dir, "sessions.json")
        if not os.path.exists(sessions_path):
            return None
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            sess = sessions.get(token)
            if not sess:
                return None
            username = sess["username"]
            with self._lock:
                self._reload_users_shelf_if_changed()
                key = self._resolve_username_key(username)
                user_data = self.users_shelf.get(key) if key else None
                if not user_data:
                    return None
                return self._safe_user_info(user_data.get("user_info"), key or username)
        except Exception:
            return None

    def logout(self, token: str) -> bool:
        sessions_path = os.path.join(self.db_dir, "sessions.json")
        if not os.path.exists(sessions_path):
            return True
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            if token in sessions:
                del sessions[token]
                with open(sessions_path, "w", encoding="utf-8") as f:
                    json.dump(sessions, f, indent=2)
            return True
        except Exception:
            return False

    # ---------------------------------------------
    # COMMUNITY GAME SUBMISSIONS & WINNING TIPS
    # ---------------------------------------------
    def get_submissions_file_path(self) -> str:
        return os.path.join(self.db_dir, "submissions.json")

    def get_all_submissions(self) -> List[Dict[str, Any]]:
        p = self.get_submissions_file_path()
        if not os.path.exists(p):
            return []
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def check_is_duplicate_game(self, game_name: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if game name already exists in database or prior submissions."""
        clean_target = re.sub(r'[^a-zA-Z0-9]', '', game_name).lower()
        if not clean_target:
            return False, None

        # Check existing catalog via inverted index or query
        rows, _ = self.query(q=game_name, limit=10)
        for r in rows:
            clean_existing = re.sub(r'[^a-zA-Z0-9]', '', r.get("name", "")).lower()
            if clean_target == clean_existing:
                return True, r

        # Check existing user submissions
        subs = self.get_all_submissions()
        for s in subs:
            clean_sub = re.sub(r'[^a-zA-Z0-9]', '', s.get("name", "")).lower()
            if clean_target == clean_sub:
                return True, s

        return False, None

    def submit_game(self, submission_data: Dict[str, Any], username: str) -> Dict[str, Any]:
        """Validate, verify non-duplicate, and save a user's submitted game with strategy & winning tips."""
        game_name = submission_data.get("name", "").strip()
        if len(game_name) < 2:
            raise ValueError("Game title must be at least 2 characters long.")

        is_dup, existing = self.check_is_duplicate_game(game_name)
        if is_dup:
            existing_title = existing.get("name", game_name)
            raise ValueError(f"Game already exists in Aatam Wiki catalog as '{existing_title}'. Cannot submit duplicates.")

        with self._lock:
            subs = self.get_all_submissions()
            sub_id = 900000 + len(subs) + 1
            
            entry = {
                "bgg_id": sub_id,
                "name": game_name,
                "year_published": submission_data.get("year_published") or datetime.utcnow().year,
                "min_players": int(submission_data.get("min_players") or 2),
                "max_players": int(submission_data.get("max_players") or 4),
                "mfg_playtime": int(submission_data.get("mfg_playtime") or 45),
                "game_weight": float(submission_data.get("game_weight") or 2.5),
                "categories": submission_data.get("categories", "Strategy; Thematic"),
                "mechanics": submission_data.get("mechanics", "Hand Management; Action Selection"),
                "description": submission_data.get("description", "Community submitted board game."),
                "image_path": submission_data.get("image_path") or "/static/images/placeholder.jpg",
                "submitted_by": username,
                "how_i_won": submission_data.get("how_i_won", "Balanced economy and early development."),
                "winning_tips": submission_data.get("winning_tips", "Watch opponents' turn tempo and conserve actions."),
                "submitted_at": datetime.utcnow().isoformat(),
                "bayes_avg_rating": 8.0,
                "avg_rating": 8.0,
                "num_ratings": 1
            }

            subs.insert(0, entry)
            with open(self.get_submissions_file_path(), "w", encoding="utf-8") as f:
                json.dump(subs, f, indent=2)

            return entry

# Global singleton
aatam_db = AatamDB()
