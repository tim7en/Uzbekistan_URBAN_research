"""
Uzbekistan Industrial & Environmental Monitoring Analysis
Analyzes factory/facility air quality data from factories+extra.xlsx
Produces: facility location map + multi-page PDF report
"""

import sys
import os
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import matplotlib.ticker as mticker
from openpyxl import load_workbook
from datetime import datetime

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = "d:/dev/Uzbekistan_URBAN_research"
XLSX_PATH = os.path.join(BASE_DIR, "factories+extra.xlsx")
SHEET_NAME = "havo_sifati_2026-03-01_2026-03-"
UZ_JSON    = os.path.join(BASE_DIR, "uz.json")
OUT_DIR    = os.path.join(BASE_DIR, "suhi_analysis_output")
MAP_OUT    = os.path.join(OUT_DIR, "uzbekistan_facility_map.png")
PDF_OUT    = os.path.join(OUT_DIR, "uzbekistan_factory_emissions_report.pdf")

os.makedirs(OUT_DIR, exist_ok=True)

# ── Dark theme defaults ────────────────────────────────────────────────────────
BG = "#0E1117"
FG = "#E0E0E0"
ACCENT = "#4A90D9"
matplotlib.rcParams.update({
    'figure.facecolor': BG,
    'axes.facecolor':   BG,
    'axes.edgecolor':   '#444',
    'axes.labelcolor':  FG,
    'xtick.color':      FG,
    'ytick.color':      FG,
    'text.color':       FG,
    'grid.color':       '#2A2A2A',
    'grid.linewidth':   0.5,
    'font.family':      'DejaVu Sans',
})

# ── Classification rules ───────────────────────────────────────────────────────
TYPE_RULES = [
    ("Power Plant",          ["IES","TES","\u0422\u042d\u0421","IEM","issiqlik elektr"]),
    ("Gold Mining",          ["NGMK","KON-METALLURGIYA","GMZ"]),
    ("Chemical Plant",       ["NAVOIYAZOT","NAZOT","AMMOFOS","MAXAM","fosforit"]),
    ("Oil & Gas",            ["LUKOIL","\u041b\u0423\u041a\u041e\u0418\u041b","O'ztransgaz","Ztransgaz","NPZ","\u041d\u041f\u0417","EQMS","neft"]),
    ("Cement",               ["Sement","cement","HUAXIN"]),
    ("Manufacturing",        ["zavod","ZAVOD","Zavodi","mexanika","quyuv","TTZ"]),
    ("Air Quality Monitor",  ["AIRCONTROL","Uzhydromet","observatory"]),
    ("Weather Station",      ["AWS"]),
    ("Other Industrial",     ["ENE0","CEMS"]),
]
DEFAULT_TYPE = "Other"

TYPE_COLORS = {
    "Power Plant":          "#E63946",
    "Gold Mining":          "#FFD700",
    "Chemical Plant":       "#F4A261",
    "Oil & Gas":            "#8B4513",
    "Cement":               "#A8DADC",
    "Manufacturing":        "#2A9D8F",
    "Air Quality Monitor":  "#4A90D9",
    "Weather Station":      "#555555",
    "Other Industrial":     "#E9C46A",
    "Other":                "#888888",
}

POLLUTANTS = ["PM2.5 (mg/m\u00b3)", "PM10 (mg/m\u00b3)", "SO2 (mg/m\u00b3)",
              "NO (mg/m\u00b3)", "NO2 (mg/m\u00b3)", "NOx (mg/m\u00b3)",
              "CO (mg/m\u00b3)", "O3 (mg/m\u00b3)", "NH3 (mg/m\u00b3)", "H2S (mg/m\u00b3)"]

# WHO 24h thresholds (mg/m3)
WHO = {
    "PM2.5 (mg/m\u00b3)": 0.025,
    "PM10 (mg/m\u00b3)":  0.050,
    "SO2 (mg/m\u00b3)":   0.125,
    "NO2 (mg/m\u00b3)":   0.025,
    "CO (mg/m\u00b3)":    10.0,
}

# ── GeoJSON helper ─────────────────────────────────────────────────────────────
print("[1/7] Loading GeoJSON regions ...")
with open(UZ_JSON, encoding='utf-8') as f:
    GJ = json.load(f)

def draw_uz_regions(ax, facecolor="#161B22", edgecolor="#555", lw=1.0, alpha=1.0):
    patches = []
    for feat in GJ['features']:
        geom = feat['geometry']
        if geom['type'] == 'Polygon':
            polys = [geom['coordinates']]
        else:
            polys = geom['coordinates']
        for poly in polys:
            ring = poly[0] if isinstance(poly[0][0], list) else poly
            arr = np.array(ring)
            patches.append(MplPolygon(arr[:, :2], closed=True))
    pc = PatchCollection(patches, facecolor=facecolor, edgecolor=edgecolor,
                         linewidth=lw, alpha=alpha, zorder=1)
    ax.add_collection(pc)

