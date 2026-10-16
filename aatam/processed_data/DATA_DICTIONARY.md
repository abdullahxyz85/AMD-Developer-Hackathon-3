# Data Dictionary: `bgg_master_dataset.csv`

Complete schema definition for all 77 columns in the single consolidated dataset (94,998 games).

| # | Column Name | Type | Description |
| :-: | :--- | :--- | :--- |
| 1 | `BGGId` | Integer / String | Unique BoardGameGeek game ID (Primary Key) |
| 2 | `Name` | String | Official game title |
| 3 | `GameType` | String | Classification: `boardgame` or `boardgameexpansion` |
| 4 | `YearPublished` | Integer | First publication year |
| 5 | `Description` | Text | Synopsis of gameplay and theme |
| 6 | `ImagePath` | String | URL to cover image on BoardGameGeek |
| 7 | `Family` | String | BGG game series/family |
| 8 | `GameWeight` | Float | Community complexity rating (1.0 to 5.0 scale) |
| 9 | `MinPlayers` | Integer | Minimum required players |
| 10 | `MaxPlayers` | Integer | Maximum supported players |
| 11 | `BestPlayers` | Integer / String | Community voted best player count |
| 12 | `GoodPlayers` | String (JSON list) | Community recommended player counts |
| 13 | `ComAgeRec` | Float | Community minimum age recommendation |
| 14 | `MfgAgeRec` | Integer | Manufacturer stated minimum age |
| 15 | `LanguageEase` | Float | Language dependence difficulty score |
| 16 | `MfgPlaytime` | Integer | Manufacturer stated playtime in minutes |
| 17 | `ComMinPlaytime` | Integer | Community minimum playtime in minutes |
| 18 | `ComMaxPlaytime` | Integer | Community maximum playtime in minutes |
| 19 | `AvgRating` | Float | Arithmetic mean user rating (1.0 to 10.0 scale) |
| 20 | `BayesAvgRating` | Float | Geek Rating / Bayesian weighted average |
| 21 | `StdDev` | Float | Standard deviation of user ratings |
| 22 | `NumUserRatings` | Integer | Total count of user ratings |
| 23 | `NumComments` | Integer | Total user comments posted |
| 24 | `NumOwned` | Integer | Total users owning the game |
| 25 | `NumWant` | Integer | Total users wanting the game |
| 26 | `NumWish` | Integer | Total users wishlisting the game |
| 27 | `NumWeightVotes` | Integer | Total votes on complexity weight |
| 28 | `Rank:boardgame` | Integer | Overall BoardGameGeek leaderboard rank |
| 29 | `Rank:strategygames` | Integer | Leaderboard rank in Strategy Games |
| 30 | `Rank:abstracts` | Integer | Leaderboard rank in Abstract Games |
| 31 | `Rank:familygames` | Integer | Leaderboard rank in Family Games |
| 32 | `Rank:thematic` | Integer | Leaderboard rank in Thematic Games |
| 33 | `Rank:cgs` | Integer | Leaderboard rank in Customizable Games |
| 34 | `Rank:wargames` | Integer | Leaderboard rank in Wargames |
| 35 | `Rank:partygames` | Integer | Leaderboard rank in Party Games |
| 36 | `Rank:childrensgames`| Integer | Leaderboard rank in Children's Games |
| 37 | `Rank_2017_04` | Integer / Empty | Snapshot rank as of April 2017 |
| 38 | `Rank_2018_01` | Integer / Empty | Snapshot rank as of January 2018 |
| 39 | `Rank_2018_06` | Integer / Empty | Snapshot rank as of June 2018 |
| 40 | `BGGRank_2021` | Integer / Empty | BGG rank from 2021 dataset |
| 41 | `Categories` | String | Semicolon-delimited high-level categories |
| 42 | `Domains` | String | Delimited game domains (e.g. Strategy Games) |
| 43 | `Cat:Thematic` | Binary (0/1) | Flag: Thematic category |
| 44 | `Cat:Strategy` | Binary (0/1) | Flag: Strategy category |
| 45 | `Cat:War` | Binary (0/1) | Flag: War category |
| 46 | `Cat:Family` | Binary (0/1) | Flag: Family category |
| 47 | `Cat:CGS` | Binary (0/1) | Flag: Customizable / Card Games category |
| 48 | `Cat:Abstract` | Binary (0/1) | Flag: Abstract category |
| 49 | `Cat:Party` | Binary (0/1) | Flag: Party category |
| 50 | `Cat:Childrens` | Binary (0/1) | Flag: Children's category |
| 51 | `NumAlternates` | Integer | Count of alternate editions |
| 52 | `NumExpansions` | Integer | Count of expansion releases |
| 53 | `NumImplementations` | Integer | Count of reimplementations |
| 54 | `IsReimplementation` | Binary (0/1) | Flag: Is a reimplementation |
| 55 | `Kickstarted` | Binary (0/1) | Flag: Funded via Kickstarter |
| 56 | `Mechanics` | String | Semicolon-separated list of gameplay mechanics |
| 57 | `MechanicsCount` | Integer | Total mechanics tagged |
| 58 | `Themes` | String | Semicolon-separated thematic genres |
| 59 | `ThemesCount` | Integer | Total themes tagged |
| 60 | `Subcategories` | String | Semicolon-separated subcategories |
| 61 | `SubcategoriesCount` | Integer | Total subcategories tagged |
| 62 | `Artists` | String | Semicolon-separated credited artists |
| 63 | `ArtistsCount` | Integer | Total artists credited |
| 64 | `LowExpArtist` | Binary (0/1) | Flag: Has unlisted/emerging artist (<= 3 games) |
| 65 | `Designers` | String | Semicolon-separated credited designers |
| 66 | `DesignersCount` | Integer | Total designers credited |
| 67 | `LowExpDesigner` | Binary (0/1) | Flag: Has unlisted/emerging designer (<= 3 games) |
| 68 | `Publishers` | String | Semicolon-separated credited publishers |
| 69 | `PublishersCount` | Integer | Total publishers credited |
| 70 | `LowExpPublisher` | Binary (0/1) | Flag: Has unlisted/emerging publisher (<= 3 games) |
| 71 | `TotalRatingsDistribution` | Float / Empty | Total ratings summed in distribution dataset |
| 72 | `PeakRatingBucket` | String | Rating score (0.0 - 10.0) with maximum votes |
| 73 | `UserRatings_LoggedCount` | Integer / Empty | Number of logged user ratings in user_ratings.csv |
| 74 | `UserRatings_LoggedMean` | Float / Empty | Mean score calculated from user_ratings.csv |
| 75 | `UserRatings_LoggedMin` | Float / Empty | Minimum rating recorded in user_ratings.csv |
| 76 | `UserRatings_LoggedMax` | Float / Empty | Maximum rating recorded in user_ratings.csv |
| 77 | `BGG_URL` | String | Direct URL to BoardGameGeek title page |
