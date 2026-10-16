//Documentation of Benchmarks
Hardware
CPU: AMD Ryzen 7 5700U with Radeon Graphics

GPU: AMD Radeon Graphics

RAM: 24 GB

Operating System: Windows

Inference Platform: Ollama

Test Objective
Evaluate local LLMs for personalized board game tutoring.

The models are tested on:

Accuracy
Teaching quality
Personalization
Response speed
Benchmark Prompt
"Teach Catan to someone who knows Monopoly."

Explain:

Resource Management
Trading
Victory Points
Use Monopoly comparisons.

Keep the lesson beginner friendly.

Do not invent rules.

Limit the lesson to approximately 300 words.

----------- Model 1: Llama 3.2 3B ------------------
Response Time: 52.5 seconds

Quality Score (1-5): 4/5

Accuracy Score (1-5): 4/5

Personalization Score (1-5): 5/5

Notes: Local inference using Ollama. CPU inference on AMD Ryzen 7 5700U

Response:

Days              : 0
Hours             : 0
Minutes           : 0
Seconds           : 52
Milliseconds      : 505
Ticks             : 525051817
TotalDays         : 0.000607698862268518
TotalHours        : 0.0145847726944444
TotalMinutes      : 0.875086361666667
TotalSeconds      : 52.5051817
TotalMilliseconds : 52505.1817


----------- Model 2: Gemma 3 4B ------------------
Response Time: 173.7 seconds (2 minutes 53 seconds)

Quality Score (1-5): 5/5

Accuracy Score (1-5): 5/5

Personalization Score (1-5): 5/5

Notes:
  - Local inference using Ollama.
  - Tested on AMD Ryzen 7 5700U with 24 GB RAM.
  - CPU-only inference.
  - Approximately 3x slower than Llama 3.2 3B on the same hardware.
  - Suitable candidate for higher-quality generation if latency is not critical.

Response:
Days              : 0
Hours             : 0
Minutes           : 2
Seconds           : 53
Milliseconds      : 731
Ticks             : 1737317468
TotalDays         : 0.00201078410648148
TotalHours        : 0.0482588185555556
TotalMinutes      : 2.89552911333333
TotalSeconds      : 173.7317468
TotalMilliseconds : 173731.7468

----------- Model 3: Phi-3 Mini  ------------------
Response Time: 99.8 seconds (1 minute 40 seconds)

Quality Score (1-5): 2/5

Accuracy Score (1-5): 2/5

Personalization Score (1-5): 3/5

Notes:
  - Local inference using Ollama.
  - Tested on AMD Ryzen 7 5700U with 24 GB RAM.
  - CPU-only inference.
  - Faster than Gemma 3 4B.
  - Slower than Llama 3.2 3B.

Response:
Days              : 0
Hours             : 0
Minutes           : 1
Seconds           : 39
Milliseconds      : 757
Ticks             : 997573585
TotalDays         : 0.00115459905671296
TotalHours        : 0.0277103773611111
TotalMinutes      : 1.66262264166667
TotalSeconds      : 99.7573585
TotalMilliseconds : 99757.3585

Final Recommendation
Selected Model: Llama 3.2 3B

Reason: Among the tested local models, Llama 3.2 3B delivered the best response latency on AMD Ryzen 7 5700U hardware while still providing high-quality educational explanations.

Strengths:
  - Fastest inference time
  - Good Balance of speed and quality
  - Suitable for local deployment

Weaknesses:
  - Smaller model than Gemma 3 4B
  - May provide less detailed explenations than larger models.


------------ Model 1: Llama 3.2 3B --------------------

Quality Evaluation

  Score: 4/5

  - Clear and beginner-friendly explanation.
  - Well organized into Resource Management, Trading, and Victory Points sections.
  - Uses easy-to-understand Monopoly comparisons throughout the lesson.
  - Teaching style is concise and engaging.
  - Some analogies (such as comparing resources to stock portfolios) are less helpful for beginners.

