---
name: sc-eda
description: Exploratory data analysis on datasets. Generates visualizations, statistics, correlations, and HTML reports. Supports CSV, JSON, Parquet, and database sources.
---

# Exploratory Data Analysis Skill

Run exploratory data analysis on any dataset. Generates distribution plots, time series, correlation matrices, summary statistics, and interactive HTML reports.

## Quick Start

```bash
# Analyze a CSV file
/sc:eda data/sales.csv

# Analyze with specific output directory
/sc:eda data/users.json --output eda_results/users/

# Analyze with column focus
/sc:eda data/metrics.parquet --focus revenue,churn,signups

# Analyze a directory of JSON files
/sc:eda results/ --format json

# Quick summary only
/sc:eda data/logs.csv --depth quick
```

## Behavioral Flow

1. **Parse** - Extract input path, output directory, focus columns, depth
2. **Discover** - Detect file format, schema, row count, column types
3. **Profile** - Generate summary statistics for all columns
4. **Visualize** - Create distribution plots, correlations, time series
5. **Analyze** - Identify patterns, outliers, missing data, correlations
6. **Report** - Generate interactive HTML report with findings
7. **Summarize** - Present key insights to user

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output` | string | `eda_results/<name>_eda/` | Output directory for plots and reports |
| `--focus` | string | - | Comma-separated columns to focus analysis on |
| `--depth` | string | standard | quick (stats only), standard (stats + plots), deep (full analysis) |
| `--format` | string | auto | Input format: csv, json, parquet, auto-detect |
| `--time-col` | string | auto | Column to use for time series (auto-detects datetime columns) |
| `--group-by` | string | - | Column to group analysis by (e.g., category, region) |

## Phase 1: Data Discovery

Detect and load the dataset:

| Source | Detection | Loading |
|--------|-----------|---------|
| Single CSV | `.csv` extension | `pandas.read_csv()` |
| Single JSON | `.json` extension | `pandas.read_json()` or `json_normalize()` |
| Parquet | `.parquet` extension | `pandas.read_parquet()` |
| Directory | Multiple files | Glob + concatenate with source tracking |
| Nested JSON | Nested objects | `json_normalize()` with record paths |

Report schema summary:
- Total rows and columns
- Column names, types, and non-null counts
- Memory usage
- Sample rows (first 5)

## Phase 2: Statistical Profiling

Generate summary statistics:

| Metric | Numeric Columns | Categorical Columns |
|--------|----------------|-------------------|
| Count, mean, std, min, max | Yes | - |
| Quartiles (25%, 50%, 75%) | Yes | - |
| Unique values, top values | - | Yes |
| Missing value counts | Yes | Yes |
| Skewness, kurtosis | Yes | - |

Save to `data/summary_stats.csv`.

## Phase 3: Visualizations

Generate plots based on depth level:

### Quick Depth
- Missing value heatmap

### Standard Depth (default)
- **Distributions** - Histograms/KDE for numeric columns, bar charts for categorical
- **Correlation matrix** - Heatmap of numeric column correlations
- **Missing values** - Heatmap showing missing data patterns

### Deep Depth
All standard plots plus:
- **Time series** - Trends over time (if datetime column detected)
- **Group analysis** - Per-group comparisons (if `--group-by` specified)
- **Outlier detection** - Box plots and IQR-based outlier flagging
- **Pairplot** - Scatter matrix for top correlated columns (max 6)
- **Category heatmap** - Normalized metric comparison across categories

**Output structure:**
```
<output_dir>/
  plots/
    distributions.png
    correlation.png
    missing_values.png
    time_series.png      # deep only
    outliers.png         # deep only
    group_analysis.png   # if --group-by
    pairplot.png         # deep only
  data/
    summary_stats.csv
    correlation_matrix.csv
    outliers.csv         # deep only
  eda_report.html        # interactive report
```

## Phase 4: Pattern Analysis

Identify and report:

| Pattern | Method | Threshold |
|---------|--------|-----------|
| Strong correlations | Pearson r | \|r\| > 0.7 |
| Missing data patterns | MCAR/MAR analysis | > 5% missing |
| Outliers | IQR method | > 1.5 * IQR |
| Skewed distributions | Skewness test | \|skew\| > 1.0 |
| Categorical imbalance | Frequency ratios | Majority > 80% |
| Temporal trends | Rolling mean slope | Monotonic shift |

## Phase 5: Generate HTML Report

Create an interactive HTML report combining:
- Data overview and schema
- Summary statistics tables
- Embedded plot images (base64)
- Key findings and patterns
- Recommendations for further analysis

## Phase 6: Present Summary

Report key findings:
- Total records and features analyzed
- Top correlations found
- Outlier counts and affected columns
- Missing data summary
- Notable patterns and anomalies
- Recommendations

## Dependencies

The EDA script requires common data science packages:
- `pandas` - Data loading and manipulation
- `matplotlib` - Plot generation
- `seaborn` - Statistical visualizations
- `numpy` - Numerical computations

If not available, install via: `pip install pandas matplotlib seaborn numpy`

## MCP Integration

### PAL MCP (Optional)

| Tool | When | Purpose |
|------|------|---------|
| `mcp__pal__thinkdeep` | `--depth deep` | Hypothesis testing on patterns |
| `mcp__pal__chat` | Interpretation | Second opinion on findings |

### Rube MCP (Optional)

| Tool | When | Purpose |
|------|------|---------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | Database source | Find DB query tools |
| `mcp__rube__RUBE_REMOTE_WORKBENCH` | Large datasets | Process in Python sandbox |

## Error Handling

| Scenario | Action |
|----------|--------|
| File not found | Error with path suggestions |
| Unsupported format | Error listing supported formats |
| No numeric columns | Skip correlation/distribution, focus on categorical |
| Missing pandas/matplotlib | Prompt user to install |
| Dataset too large (>1M rows) | Sample for plots, full stats on complete data |
| All values missing in column | Skip column, note in report |

## Tool Coordination

- **Read** - Inspect data files and schemas
- **Bash** - Run Python scripts, install packages
- **Write** - Generate HTML reports and CSV outputs
- **Glob** - Find data files in directories
- **PAL MCP** - Pattern interpretation (deep mode)
