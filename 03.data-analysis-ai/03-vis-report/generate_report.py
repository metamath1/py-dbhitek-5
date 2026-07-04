"""
HR data visualization report generator.

Runs from Windows Task Scheduler. Picks up new CSV files in ./input/
and creates an HTML report for each one in ./output/.

Files:
  Input:  ./input/hr_qN.csv
  Output: ./output/hr_qN_report.html
          ./output/YYYY-MM-DD-HH-MM.log
          ./output/processed.txt
"""

import os
import sys
import re
import glob
import base64
import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # No display backend (for background runs)
import matplotlib.pyplot as plt
import seaborn as sns


# ===== Paths =====
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / 'input'
OUTPUT_DIR = SCRIPT_DIR / 'output'
PROCESSED_LIST = OUTPUT_DIR / 'processed.txt'


def setup_log():
    OUTPUT_DIR.mkdir(exist_ok=True)
    now = datetime.datetime.now()
    return OUTPUT_DIR / (now.strftime('%Y-%m-%d-%H-%M') + '.log')


def write_log(log_path, message):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f'[{timestamp}] {message}\n')


def get_processed():
    if not PROCESSED_LIST.exists():
        return set()
    with open(PROCESSED_LIST, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())


def mark_processed(filename):
    with open(PROCESSED_LIST, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')


def find_new_files():
    processed = get_processed()
    new_files = []
    for path in sorted(glob.glob(str(INPUT_DIR / 'hr_*.csv'))):
        fname = os.path.basename(path)
        if fname not in processed:
            new_files.append(Path(path))
    return new_files


def fig_to_base64():
    """Save current matplotlib figure as base64-encoded PNG."""
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=90)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def make_chart_1_scatter(df):
    plt.figure(figsize=(8, 5))
    sns.scatterplot(
        data=df,
        x='Age',
        y='MonthlyIncome',
        hue='Attrition',
        hue_order=['No', 'Yes'],
    )
    plt.title('Age vs MonthlyIncome by Attrition')
    plt.xlabel('Age')
    plt.ylabel('MonthlyIncome')
    return fig_to_base64()


def make_chart_2_countplot(df):
    plt.figure(figsize=(8, 5))
    sns.countplot(
        data=df,
        x='Department',
        hue='Attrition',
        order=['Human Resources', 'Research & Development', 'Sales'],
        hue_order=['No', 'Yes'],
    )
    plt.title('Attrition by Department')
    return fig_to_base64()


def make_chart_3_heatmap(df):
    cols = ['Age', 'MonthlyIncome', 'YearsAtCompany', 'DistanceFromHome']
    corr = df[cols].corr()
    plt.figure(figsize=(6, 5))
    sns.heatmap(corr, annot=True, cmap='coolwarm')
    plt.title('Correlation Heatmap')
    return fig_to_base64()


def make_chart_4_histplot(df):
    plt.figure(figsize=(8, 5))
    sns.histplot(data=df, x='MonthlyIncome', bins=30, kde=True)
    plt.title('MonthlyIncome Distribution')
    return fig_to_base64()


def make_chart_5_boxplot(df):
    plt.figure(figsize=(7, 5))
    sns.boxplot(
        data=df,
        x='Attrition',
        y='MonthlyIncome',
        order=['No', 'Yes'],
    )
    plt.title('MonthlyIncome by Attrition')
    return fig_to_base64()


def make_chart_6_barplot(df):
    plt.figure(figsize=(8, 5))
    sns.barplot(
        data=df,
        x='Department',
        y='MonthlyIncome',
        hue='OverTime',
        order=['Human Resources', 'Research & Development', 'Sales'],
        hue_order=['No', 'Yes'],
    )
    plt.title('MonthlyIncome by Department and OverTime')
    return fig_to_base64()


def extract_quarter_label(filename):
    """Pull a quarter label like 'Q1' from hr_q1.csv."""
    m = re.search(r'q(\d+)', filename.lower())
    if m:
        return f'Q{m.group(1)}'
    return filename