# ── STEP 1: Load data ──────────────────────────────────────────────────────────
print("[2/7] Loading Excel data (this may take a minute) ...")

wb = load_workbook(XLSX_PATH, data_only=True, read_only=True)
ws = wb[SHEET_NAME]

rows = ws.values
header = next(rows)
header = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(header)]
print(f"    Columns detected: {len(header)}")

data = list(rows)
print(f"    Rows loaded: {len(data):,}")

df = pd.DataFrame(data, columns=header)
wb.close()

# Rename for convenience
TS_COL  = "Sana va Vaqt"
DEV_COL = "Qurilma"
NAM_COL = "Qurilma Nomi"
LOC_COL = "Joylashuv"
LAT_COL = "Latitude"
LON_COL = "Longitude"

# Parse timestamp
df[TS_COL] = pd.to_datetime(df[TS_COL], errors='coerce')

# Convert pollutant columns to float
numeric_cols = POLLUTANTS + ["Harorat (\u00b0C)", "Namlik (%)", "Bosim (hPa)",
                              "Shamol Tezligi (m/s)", "Shamol Yo'nalishi (\u00b0)",
                              LAT_COL, LON_COL]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# String columns
for col in [DEV_COL, NAM_COL, LOC_COL]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

print(f"    Date range: {df[TS_COL].min()} to {df[TS_COL].max()}")
print(f"    Unique devices: {df[DEV_COL].nunique()}")

# ── Classification ─────────────────────────────────────────────────────────────
def classify(row):
    combined = " ".join([
        str(row.get(DEV_COL, "")),
        str(row.get(NAM_COL, "")),
        str(row.get(LOC_COL, ""))
    ])
    for ftype, keywords in TYPE_RULES:
        for kw in keywords:
            if kw.lower() in combined.lower():
                return ftype
    return DEFAULT_TYPE

print("[3/7] Classifying facility types ...")
# Build per-device classification (faster than row-by-row on 435k rows)
device_df = df[[DEV_COL, NAM_COL, LOC_COL]].drop_duplicates(subset=[DEV_COL])
device_df = device_df.copy()
device_df['facility_type'] = device_df.apply(classify, axis=1)

type_map = device_df.set_index(DEV_COL)['facility_type'].to_dict()
df['facility_type'] = df[DEV_COL].map(type_map)

print("    Facility type distribution:")
for ft, cnt in df['facility_type'].value_counts().items():
    print(f"      {ft}: {cnt:,} readings")

# ── STEP 2: Facilities DataFrame ───────────────────────────────────────────────
print("[4/7] Building facilities table ...")

def first_valid(series):
    valid = series.dropna()
    return valid.iloc[0] if len(valid) > 0 else np.nan

def extract_region(loc_str):
    loc = str(loc_str)
    for pat in ["viloyati", "Viloyati", "Respublikasi", "respublikasi", "shahri", "Shahri"]:
        idx = loc.find(pat)
        if idx > 0:
            # grab the word before the pattern
            before = loc[:idx].strip().split()
            if before:
                return before[-1] + " " + pat
    return "Unknown"

fac_rows = []
for dev_id, grp in df.groupby(DEV_COL):
    lat = first_valid(grp[LAT_COL])
    lon = first_valid(grp[LON_COL])
    name = first_valid(grp[NAM_COL].replace('nan', np.nan).replace('None', np.nan))
    location = first_valid(grp[LOC_COL].replace('nan', np.nan).replace('None', np.nan))
    ftype = type_map.get(dev_id, DEFAULT_TYPE)
    region = extract_region(location if pd.notna(location) else "")
    fac_rows.append({
        'device_id':    dev_id,
        'name':         str(name) if pd.notna(name) else dev_id,
        'location':     str(location) if pd.notna(location) else "",
        'lat':          lat,
        'lon':          lon,
        'facility_type':ftype,
        'region':       region,
        'meas_count':   len(grp),
    })

facilities = pd.DataFrame(fac_rows)
print(f"    Total unique facilities: {len(facilities)}")

# ── STEP 3: Pollutant statistics ───────────────────────────────────────────────
print("[5/7] Computing pollutant statistics ...")

poll_stats = {}
for poll in POLLUTANTS:
    if poll not in df.columns:
        continue
    g = df.groupby(DEV_COL)[poll]
    stats = pd.DataFrame({
        'mean':        g.mean(),
        'max':         g.max(),
        'count_valid': g.count(),
    })
    if poll in WHO:
        thresh = WHO[poll]
        exc = df[df[poll] > thresh].groupby(DEV_COL)[poll].count()
        stats['exceedances'] = exc
        stats['exceedances'] = stats['exceedances'].fillna(0).astype(int)
    else:
        stats['exceedances'] = 0
    poll_stats[poll] = stats

