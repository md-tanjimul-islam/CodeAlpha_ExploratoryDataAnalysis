# CodeAlpha_ExploratoryDataAnalysis

**Task 2: Exploratory Data Analysis | CodeAlpha Data Analytics Internship**

---

## What This Project Does
This project explores the Steam game and review data collected in Task 1 (`CodeAlpha_WebScraping`). It cleans the data, finds outliers, tests five business questions with statistics, and produces five publication-quality charts, all from one script.

## Business Questions
1. **Visibility:** Do discounted games get significantly more reviews than full-price games?
2. **Engagement:** Is longer playtime linked to a player recommending the game?
3. **Pricing and quality:** Is price tier (Free, Budget, Mid-tier, AAA) independent of Steam's review summary?
4. **Market trends:** How have release volume and average launch price changed over time?
5. **Discount strategy:** Does review sentiment differ across discount depth brackets?

## What I Built
One script, `src/eda_pipeline.py`, that runs these stages in order:

1. **Load and validate:** checks that both input CSVs exist and have the expected columns.
2. **Clean:**
   - removes duplicates (`app_id`, `review_id`) and empty reviews;
   - converts columns to proper types and fills missing values (prices from each other, discount to 0, playtime to the median);
   - parses release dates into `release_year` and `release_month`;
   - computes review length in characters and words;
   - creates `price_tier` (Free = $0, Budget under $10, Mid-tier $10-$30, AAA $30 or more), `log_reviews`, an ordinal `sentiment_score` (0 to 8), and `discount_bracket`.
3. **Detect outliers:** uses the IQR method (1.5 x IQR fences) on `original_price` and `playtime_hours`. Outliers are flagged, not deleted.
4. **Test hypotheses** with `scipy.stats` (significance level 0.05):

| Question | Test | Why this test |
|---|---|---|
| Q1 | Mann-Whitney U (one-sided) | Review counts are heavy-tailed, so a rank-based test is safer than a t-test. A Shapiro-Wilk check is printed to justify this. |
| Q2 | Spearman correlation, plus point-biserial as a robustness check | `recommended` is binary and playtime has extreme values, so a rank correlation is more reliable. |
| Q3 | Chi-square test of independence, plus Cramer's V | Both variables are categorical. The script warns when many cells have low expected counts. |

5. **Plot** five 300 DPI charts into `plots/`.
6. **Report:** writes `reports/results_summary.md` with a results table and the anomaly findings.

## How It Works: Data Flow
```
data/steam_games_metadata.csv ──┐
                                ├─> clean + validate ─> data/cleaned_*.csv
data/steam_user_reviews.csv ────┘          │
                                           ├─> IQR outlier detection
                                           ├─> 3 hypothesis tests
                                           ├─> 5 plots   (plots/)
                                           └─> reports/results_summary.md
```

## Project Structure
```
CodeAlpha_ExploratoryDataAnalysis/
├── data/        # input CSVs from Task 1, plus cleaned_*.csv output
├── plots/       # 5 PNG charts (300 DPI)
├── reports/     # results_summary.md (auto-generated)
├── src/eda_pipeline.py
├── requirements.txt
├── .gitignore
└── README.md
```

## How to Run
```bash
git clone https://github.com/md-tanjimul-islam/CodeAlpha_ExploratoryDataAnalysis
cd CodeAlpha_ExploratoryDataAnalysis
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Copy the two CSVs from the Task 1 repo into this repo's `data/` folder:
```
data/steam_games_metadata.csv
data/steam_user_reviews.csv
```

Then run:
```bash
python src/eda_pipeline.py
```

**Outputs**
- `data/cleaned_steam_games_metadata.csv`, `data/cleaned_steam_user_reviews.csv`
- `plots/` (the five charts below)
- `reports/results_summary.md`: the p-value table and anomaly findings from your run

## Visualizations

**1. Price vs review volume** (joint scatter with KDE and marginal histograms)
![Price vs Reviews](plots/price_vs_reviews_dist.png)

**2. Playtime anomalies** (boxplot by recommendation, with outlier counts)
![Playtime Anomalies](plots/playtime_anomalies_boxplot.png)

**3. Correlation heatmap** (Spearman correlations of all numeric features)
![Correlation Heatmap](plots/correlation_heatmap.png)

**4. Release trends** (games released per year and average launch price)
![Release Trends](plots/release_trends_timeseries.png)

**5. Discount impact** (review sentiment tiers across discount brackets)
![Discount Impact](plots/discount_impact_violin.png)

## Reading the Results
Open `reports/results_summary.md` after a run. For each test it gives the statistic, the p-value, and a plain-language conclusion. A p-value below 0.05 means the pattern is unlikely to be due to chance alone. It does not prove cause and effect. The anomaly section lists the IQR fences, how many price and playtime outliers were found, and how extreme the largest values are compared with the median.

## Important Notes
- If the input data came from the synthetic fallback in Task 1, the findings describe simulated data, not the real Steam market. Say so in any write-up.
- Top-seller sampling is biased toward successful games.
- The chi-square test can be unreliable with small samples. The script flags this when it happens.

## Next Steps
The same review data is used in **Task 4 (Sentiment Analysis)** to classify opinions and detect emotions.

---
**Owner:** Md. Tanjimul Islam - CodeAlpha Intern