def build_html(df, filename):
    """Build the full HTML report string for one data file."""
    quarter = extract_quarter_label(filename)
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Summary stats
    n_rows = len(df)
    attrition_rate = (df['Attrition'] == 'Yes').mean() * 100
    missing_rate = df.isnull().sum().sum() / df.size * 100
    dept_counts = df['Department'].value_counts().to_dict()
    dept_summary = ', '.join(f'{k}: {v}' for k, v in dept_counts.items())

    # Charts
    chart1 = make_chart_1_scatter(df)
    chart2 = make_chart_2_countplot(df)
    chart3 = make_chart_3_heatmap(df)
    chart4 = make_chart_4_histplot(df)
    chart5 = make_chart_5_boxplot(df)
    chart6 = make_chart_6_barplot(df)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HR Quarterly Report - {quarter}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 20px; color: #222; }}
  h1 {{ border-bottom: 2px solid #444; padding-bottom: 8px; }}
  h2 {{ color: #555; margin-top: 40px; }}
  .summary {{ background-color: #f4f4f4; padding: 15px; border-radius: 6px; }}
  .summary li {{ margin: 4px 0; }}
  .chart {{ margin: 25px 0; text-align: center; }}
  .chart img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
  footer {{ margin-top: 50px; text-align: center; color: #888; font-size: 0.9em; }}
</style>
</head>
<body>

<h1>HR Quarterly Report - {quarter}</h1>
<p>Source file: <code>{filename}</code></p>

<h2>Summary</h2>
<div class="summary">
<ul>
  <li>Total rows: {n_rows}</li>
  <li>Attrition rate: {attrition_rate:.1f}%</li>
  <li>Missing value rate: {missing_rate:.1f}%</li>
  <li>Department counts: {dept_summary}</li>
</ul>
</div>

<h2>1. Age vs MonthlyIncome (by Attrition)</h2>
<div class="chart"><img src="data:image/png;base64,{chart1}" alt="scatter"></div>

<h2>2. Attrition by Department</h2>
<div class="chart"><img src="data:image/png;base64,{chart2}" alt="countplot"></div>

<h2>3. Correlation Heatmap</h2>
<div class="chart"><img src="data:image/png;base64,{chart3}" alt="heatmap"></div>

<h2>4. MonthlyIncome Distribution</h2>
<div class="chart"><img src="data:image/png;base64,{chart4}" alt="histogram"></div>

<h2>5. MonthlyIncome by Attrition</h2>
<div class="chart"><img src="data:image/png;base64,{chart5}" alt="boxplot"></div>

<h2>6. MonthlyIncome by Department and OverTime</h2>
<div class="chart"><img src="data:image/png;base64,{chart6}" alt="barplot"></div>

<footer>Generated at {now_str}</footer>

</body>
</html>
"""
    return html


def process_file(data_path, log_path):
    fname = data_path.name
    write_log(log_path, f'Processing {fname}')

    df = pd.read_csv(data_path)
    write_log(log_path, f'  Rows: {len(df)}, Columns: {len(df.columns)}')

    missing_total = df.isnull().sum().sum()
    write_log(log_path, f'  Missing cells: {missing_total} '
                        f'(rate: {missing_total / df.size:.3f})')

    # Build report
    html = build_html(df, fname)

    # Save report
    out_name = fname.replace('.csv', '_report.html')
    out_path = OUTPUT_DIR / out_name
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    write_log(log_path, f'  Report saved: {out_name}')

    return True


def main():
    log_path = setup_log()
    write_log(log_path, 'Script started.')

    new_files = find_new_files()
    if not new_files:
        write_log(log_path, 'No new files. Exit.')
        return

    write_log(log_path, f'Found {len(new_files)} new file(s): '
                        f'{[f.name for f in new_files]}')

    for data_path in new_files:
        try:
            if process_file(data_path, log_path):
                mark_processed(data_path.name)
                write_log(log_path, f'  Done: {data_path.name}')
        except Exception as e:
            write_log(log_path, f'  ERROR processing {data_path.name}: {e}')
            import traceback
            write_log(log_path, traceback.format_exc())

    write_log(log_path, 'Script finished.')


if __name__ == '__main__':
    main()