# Merge into facilities
for poll in POLLUTANTS:
    if poll not in poll_stats:
        continue
    stats = poll_stats[poll]
    short = poll.split(' ')[0]
    facilities = facilities.merge(
        stats[['mean','max','count_valid','exceedances']].rename(columns={
            'mean':        f'{short}_mean',
            'max':         f'{short}_max',
            'count_valid': f'{short}_n',
            'exceedances': f'{short}_exc',
        }),
        left_on='device_id', right_index=True, how='left'
    )

# ── Load GeoJSON for bounds ────────────────────────────────────────────────────
all_lons, all_lats = [], []
for feat in GJ['features']:
    geom = feat['geometry']
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    for poly in polys:
        ring = poly[0] if isinstance(poly[0][0], list) else poly
        arr = np.array(ring)
        all_lons.extend(arr[:, 0].tolist())
        all_lats.extend(arr[:, 1].tolist())

MAP_XLIM = (min(all_lons) - 0.5, max(all_lons) + 0.5)
MAP_YLIM = (min(all_lats) - 0.5, max(all_lats) + 0.5)

# ── STEP 4: Facility Location Map ─────────────────────────────────────────────
print("[6/7] Generating facility location map ...")

fig_map, ax_map = plt.subplots(figsize=(18, 12), facecolor=BG)
ax_map.set_facecolor(BG)

draw_uz_regions(ax_map, facecolor="#161B22", edgecolor="#666666", lw=1.2, alpha=1.0)

# Plot facilities
type_order = [t for t, _ in TYPE_RULES] + [DEFAULT_TYPE]
legend_handles = []

for ftype in type_order:
    sub = facilities[facilities['facility_type'] == ftype].copy()
    sub = sub.dropna(subset=['lat', 'lon'])
    if sub.empty:
        continue
    color = TYPE_COLORS.get(ftype, "#888888")
    sizes = np.clip(sub['meas_count'] / sub['meas_count'].max() * 180 + 30, 30, 210)
    ax_map.scatter(sub['lon'], sub['lat'], c=color, s=sizes,
                   alpha=0.85, zorder=3, edgecolors='white', linewidths=0.4)
    handle = mpatches.Patch(color=color, label=f"{ftype} ({len(sub)})")
    legend_handles.append(handle)

# Label important industrial sites
LABEL_TYPES = {"Power Plant", "Gold Mining", "Chemical Plant", "Oil & Gas"}
labeled = facilities[facilities['facility_type'].isin(LABEL_TYPES)].dropna(subset=['lat','lon'])
for _, row in labeled.iterrows():
    lbl = str(row['name'])[:28]
    ax_map.annotate(lbl, xy=(row['lon'], row['lat']),
                    xytext=(row['lon'] + 0.15, row['lat'] + 0.12),
                    fontsize=6.5, color='white', alpha=0.88,
                    arrowprops=dict(arrowstyle='-', color='#aaa', lw=0.4),
                    zorder=5)

ax_map.set_xlim(MAP_XLIM)
ax_map.set_ylim(MAP_YLIM)
ax_map.set_xlabel("Longitude", fontsize=11)
ax_map.set_ylabel("Latitude", fontsize=11)
ax_map.set_title("Uzbekistan Industrial & Environmental Monitoring Network 2026",
                 fontsize=16, fontweight='bold', color='white', pad=14)

legend = ax_map.legend(handles=legend_handles, loc='lower left', framealpha=0.25,
                        fontsize=9, labelcolor='white', facecolor='#1A1F2E',
                        edgecolor='#444', title="Facility Type", title_fontsize=10)
legend.get_title().set_color('white')

# Size legend note
ax_map.text(0.99, 0.01, "Dot size ~ measurement count",
            transform=ax_map.transAxes, ha='right', va='bottom',
            fontsize=8, color='#aaa')

plt.tight_layout()
fig_map.savefig(MAP_OUT, dpi=180, facecolor=BG, bbox_inches='tight')
plt.close(fig_map)
print(f"    Map saved: {MAP_OUT}")

# ── STEP 5: PDF Report ─────────────────────────────────────────────────────────
print("[7/7] Generating PDF report ...")

def set_dark(fig, axes=None):
    fig.patch.set_facecolor(BG)
    if axes is None:
        return
    if not hasattr(axes, '__iter__'):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(BG)
        ax.tick_params(colors=FG)
        for spine in ax.spines.values():
            spine.set_edgecolor('#444')

def trunc(s, n=40):
    s = str(s)
    return s[:n] + "..." if len(s) > n else s

