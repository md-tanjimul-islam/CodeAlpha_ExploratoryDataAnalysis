"""EDA pipeline: cleaning, outlier detection, hypothesis tests, 5 publication plots.

Run from the repo root:  python src/eda_pipeline.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA, PLOTS, REPORTS = ROOT / "data", ROOT / "plots", ROOT / "reports"
DPI, ALPHA = 300, 0.05
SENTIMENT = {"Overwhelmingly Negative": 0, "Very Negative": 1, "Negative": 2, "Mostly Negative": 3,
             "Mixed": 4, "Mostly Positive": 5, "Positive": 6, "Very Positive": 7,
             "Overwhelmingly Positive": 8}
TIERS = ["Free", "Budget", "Mid-tier", "AAA"]
GAME_COLUMNS = ["app_id", "title", "release_date", "original_price", "final_price",
                "discount_pct", "review_summary", "total_reviews"]
REVIEW_COLUMNS = ["review_id", "app_id", "title", "review_text", "recommended",
                  "playtime_hours", "helpful_votes", "date_posted"]
sns.set_theme(style="whitegrid", font_scale=1.1)


# ------------------------------------------------------------------ input / cleaning
def read_input(filename, required, **kwargs):
    path = DATA / filename
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}\n"
                                f"Copy it from the Task 1 repo into the data/ folder and re-run.")
    df = pd.read_csv(path, **kwargs)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{filename} is missing columns: {missing}")
    return df


def iqr_bounds(s, k=1.5):
    q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def flag_outliers(df, col):
    lo, hi = iqr_bounds(df[col].dropna())
    df[f"{col}_outlier"] = (df[col] < lo) | (df[col] > hi)
    return {"col": col, "lower": lo, "upper": hi, "n": int(df[f"{col}_outlier"].sum()),
            "pct": 100 * float(df[f"{col}_outlier"].mean()), "max": float(df[col].max())}


def clean_games():
    g = read_input("steam_games_metadata.csv", GAME_COLUMNS)
    n0 = len(g)
    g = g.drop_duplicates("app_id").copy()
    for c in ["app_id", "original_price", "final_price", "discount_pct", "total_reviews"]:
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g["title"] = g["title"].astype("string").str.strip()
    g = g.dropna(subset=["app_id", "title"]).copy()
    g["original_price"] = g["original_price"].fillna(g["final_price"]).fillna(0).clip(lower=0)
    g["final_price"] = g["final_price"].fillna(g["original_price"]).clip(lower=0)
    g["discount_pct"] = g["discount_pct"].fillna(0).clip(0, 100)
    g["total_reviews"] = g["total_reviews"].fillna(0).astype(int)
    g["app_id"] = g["app_id"].astype(int)
    g["review_summary"] = g["review_summary"].fillna("No Reviews").astype(str).str.strip()
    g["release_date"] = pd.to_datetime(g["release_date"], errors="coerce", format="mixed")
    g["release_year"] = g["release_date"].dt.year.astype("Int64")
    g["release_month"] = g["release_date"].dt.month.astype("Int64")
    g["price_tier"] = pd.cut(g["original_price"], [-1, 0, 9.99, 29.99, np.inf],
                             labels=TIERS).astype(str)
    g["log_reviews"] = np.log10(g["total_reviews"] + 1)
    g["sentiment_score"] = g["review_summary"].map(SENTIMENT)
    g["discount_bracket"] = pd.cut(g["discount_pct"], [-1, 0, 25, 50, 100],
                                   labels=["None", "1-25%", "26-50%", "51%+"]).astype(str)
    price_out = flag_outliers(g, "original_price")
    print(f"[games] {n0} rows -> {len(g)} after dedup/cleaning | "
          f"unparsed dates: {int(g['release_date'].isna().sum())}")
    return g.reset_index(drop=True), price_out


def clean_reviews(g):
    r = read_input("steam_user_reviews.csv", REVIEW_COLUMNS, dtype={"review_id": str})
    n0 = len(r)
    r = r.drop_duplicates("review_id").dropna(subset=["recommended", "app_id"]).copy()
    r["review_text"] = r["review_text"].fillna("").astype(str).str.strip()
    r = r[r["review_text"] != ""].copy()
    r["recommended"] = r["recommended"].map(lambda v: str(v).strip().lower() in {"true", "1", "yes"})
    for c in ["app_id", "playtime_hours", "helpful_votes"]:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["playtime_hours"] = r["playtime_hours"].fillna(r["playtime_hours"].median()).clip(lower=0)
    r["helpful_votes"] = r["helpful_votes"].fillna(0).clip(lower=0).astype(int)
    r["app_id"] = r["app_id"].astype(int)
    r["date_posted"] = pd.to_datetime(r["date_posted"], errors="coerce")
    r["review_len_chars"] = r["review_text"].str.len()
    r["review_len_words"] = r["review_text"].str.count(r"\S+")
    play_out = flag_outliers(r, "playtime_hours")
    orphans = int((~r["app_id"].isin(g["app_id"])).sum())
    print(f"[reviews] {n0} rows -> {len(r)} after cleaning | orphan app_ids: {orphans}")
    return r.reset_index(drop=True), play_out


# ------------------------------------------------------------------ hypothesis tests
def stat_p(res):
    """Return (statistic, p-value) as floats from any scipy test result."""
    return float(getattr(res, "statistic")), float(getattr(res, "pvalue"))


def row(test, stat, p, conclusion):
    ptxt = f"{p:.4g}" if not np.isnan(p) else "n/a"
    print(f"\n=== {test} ===\n  statistic : {stat}\n  p-value   : {ptxt}\n  conclusion: {conclusion}")
    return {"test": test, "stat": stat, "p": p, "conclusion": conclusion}


def skipped(test, reason):
    return row(test, "not computed", float("nan"), f"Skipped: {reason}")


def test_discount_reviews(g):
    name = "A) Mann-Whitney U: discounted vs non-discounted total_reviews"
    d = g.loc[g["discount_pct"] > 0, "total_reviews"]
    n = g.loc[g["discount_pct"] == 0, "total_reviews"]
    if len(d) < 3 or len(n) < 3:
        return skipped(name, f"need >=3 games per group (discounted={len(d)}, non-discounted={len(n)})")
    if len(g) >= 3:
        sw = stat_p(stats.shapiro(g["log_reviews"]))[1]
        print(f"\nNormality (Shapiro-Wilk on log10 reviews): p={sw:.3g} -> "
              f"{'normal' if sw > ALPHA else 'non-normal, using Mann-Whitney U'}")
    u, p = stat_p(stats.mannwhitneyu(d, n, alternative="greater"))
    rbc = 2 * u / (len(d) * len(n)) - 1
    verdict = ("Reject H0: discounted games have significantly MORE reviews" if p < ALPHA else
               "Fail to reject H0: no significant evidence discounted games have more reviews")
    return row(name, f"U={u:.1f} (n={len(d)} vs {len(n)}), rank-biserial r={rbc:.3f}", p, verdict)


def test_playtime_recommended(r):
    name = "B) Spearman: playtime_hours vs recommended"
    rec = r["recommended"].astype(int)
    if rec.nunique() < 2 or r["playtime_hours"].nunique() < 2:
        return skipped(name, "recommended or playtime has no variation")
    rpb, p_pb = stat_p(stats.pointbiserialr(rec, r["playtime_hours"]))
    rho, p = stat_p(stats.spearmanr(rec, r["playtime_hours"]))
    print(f"\nPoint-biserial (raw hours): r={rpb:.3f}, p={p_pb:.3g} (outlier-sensitive)")
    verdict = (f"Reject H0: playtime is {'positively' if rho > 0 else 'negatively'} associated "
               f"with recommendation" if p < ALPHA else
               "Fail to reject H0: no significant monotonic association")
    return row(name, f"rho={rho:.3f}, point-biserial r={rpb:.3f}", p, verdict)


def test_tier_sentiment(g):
    name = "C) Chi-square independence: price_tier vs review_summary"
    ct = pd.crosstab(g["price_tier"], g["review_summary"])
    ct = ct.drop(columns=["No Reviews"], errors="ignore")
    ct = ct.loc[:, ct.sum() >= 5]
    ct = ct.loc[ct.sum(axis=1) > 0]
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return skipped(name, f"contingency table too small ({ct.shape[0]}x{ct.shape[1]})")
    print("\nContingency table (price tier x review_summary):\n", ct)
    res = stats.chi2_contingency(ct)
    chi2, p = stat_p(res)
    dof = int(getattr(res, "dof"))
    exp = np.asarray(getattr(res, "expected_freq"))
    v = float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1))))
    low = 100 * float((exp < 5).mean())
    verdict = ("Reject H0: price tier and review summary are dependent" if p < ALPHA else
               "Fail to reject H0: price tier and review summary appear independent")
    if low > 20:
        verdict += f" (caution: {low:.0f}% of cells have expected count < 5)"
    return row(name, f"chi2={chi2:.2f}, dof={dof}, Cramer's V={v:.3f}", p, verdict)


# ------------------------------------------------------------------ plots
def save(fig, name):
    PLOTS.mkdir(exist_ok=True)
    fig.savefig(PLOTS / name, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved plots/{name}")


def plot_price_vs_reviews(g):
    jg = sns.jointplot(data=g, x="original_price", y="log_reviews", kind="scatter", height=8,
                       alpha=0.6, color="#1b6ca8", marginal_kws={"bins": 30, "kde": True})
    try:
        jg.plot_joint(sns.kdeplot, levels=5, color="k", linewidths=1)
    except (np.linalg.LinAlgError, ValueError):
        pass
    jg.set_axis_labels("Original price (USD)", "log10(total reviews + 1)")
    jg.figure.suptitle("Price vs Review Volume Distribution", y=1.02, fontsize=15)
    save(jg.figure, "price_vs_reviews_dist.png")


def plot_playtime_box(r):
    groups = sorted(r["recommended"].unique())
    names = {False: "Not recommended", True: "Recommended"}
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.boxplot(data=r, x="recommended", y="playtime_hours", order=groups, hue="recommended",
                hue_order=groups, palette={False: "#d1495b", True: "#2a9d8f"}, legend=False,
                flierprops={"marker": "o", "markersize": 3, "alpha": 0.4}, ax=ax)
    ax.set_yscale("symlog", linthresh=1)
    for i, grp in enumerate(groups):
        s = r.loc[r["recommended"] == grp, "playtime_hours"]
        _, hi = iqr_bounds(s)
        ax.text(i, float(s.max()) * 1.15 + 1, f"{int((s > hi).sum())} extreme outliers\n"
                f"max {s.max():,.0f} h", ha="center", fontsize=10)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([names[x] for x in groups])
    ax.set(xlabel="", ylabel="Playtime (hours, symlog scale)",
           title="Playtime Distribution and Extreme-Gamer Outliers")
    save(fig, "playtime_anomalies_boxplot.png")


def plot_heatmap(g, r):
    m = r.merge(g[["app_id", "original_price", "final_price", "discount_pct", "total_reviews",
                   "release_year", "sentiment_score"]], on="app_id", how="inner")
    m["recommended"] = m["recommended"].astype(int)
    m["release_year"] = m["release_year"].astype(float)
    cols = ["original_price", "final_price", "discount_pct", "total_reviews", "release_year",
            "sentiment_score", "playtime_hours", "helpful_votes", "review_len_words", "recommended"]
    corr = m[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(corr, mask=np.triu(np.ones(corr.shape, dtype=bool), k=1), annot=True, fmt=".2f",
                cmap="coolwarm", center=0, vmin=-1, vmax=1, square=True, linewidths=0.5, ax=ax)
    ax.set_title("Spearman Correlation Matrix (reviews joined to game metadata)")
    save(fig, "correlation_heatmap.png")


def plot_release_trends(g):
    t = (g.dropna(subset=["release_year"]).groupby("release_year")
         .agg(releases=("app_id", "count"), avg_price=("original_price", "mean")).reset_index())
    years = t["release_year"].astype(int)
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(years, t["releases"], color="#8ecae6", label="Games released")
    ax.set(xlabel="Release year", ylabel="Number of games in sample",
           title="Game Releases and Average Launch Price Over Time")
    ax2 = ax.twinx()
    ax2.plot(years, t["avg_price"], color="#d1495b", marker="o", lw=2.5, label="Avg original price")
    ax2.set_ylabel("Average original price (USD)")
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    save(fig, "release_trends_timeseries.png")


def plot_discount_violin(g):
    d = g.dropna(subset=["sentiment_score"])
    order = [b for b in ["None", "1-25%", "26-50%", "51%+"] if b in set(d["discount_bracket"])]
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.violinplot(data=d, x="discount_bracket", y="sentiment_score", order=order,
                   hue="discount_bracket", hue_order=order, palette="viridis", legend=False,
                   cut=0, inner="quartile", ax=ax)
    ax.set_yticks(range(9))
    ax.set_yticklabels(list(SENTIMENT))
    ax.set(xlabel="Discount bracket", ylabel="Steam review sentiment tier",
           title="Review Sentiment Across Discount Brackets")
    save(fig, "discount_impact_violin.png")


# ------------------------------------------------------------------ report
def write_report(results, price_out, play_out, g, r):
    REPORTS.mkdir(exist_ok=True)
    lines = ["# Results Summary (auto-generated)", "",
             "| Test | Statistic | p-value | Conclusion |", "|---|---|---|---|"]
    lines += [f"| {x['test']} | {x['stat']} | "
              f"{'n/a' if np.isnan(x['p']) else format(x['p'], '.3g')} | {x['conclusion']} |"
              for x in results]
    median = float(r["playtime_hours"].quantile(0.5))
    p99 = float(r["playtime_hours"].quantile(0.99))
    lines += ["", "## Anomaly detection (IQR, k=1.5)", "",
              f"- **Price:** fence ${price_out['lower']:.2f} to ${price_out['upper']:.2f}; "
              f"{price_out['n']} outlier games ({price_out['pct']:.1f}%), max ${price_out['max']:.2f}.",
              f"- **Playtime:** fence {play_out['lower']:.1f} to {play_out['upper']:.1f} h; "
              f"{play_out['n']} outlier reviews ({play_out['pct']:.1f}%), max {play_out['max']:,.0f} h "
              f"vs median {median:.1f} h and 99th percentile {p99:.1f} h.",
              f"- **Dataset size after cleaning:** {len(g)} games, {len(r)} reviews.", ""]
    (REPORTS / "results_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n  saved reports/results_summary.md")


def main():
    g, price_out = clean_games()
    r, play_out = clean_reviews(g)
    g.to_csv(DATA / "cleaned_steam_games_metadata.csv", index=False)
    r.to_csv(DATA / "cleaned_steam_user_reviews.csv", index=False)
    print(f"\nOutliers -> price: {price_out['n']} | playtime: {play_out['n']}")
    results = [test_discount_reviews(g), test_playtime_recommended(r), test_tier_sentiment(g)]
    print("\nGenerating plots...")
    plot_price_vs_reviews(g)
    plot_playtime_box(r)
    plot_heatmap(g, r)
    plot_release_trends(g)
    plot_discount_violin(g)
    write_report(results, price_out, play_out, g, r)


if __name__ == "__main__":
    main()