"""
SECOM daily inspection script.

Runs every 5 minutes via Windows Scheduler.
Picks up new data files from ./input/ and predicts using the saved model.

Files:
  Input:  ./input/secom_dayN.csv   (no label)
  Output: ./output/result_log.csv  (one line per day)
          ./output/YYYY-MM-DD-HH-MM.log  (run log)
          ./output/processed.txt   (list of done files)
  Model:  ./model.pkl   (created by the training notebook)
"""

import os
import sys
import re
import glob
import datetime
from pathlib import Path

import pandas as pd
import joblib


# ===== Paths =====
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / 'input'
OUTPUT_DIR = SCRIPT_DIR / 'output'
MODEL_PATH = SCRIPT_DIR / 'model.pkl'
RESULT_LOG = OUTPUT_DIR / 'result_log.csv'
PROCESSED_LIST = OUTPUT_DIR / 'processed.txt'


def setup_logger():
    """Create a log file for this run. Returns the log file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    now = datetime.datetime.now()
    log_name = now.strftime('%Y-%m-%d-%H-%M') + '.log'
    return OUTPUT_DIR / log_name


def write_log(log_path, message):
    """Append a message to the log file with timestamp."""
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    line = f'[{timestamp}] {message}\n'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(line)


def get_processed_files():
    """Read the list of already-processed files."""
    if not PROCESSED_LIST.exists():
        return set()
    with open(PROCESSED_LIST, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())


def mark_processed(filename):
    """Add a filename to the processed list."""
    with open(PROCESSED_LIST, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')


def find_new_files():
    """Find data files in input folder that have not been processed yet."""
    processed = get_processed_files()
    new_files = []
    pattern = str(INPUT_DIR / 'secom_day*.csv')
    for path in sorted(glob.glob(pattern)):
        fname = os.path.basename(path)
        if fname not in processed:
            new_files.append(Path(path))
    return new_files


def append_result(record):
    """Append one row to the result CSV."""
    df_new = pd.DataFrame([record])
    if RESULT_LOG.exists():
        df_old = pd.read_csv(RESULT_LOG)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_csv(RESULT_LOG, index=False, encoding='utf-8-sig')


def analyze_file(data_path, imputer, model, log_path):
    """Run prediction on one data file."""
    fname = data_path.name
    write_log(log_path, f'Analyzing {fname}')

    # Load data
    df = pd.read_csv(data_path)
    write_log(log_path, f'  Rows: {len(df)}, Columns: {len(df.columns)}')

    # Separate ID and features
    if 'wafer_id' not in df.columns:
        write_log(log_path, '  ERROR: wafer_id column not found.')
        return None
    X = df.drop(columns=['wafer_id'])

    # Check feature count
    expected_n = imputer.n_features_in_
    if X.shape[1] != expected_n:
        write_log(log_path, f'  ERROR: feature count mismatch. '
                            f'Expected {expected_n}, got {X.shape[1]}.')
        return None

    # Missing value check (before imputation)
    missing_per_col = X.isnull().sum()
    missing_total = int(missing_per_col.sum())
    missing_rate = missing_total / X.size
    cols_with_missing = missing_per_col[missing_per_col > 0]
    write_log(log_path, f'  Missing values before imputation: '
                        f'{missing_total} cells '
                        f'({len(cols_with_missing)} columns affected, '
                        f'rate {missing_rate:.3f})')

    # Show top columns with missing values
    if len(cols_with_missing) > 0:
        top_missing = cols_with_missing.sort_values(ascending=False).head(5)
        for col, n_miss in top_missing.items():
            write_log(log_path, f'    {col}: {int(n_miss)} missing')

    # Imputation: use median values learned during training
    strategy = getattr(imputer, 'strategy', 'unknown')
    write_log(log_path, f'  Imputation strategy: {strategy} '
                        f'(values from training data)')

    X_imp = pd.DataFrame(imputer.transform(X), columns=X.columns)

    # Confirm imputation result
    missing_after = int(X_imp.isnull().sum().sum())
    write_log(log_path, f'  Missing values after imputation: {missing_after}')

    pred = model.predict(X_imp)
    n_fail = int((pred == 1).sum())
    fail_rate = n_fail / len(pred)
    write_log(log_path, f'  Predicted Fail: {n_fail} / {len(pred)} '
                        f'(rate: {fail_rate:.3f})')

    # Key features average (for drift monitoring)
    key_features = ['etch_chamber_temp_avg',
                    'metrology_cd_uniformity',
                    'litho_focus_offset']
    feature_means = {}
    for feat in key_features:
        if feat in X.columns:
            feature_means[feat] = round(float(X[feat].mean()), 4)

    # Build result record
    record = {
        'run_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'file': fname,
        'rows': len(df),
        'predicted_fail': n_fail,
        'predicted_fail_rate': round(fail_rate, 4),
        'missing_rate': round(missing_rate, 4),
    }
    for feat, val in feature_means.items():
        record[f'{feat}_mean'] = val

    write_log(log_path, f'  Done: {fname}')
    return record


def main():
    log_path = setup_logger()
    write_log(log_path, 'Script started.')
    write_log(log_path, f'Working dir: {SCRIPT_DIR}')

    # Load model
    if not MODEL_PATH.exists():
        write_log(log_path, f'ERROR: model file not found: {MODEL_PATH}')
        write_log(log_path, 'Run the training notebook first to create model.pkl.')
        return

    try:
        imputer, model = joblib.load(MODEL_PATH)
        write_log(log_path, f'Model loaded from {MODEL_PATH.name}')
    except Exception as e:
        write_log(log_path, f'ERROR: failed to load model: {e}')
        return

    # Find new files
    new_files = find_new_files()
    if not new_files:
        write_log(log_path, 'No new files. Exit.')
        return

    write_log(log_path, f'Found {len(new_files)} new file(s): '
                        f'{[f.name for f in new_files]}')

    # Process each file
    for data_path in new_files:
        try:
            record = analyze_file(data_path, imputer, model, log_path)
            if record is not None:
                append_result(record)
                mark_processed(data_path.name)
                write_log(log_path, f'  Result saved to {RESULT_LOG.name}')
        except Exception as e:
            write_log(log_path, f'  ERROR processing {data_path.name}: {e}')
            import traceback
            write_log(log_path, traceback.format_exc())

    write_log(log_path, 'Script finished.')


if __name__ == '__main__':
    main()