with PdfPages(PDF_OUT) as pdf:

    # ── PAGE 1: Cover & Overview ───────────────────────────────────────────────
    fig = plt.figure(figsize=(17, 11), facecolor=BG)
    set_dark(fig)

    ax_title = fig.add_axes([0.0, 0.72, 1.0, 0.28])
    ax_title.set_facecolor("#0E1117")
    ax_title.axis('off')
    ax_title.text(0.5, 0.80, "Uzbekistan Industrial & Environmental Monitoring",
                  ha='center', va='center', fontsize=22, fontweight='bold', color='white')
    ax_title.text(0.5, 0.55, "Factory Emissions Analysis Report  |  March 2026",
                  ha='center', va='center', fontsize=14, color=ACCENT)
    ax_title.text(0.5, 0.30,
                  f"Data source: Air Quality Monitoring Network  |  Generated: {datetime.now().strftime('%Y-%m-%d')}",
                  ha='center', va='center', fontsize=10, color='#999')

    # Key stats
    total_fac = len(facilities)
    total_meas = len(df)
    date_min = df[TS_COL].min()
    date_max = df[TS_COL].max()
    type_counts = facilities['facility_type'].value_counts()

    ax_stats = fig.add_axes([0.03, 0.45, 0.38, 0.26])
    ax_stats.set_facecolor("#161B22")
    ax_stats.axis('off')
    stats_text = [
        ("Total Facilities",    str(total_fac)),
        ("Total Measurements",  f"{total_meas:,}"),
        ("Date Range",          f"{date_min.strftime('%Y-%m-%d') if pd.notna(date_min) else 'N/A'} to {date_max.strftime('%Y-%m-%d') if pd.notna(date_max) else 'N/A'}"),
        ("Facility Types",      str(len(type_counts))),
        ("Unique Regions",      str(facilities['region'].nunique())),
    ]
    for i, (lbl, val) in enumerate(stats_text):
        y = 0.88 - i * 0.18
        ax_stats.text(0.05, y, lbl + ":", fontsize=11, color='#aaa', va='center')
        ax_stats.text(0.55, y, val,        fontsize=11, color='white', va='center', fontweight='bold')
    ax_stats.set_title("Key Statistics", fontsize=12, color=ACCENT, pad=8)
    for spine in ax_stats.spines.values():
        spine.set_edgecolor('#333')

    # Facility type table
    ax_table = fig.add_axes([0.03, 0.06, 0.38, 0.38])
    ax_table.set_facecolor("#161B22")
    ax_table.axis('off')
    ax_table.set_title("Facilities by Type", fontsize=12, color=ACCENT, pad=8)
    col_labels = ["Facility Type", "Count", "% of Total"]
    table_data = []
    for ft in type_order:
        cnt = type_counts.get(ft, 0)
        if cnt == 0:
            continue
        table_data.append([ft, str(cnt), f"{cnt/total_fac*100:.1f}%"])
    tbl = ax_table.table(cellText=table_data, colLabels=col_labels,
                          loc='center', cellLoc='left')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_facecolor("#1E2530" if r % 2 == 0 else "#161B22")
        cell.set_text_props(color='white')
        cell.set_edgecolor('#333')
        if r == 0:
            cell.set_facecolor("#1A3A5C")
            cell.set_text_props(color=ACCENT, fontweight='bold')

    # Donut chart
    ax_donut = fig.add_axes([0.45, 0.06, 0.52, 0.66])
    ax_donut.set_facecolor(BG)
    donut_types = [ft for ft in type_order if type_counts.get(ft, 0) > 0]
    donut_vals  = [type_counts[ft] for ft in donut_types]
    donut_cols  = [TYPE_COLORS[ft] for ft in donut_types]
    wedges, texts, autotexts = ax_donut.pie(
        donut_vals, labels=None, colors=donut_cols,
        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
        pctdistance=0.80, startangle=90,
        wedgeprops=dict(width=0.55, edgecolor=BG, linewidth=1.5)
    )
    for at in autotexts:
        at.set_color('white')
        at.set_fontsize(8)
    ax_donut.legend(wedges, [f"{t} ({v})" for t, v in zip(donut_types, donut_vals)],
                    loc='lower right', fontsize=8, labelcolor='white',
                    facecolor='#1A1F2E', edgecolor='#444')
    ax_donut.set_title("Facility Distribution by Type", fontsize=13, color='white', pad=10)

    plt.tight_layout(rect=[0, 0, 1, 1])
    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 1 done (Cover)")

    # ── PAGE 2: Facility Inventory Table ──────────────────────────────────────
    fig = plt.figure(figsize=(17, 11), facecolor=BG)
    set_dark(fig)

    ax_hdr = fig.add_axes([0, 0.93, 1, 0.07])
    ax_hdr.axis('off')
    ax_hdr.text(0.5, 0.5, "Facility Inventory", ha='center', va='center',
                fontsize=18, fontweight='bold', color='white')

    fac_sorted = facilities.sort_values(['facility_type', 'name']).reset_index(drop=True)
    table_cols = ['device_id', 'name', 'facility_type', 'region', 'lat', 'lon', 'meas_count']
    col_headers = ['Device ID', 'Name', 'Type', 'Region', 'Lat', 'Lon', 'Measurements']

    rows_per_page = 38
    n_pages = int(np.ceil(len(fac_sorted) / rows_per_page))

    for pg in range(n_pages):
        if pg > 0:
            pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
            plt.close(fig)
            fig = plt.figure(figsize=(17, 11), facecolor=BG)
            set_dark(fig)
            ax_hdr2 = fig.add_axes([0, 0.93, 1, 0.07])
            ax_hdr2.axis('off')
            ax_hdr2.text(0.5, 0.5, f"Facility Inventory (cont. {pg+1}/{n_pages})",
                         ha='center', va='center', fontsize=18, fontweight='bold', color='white')

        chunk = fac_sorted.iloc[pg*rows_per_page:(pg+1)*rows_per_page]
        cell_data = []
        for _, row in chunk.iterrows():
            cell_data.append([
                trunc(row['device_id'], 20),
                trunc(row['name'], 38),
                row['facility_type'],
                trunc(row['region'], 22),
                f"{row['lat']:.4f}" if pd.notna(row['lat']) else "N/A",
                f"{row['lon']:.4f}" if pd.notna(row['lon']) else "N/A",
                f"{row['meas_count']:,}",
            ])

        ax_t = fig.add_axes([0.01, 0.02, 0.98, 0.90])
        ax_t.axis('off')
        tbl = ax_t.table(cellText=cell_data, colLabels=col_headers, loc='upper center',
                          cellLoc='left')
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(7.5)
        tbl.auto_set_column_width(col=list(range(len(col_headers))))
        for (r, c), cell in tbl.get_celld().items():
            if r == 0:
                cell.set_facecolor("#1A3A5C")
                cell.set_text_props(color=ACCENT, fontweight='bold')
            else:
                cell.set_facecolor("#1E2530" if r % 2 == 1 else "#161B22")
                cell.set_text_props(color='white')
            cell.set_edgecolor('#2A2A2A')

    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 2 done (Inventory table)")

    # ── PAGE 3: Top Industrial Emitters ───────────────────────────────────────
    poll_show = [
        ("SO2 (mg/m\u00b3)",  "SO2"),
        ("NO2 (mg/m\u00b3)",  "NO2"),
        ("NOx (mg/m\u00b3)",  "NOx"),
        ("CO (mg/m\u00b3)",   "CO"),
        ("PM2.5 (mg/m\u00b3)","PM2.5"),
        ("PM10 (mg/m\u00b3)", "PM10"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(17, 11), facecolor=BG)
    set_dark(fig, axes.flatten())
    fig.suptitle("Top 10 Industrial Emitters by Mean Concentration",
                 fontsize=16, fontweight='bold', color='white', y=0.98)

    for idx, (poll_col, short) in enumerate(poll_show):
        ax = axes[idx // 3][idx % 3]
        col_mean = f'{short}_mean'
        if col_mean not in facilities.columns:
            ax.text(0.5, 0.5, f"No data: {short}", ha='center', va='center', color=FG)
            ax.axis('off')
            continue
        top10 = facilities.nlargest(10, col_mean)[['name', col_mean, 'facility_type']].dropna(subset=[col_mean])
        if top10.empty:
            ax.text(0.5, 0.5, f"No data: {short}", ha='center', va='center', color=FG)
            ax.axis('off')
            continue
        colors_bar = [TYPE_COLORS.get(ft, '#888') for ft in top10['facility_type']]
        bars = ax.barh(range(len(top10)), top10[col_mean].values, color=colors_bar,
                       edgecolor='none', height=0.7)
        ax.set_yticks(range(len(top10)))
        ax.set_yticklabels([trunc(n, 25) for n in top10['name']], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel(f"Mean {short} (mg/m3)", fontsize=8)
        ax.set_title(short, fontsize=11, color=ACCENT)
        ax.grid(axis='x', alpha=0.3)
        for bar, val in zip(bars, top10[col_mean].values):
            ax.text(bar.get_width() * 1.02, bar.get_y() + bar.get_height()/2,
                    f'{val:.4f}', va='center', fontsize=6.5, color=FG)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 3 done (Top emitters)")

    # ── PAGE 4: Exceedance Analysis ────────────────────────────────────────────
    fig = plt.figure(figsize=(17, 11), facecolor=BG)
    set_dark(fig)
    fig.suptitle("WHO Guideline Exceedance Analysis", fontsize=16,
                 fontweight='bold', color='white', y=0.98)

    who_polls = [("PM2.5","PM2.5 (mg/m\u00b3)"),("PM10","PM10 (mg/m\u00b3)"),
                 ("SO2","SO2 (mg/m\u00b3)"),("NO2","NO2 (mg/m\u00b3)"),("CO","CO (mg/m\u00b3)")]

    # Bar chart: exceedances by facility type
    ax1 = fig.add_axes([0.05, 0.52, 0.90, 0.40])
    ax1.set_facecolor(BG)

    exc_by_type = {}
    for short, poll_col in who_polls:
        col_exc = f'{short}_exc'
        if col_exc not in facilities.columns:
            continue
        g = facilities.groupby('facility_type')[col_exc].sum()
        exc_by_type[short] = g

    exc_df = pd.DataFrame(exc_by_type).fillna(0)
    exc_df = exc_df[exc_df.sum(axis=1) > 0]

    if not exc_df.empty:
        exc_colors = ['#E63946','#FFD700','#F4A261','#4A90D9','#2A9D8F']
        bottom = np.zeros(len(exc_df))
        xticks = range(len(exc_df))
        for i, (col, color) in enumerate(zip(exc_df.columns, exc_colors)):
            ax1.bar(xticks, exc_df[col].values, bottom=bottom, color=color,
                    label=col, edgecolor='none', width=0.6)
            bottom += exc_df[col].values
        ax1.set_xticks(xticks)
        ax1.set_xticklabels(exc_df.index, rotation=25, ha='right', fontsize=9)
        ax1.set_ylabel("Total Exceedance Readings", fontsize=9)
        ax1.set_title("Exceedances by Facility Type (Stacked by Pollutant)", fontsize=11, color=ACCENT)
        ax1.legend(fontsize=8, labelcolor='white', facecolor='#1A1F2E', edgecolor='#444')
        ax1.grid(axis='y', alpha=0.3)

    # Table: top exceedance facilities
    ax2 = fig.add_axes([0.03, 0.04, 0.94, 0.44])
    ax2.axis('off')
    ax2.set_facecolor(BG)

    exc_cols = [f'{s}_exc' for s, _ in who_polls if f'{s}_exc' in facilities.columns]
    facilities['total_exc'] = facilities[exc_cols].sum(axis=1) if exc_cols else 0
    top_exc = facilities.nlargest(15, 'total_exc')[
        ['name','facility_type','region'] + exc_cols + ['total_exc']
    ].copy()

    th_headers = ['Name','Type','Region'] + [s for s, _ in who_polls if f'{s}_exc' in facilities.columns] + ['Total Exc.']
    th_data = []
    for _, row in top_exc.iterrows():
        r = [trunc(row['name'],30), row['facility_type'], trunc(row['region'],18)]
        for s, _ in who_polls:
            col_e = f'{s}_exc'
            if col_e in facilities.columns:
                r.append(str(int(row[col_e])))
        r.append(str(int(row['total_exc'])))
        th_data.append(r)

    tbl2 = ax2.table(cellText=th_data, colLabels=th_headers, loc='upper center', cellLoc='center')
    tbl2.auto_set_font_size(False)
    tbl2.set_fontsize(8)
    tbl2.auto_set_column_width(col=list(range(len(th_headers))))
    for (r, c), cell in tbl2.get_celld().items():
        if r == 0:
            cell.set_facecolor("#1A3A5C")
            cell.set_text_props(color=ACCENT, fontweight='bold')
        else:
            cell.set_facecolor("#1E2530" if r % 2 == 1 else "#161B22")
            cell.set_text_props(color='white')
        cell.set_edgecolor('#2A2A2A')
    ax2.set_title("Facilities with Highest WHO Exceedance Counts (Top 15)",
                  fontsize=11, color=ACCENT, pad=5)

    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 4 done (Exceedances)")

    # ── PAGE 5: Time Series ────────────────────────────────────────────────────
    fig = plt.figure(figsize=(17, 11), facecolor=BG)
    set_dark(fig)
    fig.suptitle("Daily Mean Concentrations: Key Industrial Sites",
                 fontsize=15, fontweight='bold', color='white', y=0.99)

    so2_col = "SO2 (mg/m\u00b3)"
    no2_col = "NO2 (mg/m\u00b3)"
    top5_so2 = facilities.nlargest(5, 'SO2_mean')['device_id'].tolist() if 'SO2_mean' in facilities.columns else []
    top5_no2 = facilities.nlargest(5, 'NO2_mean')['device_id'].tolist() if 'NO2_mean' in facilities.columns else []
    key_devs = list(dict.fromkeys(top5_so2 + top5_no2))[:8]

    n_devs = len(key_devs)
    if n_devs == 0:
        ax_ts = fig.add_subplot(111)
        ax_ts.text(0.5, 0.5, "No data available", ha='center', va='center', color=FG)
        ax_ts.axis('off')
    else:
        gs = gridspec.GridSpec(n_devs, 2, figure=fig, hspace=0.55, wspace=0.3,
                               left=0.08, right=0.97, top=0.94, bottom=0.05)
        ts_colors = ['#E63946','#FFD700','#F4A261','#4A90D9','#2A9D8F',
                     '#A8DADC','#E9C46A','#8B4513']
        for i, dev_id in enumerate(key_devs):
            dev_data = df[df[DEV_COL] == dev_id].copy()
            dev_data = dev_data.set_index(TS_COL).sort_index()
            dev_name = facilities.loc[facilities['device_id']==dev_id,'name'].values
            dev_name = trunc(dev_name[0], 32) if len(dev_name) > 0 else dev_id
            color = ts_colors[i % len(ts_colors)]

            ax_so2 = fig.add_subplot(gs[i, 0])
            ax_no2 = fig.add_subplot(gs[i, 1])

            for ax_ts, poll_col, label in [(ax_so2, so2_col, 'SO2'), (ax_no2, no2_col, 'NO2')]:
                ax_ts.set_facecolor(BG)
                for spine in ax_ts.spines.values():
                    spine.set_edgecolor('#333')
                ax_ts.tick_params(colors=FG, labelsize=6)
                if poll_col in dev_data.columns:
                    daily = dev_data[poll_col].resample('D').mean().dropna()
                    if not daily.empty:
                        ax_ts.plot(daily.index, daily.values, color=color,
                                   lw=1.2, marker='.', ms=3)
                        ax_ts.fill_between(daily.index, daily.values, alpha=0.15, color=color)
                ax_ts.set_ylabel(label, fontsize=6.5, color=FG)
                ax_ts.grid(alpha=0.2)
                if i == 0:
                    ax_ts.set_title(label + " (mg/m3)", fontsize=8, color=ACCENT)
                if i == n_devs - 1:
                    ax_ts.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m-%d'))
                    plt.setp(ax_ts.xaxis.get_majorticklabels(), rotation=30, ha='right')
                else:
                    ax_ts.set_xticklabels([])

            ax_so2.set_ylabel(dev_name, fontsize=6.5, color=color,
                              rotation=0, ha='right', va='center', labelpad=5)

    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 5 done (Time series)")

    # ── PAGE 6: Spatial Distribution ──────────────────────────────────────────
    poll_map_list = [
        ("SO2 (mg/m\u00b3)",  "SO2",   "Reds"),
        ("NO2 (mg/m\u00b3)",  "NO2",   "Oranges"),
        ("CO (mg/m\u00b3)",   "CO",    "YlOrRd"),
        ("PM2.5 (mg/m\u00b3)","PM2.5", "plasma"),
        ("NH3 (mg/m\u00b3)",  "NH3",   "Greens"),
        ("H2S (mg/m\u00b3)",  "H2S",   "Purples"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(17, 11), facecolor=BG)
    set_dark(fig, axes.flatten())
    fig.suptitle("Spatial Distribution of Mean Pollutant Concentrations",
                 fontsize=15, fontweight='bold', color='white', y=0.99)

    for idx, (poll_col, short, cmap) in enumerate(poll_map_list):
        ax = axes[idx // 3][idx % 3]
        ax.set_facecolor(BG)
        draw_uz_regions(ax, facecolor="#161B22", edgecolor="#555", lw=0.8)

        col_mean = f'{short}_mean'
        sub = facilities.dropna(subset=['lat', 'lon', col_mean]) if col_mean in facilities.columns else pd.DataFrame()

        if not sub.empty:
            vmin, vmax = sub[col_mean].quantile(0.05), sub[col_mean].quantile(0.95)
            vmax = max(vmax, vmin + 1e-9)
            sc = ax.scatter(sub['lon'], sub['lat'], c=sub[col_mean],
                            cmap=cmap, vmin=vmin, vmax=vmax,
                            s=40, alpha=0.85, edgecolors='none', zorder=3)
            cbar = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
            cbar.ax.tick_params(colors=FG, labelsize=6)
            cbar.set_label("mg/m3", fontsize=7, color=FG)

        ax.set_xlim(MAP_XLIM)
        ax.set_ylim(MAP_YLIM)
        ax.set_title(short, fontsize=11, color=ACCENT)
        ax.set_xlabel("Lon", fontsize=7)
        ax.set_ylabel("Lat", fontsize=7)
        ax.tick_params(labelsize=6)
        for spine in ax.spines.values():
            spine.set_edgecolor('#333')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 6 done (Spatial maps)")

    # ── PAGE 7: Findings ──────────────────────────────────────────────────────
    fig = plt.figure(figsize=(17, 11), facecolor=BG)
    set_dark(fig)

    ax_txt = fig.add_axes([0.05, 0.05, 0.90, 0.90])
    ax_txt.axis('off')
    ax_txt.set_facecolor(BG)

    ax_txt.text(0.5, 0.97, "Key Findings & Environmental Concerns",
                ha='center', va='top', fontsize=18, fontweight='bold', color='white',
                transform=ax_txt.transAxes)

    # Build findings text
    findings = []

    # Major emitters
    findings.append(("1. MAJOR EMITTERS", ACCENT))
    if 'SO2_mean' in facilities.columns:
        top_so2 = facilities.nlargest(3, 'SO2_mean')[['name','SO2_mean']].dropna()
        for _, r in top_so2.iterrows():
            findings.append((f"  - {trunc(r['name'],50)}: SO2 mean = {r['SO2_mean']:.5f} mg/m3", FG))
    if 'NO2_mean' in facilities.columns:
        top_no2 = facilities.nlargest(3, 'NO2_mean')[['name','NO2_mean']].dropna()
        for _, r in top_no2.iterrows():
            findings.append((f"  - {trunc(r['name'],50)}: NO2 mean = {r['NO2_mean']:.5f} mg/m3", FG))

    findings.append(("", FG))
    findings.append(("2. WHO EXCEEDANCE HIGHLIGHTS", ACCENT))
    if 'total_exc' in facilities.columns:
        top_t = facilities.nlargest(5, 'total_exc')[['name','facility_type','total_exc']].dropna()
        for _, r in top_t.iterrows():
            findings.append((
                f"  - {trunc(r['name'],45)} [{r['facility_type']}]: {int(r['total_exc']):,} exceedance readings",
                "#FFD700" if r['total_exc'] > 1000 else FG
            ))

    findings.append(("", FG))
    findings.append(("3. GEOGRAPHIC HOTSPOTS", ACCENT))
    if 'region' in facilities.columns:
        region_counts = facilities.groupby('region')['meas_count'].sum().nlargest(5)
        for reg, cnt in region_counts.items():
            findings.append((f"  - {reg}: {cnt:,} total measurements", FG))

    findings.append(("", FG))
    findings.append(("4. FACILITY TYPE SUMMARY", ACCENT))
    for ft in type_order:
        cnt = type_counts.get(ft, 0)
        if cnt > 0:
            findings.append((f"  - {ft}: {cnt} facilities", FG))

    findings.append(("", FG))
    findings.append(("5. DATA QUALITY NOTES", ACCENT))
    total_rows = len(df)
    for poll_col in POLLUTANTS[:5]:
        if poll_col in df.columns:
            valid = df[poll_col].count()
            pct = valid / total_rows * 100
            short_p = poll_col.split(' ')[0]
            findings.append((f"  - {short_p}: {valid:,} valid readings ({pct:.1f}% coverage)", FG))

    findings.append(("", FG))
    findings.append(("6. RECOMMENDATIONS", ACCENT))
    findings.append(("  - Prioritize continuous SO2 and NO2 monitoring near power plants and chemical facilities.", FG))
    findings.append(("  - Investigate facilities with >1000 WHO exceedance events for regulatory compliance.", FG))
    findings.append(("  - Expand spatial coverage in regions with limited monitoring stations.", FG))
    findings.append(("  - Cross-reference emissions data with satellite (Sentinel-5P) observations for validation.", FG))

    y_pos = 0.91
    for text, color in findings:
        if text == "":
            y_pos -= 0.013
            continue
        fontsize = 11 if color == ACCENT else 9.5
        fontweight = 'bold' if color == ACCENT else 'normal'
        ax_txt.text(0.0, y_pos, text, ha='left', va='top',
                    fontsize=fontsize, color=color, fontweight=fontweight,
                    transform=ax_txt.transAxes)
        y_pos -= 0.033 if color == ACCENT else 0.028
        if y_pos < 0.0:
            break

    pdf.savefig(fig, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print("    Page 7 done (Findings)")

print("\n=== ANALYSIS COMPLETE ===")
print(f"Output files:")
print(f"  MAP:    {MAP_OUT}")
print(f"  REPORT: {PDF_OUT}")
print(f"\nSummary:")
print(f"  Total facilities: {len(facilities)}")
print(f"  Total measurements: {len(df):,}")
print(f"  Facility types found:")
for ft, cnt in facilities['facility_type'].value_counts().items():
    print(f"    {ft}: {cnt}")