Accuracy Evaluation

  Score: 4/5

  - Correctly explains the role of resources in Catan.
  - Correctly describes trading between players.
  - Correctly identifies Victory Points as the game's win condition.
  - Correctly mentions settlements, cities, and special achievements such as Longest Road.
  - Contains minor simplifications and a few statements that are not fully precise according to official game rules.
  - Personalization Evaluation

  Score: 5/5

  - Strong use of Monopoly as a familiar reference point.
  - Frequently relates Catan concepts to Monopoly mechanics.
  - Makes the transition from a familiar game to a new game easy for first-time learners.

------------ Model 2: Gemma 3 4B --------------------

Quality Evaluation

  Score: 5/5

  - Best overall teaching structure among the tested models.
  - Presents information in a logical progression from goals to gameplay mechanics.
  - Uses headings, examples, and explanations effectively.
  - Feels similar to a human tutor providing a guided introduction.
  - Provides detailed explanations without becoming difficult to follow.
  
Accuracy Evaluation

  Score: 5/5

  - Correctly explains Victory Points and the first-to-10-win condition.
  - Accurately describes settlements, cities, roads, development cards, and trading.
  - Correctly explains Longest Road, Largest Army, and the Robber mechanic.
  - No significant factual errors were identified during manual review.

Personalization Evaluation

  Score: 5/5

  - Consistently uses Monopoly analogies throughout the explanation.
  - Connects Monopoly concepts such as properties, hotels, and trading to Catan mechanics.
  - Demonstrates excellent adaptation to the user's prior game knowledge.

------------ Model 3: Phi-3 Mini --------------------

Quality Evaluation

  Score: 2/5

  - Explanation is understandable but less organized than the other models.
  - Some sections are repetitive and difficult to follow.
  - Several analogies do not improve understanding and occasionally create confusion.
  - Teaching flow feels less polished than Llama 3.2 and Gemma 3.

Accuracy Evaluation

  Score: 2/5

  - Contains several factual inaccuracies.
  - Incorrectly describes some game mechanics and terminology.
  - Introduces explanations that do not correspond to official Catan rules.
  - Less reliable as an educational model for rule teaching.

Personalization Evaluation

  Score: 3/5

  - Attempts to use Monopoly comparisons.
  - Comparisons are present but less useful and sometimes inaccurate.
  - Personalization is weaker compared with Llama 3.2 and Gemma 3.


| Model        | Time      | Quality | Accuracy | Personalization |     Total |
| ------------ | --------- | ------: | -------: | --------------: | --------: |
| Llama 3.2 3B | 52-61 sec |     4/5 |      4/5 |             5/5 | **13/15** |
| Gemma 3 4B   | 174 sec   |     5/5 |      5/5 |             5/5 | **15/15** |
| Phi-3 Mini   | 100 sec   |     2/5 |      2/5 |             3/5 |  **7/15** |


~~~~~~~~~~ FINAL CONCLUSION ~~~~~~~~~~~~~~~~~~~~

Gemma 3 4B achieved the highest educational quality and accuracy, making it the strongest model for personalized board-game tutoring.

Llama 3.2 3B provided the best balance between response latency and teaching quality, making it the most practical option for local deployment on AMD Ryzen 7 5700U hardware.

Phi-3 Mini demonstrated acceptable performance but produced noticeably weaker educational content and multiple factual inaccuracies compared with the other tested models.

----------------- Memory Usage Observations --------------------

Although Phi-3 Mini is marketed as a compact model, it consumed the largest amount of memory during local Ollama inference on the test system ($ ollama ps).

Measured loaded memory:

Llama 3.2 3B: 2.6 GB
Gemma 3 4B: 2.9 GB
Phi-3 Mini: 3.9 GB
Phi-3 Mini also produced lower quality and accuracy scores than Gemma 3 4B while using more memory than expected.

| Model        | Loaded Memory |
| ------------ | ------------- |
| Llama 3.2 3B | 2.6 GB        |
| Gemma 3 4B   | 2.9 GB        |
| Phi-3 Mini   | 3.9 GB        |

~~~~~~~~~~~~~~~~~~~~ Limitations ~~~~~~~~~~~~~~~~~~~~~~~
All benchmarks were performed locally on an AMD Ryzen 7 5700U laptop using CPU-only inference through Ollama.

Results may differ when deploying models on dedicated AMD GPU hardware or AMD cloud infrastructure.

Only a limited set of educational prompts was tested, focusing on board-game tutoring scenarios.