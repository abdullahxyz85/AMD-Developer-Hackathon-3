# Single Consolidated Master Dataset: `bgg_master_dataset.csv`

All raw datasets from `raw_data/` have been consolidated, deduplicated, and unified into **EXACTLY ONE CSV FILE**:
📁 **`processed_data/bgg_master_dataset.csv`**

---

## 1. Overview & Statistics

- **Total Rows (Unique Games):** 94,998 games
- **Total Columns:** 77 attributes
- **File Size:** ~105.7 MB
- **Primary Key:** `BGGId`
- **Encoding & Delimiter:** UTF-8, Comma-delimited (standard `,` with standard `.` decimals)

---

## 2. Synthesis of Raw Data Sources

All information across the 16 raw files in `raw_data/` is represented in this single CSV:

1. **Core 2022 Feature Tables (8 files, 21,925 games)**:
   - `games.csv`: Full metadata, player counts, playtimes, weights, community ratings, BGG ranks, and binary categories.
   - `mechanics.csv`: Extracted into human-readable semicolon-delimited `Mechanics` list and `MechanicsCount`.
   - `themes.csv`: Extracted into human-readable semicolon-delimited `Themes` list and `ThemesCount`.
   - `subcategories.csv`: Extracted into human-readable semicolon-delimited `Subcategories` list and `SubcategoriesCount`.
   - `artists_reduced.csv`: Extracted into semicolon-delimited `Artists` list, `ArtistsCount`, and `LowExpArtist`.
   - `designers_reduced.csv`: Extracted into semicolon-delimited `Designers` list, `DesignersCount`, and `LowExpDesigner`.
   - `publishers_reduced.csv`: Extracted into semicolon-delimited `Publishers` list, `PublishersCount`, and `LowExpPublisher`.
   - `ratings_distribution.csv`: Captured as `TotalRatingsDistribution` and `PeakRatingBucket`.

2. **Duplicate Pair (`BGG_Data_Set.csv` & `bgg_dataset.csv`, 20,343 games)**:
   - Semicolon-delimited formatting and duplicate copies merged.
   - Missing IDs recovered by matching game names.
   - Additional columns `Domains` and `BGGRank_2021` mapped.

3. **Temporal Snapshots (`bgg_db_2017_04.csv`, `bgg_db_2018_01.csv`, `bgg_db_1806.csv`, 5,455 games)**:
   - Historical ranks mapped directly to `Rank_2017_04`, `Rank_2018_01`, and `Rank_2018_06`.
   - Verified BGG page links captured in `BGG_URL`.

4. **User Ratings Log (`user_ratings.csv`, 18,942,215 records)**:
   - Aggregated per game: `UserRatings_LoggedCount`, `UserRatings_LoggedMean`, `UserRatings_LoggedMin`, `UserRatings_LoggedMax`.

5. **SQLite Database (`database.sqlite`, 90,400 games)**:
   - Populates game types (`boardgame`, `boardgameexpansion`).
   - Supplies missing/older catalog titles, expansions, descriptions, images, and creator credits for the ~73,000 games outside the 2022 subset.

---

## 3. High-Level Column Layout

1. **Identifiers & Overview (1-7):** `BGGId`, `Name`, `GameType`, `YearPublished`, `Description`, `ImagePath`, `Family`
2. **Gameplay Complexity & Constraints (8-18):** `GameWeight`, `MinPlayers`, `MaxPlayers`, `BestPlayers`, `GoodPlayers`, `ComAgeRec`, `MfgAgeRec`, `LanguageEase`, `MfgPlaytime`, `ComMinPlaytime`, `ComMaxPlaytime`
3. **Core Community Ratings & Engagement (19-27):** `AvgRating`, `BayesAvgRating`, `StdDev`, `NumUserRatings`, `NumComments`, `NumOwned`, `NumWant`, `NumWish`, `NumWeightVotes`
4. **Historical & Category Rankings (28-40):** `Rank:boardgame`, `Rank:strategygames`, `Rank:abstracts`, `Rank:familygames`, `Rank:thematic`, `Rank:cgs`, `Rank:wargames`, `Rank:partygames`, `Rank:childrensgames`, `Rank_2017_04`, `Rank_2018_01`, `Rank_2018_06`, `BGGRank_2021`
5. **Categories & Domains (41-50):** `Categories`, `Domains`, `Cat:Thematic`, `Cat:Strategy`, `Cat:War`, `Cat:Family`, `Cat:CGS`, `Cat:Abstract`, `Cat:Party`, `Cat:Childrens`
6. **Editions & Versions (51-55):** `NumAlternates`, `NumExpansions`, `NumImplementations`, `IsReimplementation`, `Kickstarted`
7. **Mechanics, Themes, & Subcategories (56-61):** `Mechanics`, `MechanicsCount`, `Themes`, `ThemesCount`, `Subcategories`, `SubcategoriesCount`
8. **Creators & Credits (62-70):** `Artists`, `ArtistsCount`, `LowExpArtist`, `Designers`, `DesignersCount`, `LowExpDesigner`, `Publishers`, `PublishersCount`, `LowExpPublisher`
9. **Rating Distribution & Logged Stats (71-76):** `TotalRatingsDistribution`, `PeakRatingBucket`, `UserRatings_LoggedCount`, `UserRatings_LoggedMean`, `UserRatings_LoggedMin`, `UserRatings_LoggedMax`
10. **Direct Link (77):** `BGG_URL`
