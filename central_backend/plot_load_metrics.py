#!/usr/bin/env python3
"""Plot load metrics produced by `load_data.py`.

Reads `central_backend/data/load_metrics.json` and writes PNG charts and
an HTML report into the same directory.

Requirements:
    pip install matplotlib

Usage:
    python3 plot_load_metrics.py
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import sys


def load_metrics(path: Path):
    if not path.exists():
        print("Metrics file not found:", path)
        return None
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def plot_durations(metrics, out_dir: Path):
    # Collect durations per item
    items = []
    durations = []
    labels = []
    for m in metrics:
        label = m.get('type')
        if m.get('type') == 'patients':
            label = f"patients:{m.get('region')}"
        items.append(label)
        durations.append(m.get('seconds') or 0.0)
        labels.append(label)

    if not items:
        print('No metric items to plot')
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, durations, color='tab:blue')
    ax.set_ylabel('Seconds')
    ax.set_title('Load durations')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    out = out_dir / 'load_durations.png'
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)
    return out


def plot_success_pie(metrics, out_dir: Path):
    success = sum(1 for m in metrics if m.get('success'))
    failed = sum(1 for m in metrics if not m.get('success'))
    labels = ['success', 'failed']
    sizes = [success, failed]
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#10b981', '#ef4444'])
    ax.set_title('Load success rate')
    out = out_dir / 'load_success_pie.png'
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)
    return out


def write_html_report(images, out_dir: Path, json_path: Path):
    out_path = out_dir / 'load_report.html'
    with out_path.open('w', encoding='utf-8') as fh:
        fh.write('<!doctype html><html><head><meta charset="utf-8"><title>Load Report</title></head><body>')
        fh.write(f'<h1>Load Report</h1>')
        fh.write(f'<p>Metrics file: {json_path.name}</p>')
        for img in images:
            if img:
                fh.write(f'<div><h3>{img.name}</h3><img src="{img.name}" style="max-width:900px; height:auto;"/></div>')
        fh.write('</body></html>')
    print('Wrote', out_path)
    return out_path


def main():
    repo_root = Path(__file__).resolve().parent
    data_dir = repo_root / 'data'
    metrics_file = data_dir / 'load_metrics.json'
    j = load_metrics(metrics_file)
    if not j:
        sys.exit(1)
    metrics = j.get('metrics', [])
    img1 = plot_durations(metrics, data_dir)
    img2 = plot_success_pie(metrics, data_dir)
    write_html_report([img1, img2], data_dir, metrics_file)


if __name__ == '__main__':
    main()
