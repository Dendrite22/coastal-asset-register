# =============================================================================
# Riverwall Asset Register V2 — Attribute Replacement Layer Builder
# Paste into QGIS Python Console and Run.
#
# Reads:   V2 (Final)/riverwall_assets/riverwall_assets.gpkg  (geometry, by fid)
#          V2 (Final)/riverwall_assets_attribute_update.csv   (new attributes)
# Writes:  V2 (Final)/riverwall_assets_v2.gpkg   — all features, new schema
#          V2 (Final)/riverwall_assets_v2.qgs    — QGIS project
#
# fid is the join key — geometry is preserved exactly, all attributes replaced.
#
# Child asset logic:
#   CSV child rows have Unit_ID="0"; their true ID is in Child_Unit_ID column.
#   In the GPKG, the self-referencing relation uses:
#     Child_Unit_ID field → parent's Unit_ID  (same as original)
# =============================================================================

from osgeo import ogr, osr
from qgis.core import (
    QgsProject, QgsVectorLayer,
    QgsEditorWidgetSetup, QgsDefaultValue, QgsFieldConstraints,
    QgsCoordinateReferenceSystem, QgsRelation,
)
import os, csv, sqlite3
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR   = r"C:\Users\Damia\Documents\Projects\coastal-asset-register"
V2_DIR     = os.path.join(BASE_DIR, "V2 (Final)")
SRC_GPKG   = os.path.join(V2_DIR, "riverwall_assets", "riverwall_assets.gpkg")
CSV_PATH   = os.path.join(V2_DIR, "riverwall_assets_attribute_update.csv")
OUT_GPKG   = os.path.join(V2_DIR, "riverwall_assets_v2.gpkg")
QGS_PATH   = os.path.join(V2_DIR, "riverwall_assets_v2.qgs")
LAYER_NAME = "Riverwall_Assets"
# ─────────────────────────────────────────────────────────────────────────────


# ── 1. Parse CSV ──────────────────────────────────────────────────────────────
def _money(v):
    """' 152,310 ' → 152310.0 | ' - ' / '' → None"""
    if v is None:
        return None
    s = v.strip().replace(',', '').replace('$', '').replace(' ', '')
    return None if (not s or s == '-') else float(s)

def _int(v):
    if v is None:
        return None
    s = v.strip()
    return None if (not s or s == '-') else int(float(s))

def _real(v):
    if v is None:
        return None
    s = v.strip().replace(',', '')
    return None if (not s or s == '-') else float(s)

def _text(v):
    s = (v or '').strip()
    return s or None

def _date(v):
    if v is None:
        return None
    s = v.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


csv_rows = {}
with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    # Headers with embedded newlines — match by substring
    cond_key = next(h for h in headers if 'Condition' in h and 'Rating' in h)
    aasb_key = next(h for h in headers if 'AASB' in h)

    for row in reader:
        fid_s = (row.get('fid') or '').strip()
        if not fid_s:
            continue
        try:
            fid = int(fid_s)
        except ValueError:
            continue

        csv_uid  = (row.get('Unit_ID')       or '').strip()
        csv_cid  = (row.get('Child_Unit_ID') or '').strip()
        csv_pid  = (row.get('Parent_Unit_ID') or '').strip()

        # Child rows have Unit_ID="0"; their real ID lives in Child_Unit_ID column.
        # GPKG relation: child's Child_Unit_ID field = parent's Unit_ID.
        is_child = (csv_uid == '0' or not csv_uid)
        gpkg_unit_id       = csv_cid if is_child else csv_uid
        gpkg_child_unit_id = csv_pid if is_child else None

        csv_rows[fid] = {
            'Parent_Unit_ID':           _text(csv_pid),
            'Unit_ID':                  _text(gpkg_unit_id),
            'Child_Unit_ID':            _text(gpkg_child_unit_id),
            'Location_Description':     _text(row.get('Location_Description')),
            'Location_Area':             _text(row.get('LOCATION_Description')),
            'Material':                 _text(row.get('Material')),
            'Asset_Type':               _text(row.get('Asset_Type')),
            'Length_m':                 _real(row.get('Length (m)')),
            'Construction_Year':        _int(row.get('Construction_Year (year)')),
            'Replacement_Cost':         _money(row.get('Replacement_Cost ($)')),
            'Condition_Rating':         _int(row.get(cond_key)),
            'Fair_Value_Valuation':     _money(row.get('Fair_Value_Valuation ($)')),
            'Useful_Life':              _real(row.get('Useful_Life (years)')),
            'Remaining_Useful_Life':    _real(row.get('Remaining_Useful_Life (years)')),
            'Residual_Value':           _money(row.get('Residual_Value ($)')),
            'Depreciation_Method_Rate': _text(row.get('Depreciation_Method_Rate')),
            'Depreciation_Expense':     _money(row.get('Depreciation_Expense ($)')),
            'Accumulated_Depreciation': _money(row.get('Accumulated_Depreciation ($)')),
            'AASB13_Input_Level':       _int(row.get(aasb_key)),
            'Depreciation_Method':      _text(row.get('Depreciation Method')),
            'Date_of_Inspection':       _date(row.get('Date_of_Inspection')),
            'Photo_1':                  _text(row.get('Photo_1')),
            'Photo_2':                  _text(row.get('Photo_2')),
            'Photo_3':                  _text(row.get('Photo_3')),
        }

print(f"[1/5] CSV: {len(csv_rows)} records parsed.")


# ── 2. Create output GeoPackage ───────────────────────────────────────────────
_GDA2020_MGA50_WKT = (
    'PROJCS["GDA2020 / MGA zone 50",'
    'GEOGCS["GDA2020",'
    'DATUM["GDA2020",SPHEROID["GRS 1980",6378137,298.257222101]],'
    'PRIMEM["Greenwich",0],'
    'UNIT["degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["latitude_of_origin",0],'
    'PARAMETER["central_meridian",117],'
    'PARAMETER["scale_factor",0.9996],'
    'PARAMETER["false_easting",500000],'
    'PARAMETER["false_northing",10000000],'
    'UNIT["metre",1]]'
)

drv = ogr.GetDriverByName("GPKG")
if os.path.exists(OUT_GPKG):
    drv.DeleteDataSource(OUT_GPKG)

ds_out  = drv.CreateDataSource(OUT_GPKG)
srs_out = osr.SpatialReference()
srs_out.ImportFromWkt(_GDA2020_MGA50_WKT)

out_lyr = ds_out.CreateLayer(LAYER_NAME, srs_out, ogr.wkbMultiLineString)

def _s(name, w=254): f = ogr.FieldDefn(name, ogr.OFTString);  f.SetWidth(w); return f
def _r(name):        return ogr.FieldDefn(name, ogr.OFTReal)
def _i(name):        return ogr.FieldDefn(name, ogr.OFTInteger)
def _d(name):        return ogr.FieldDefn(name, ogr.OFTDate)

for fld in [
    _s("Parent_Unit_ID",          100),
    _s("Unit_ID",                 100),   # NOT NULL (enforced by QGIS constraint)
    _s("Child_Unit_ID",           100),   # parent's Unit_ID — null on parent features
    _s("Location_Description",    500),   # long description, e.g. "Riverwall 01 - ..."
    _s("Location_Area",           254),   # area name, e.g. "Heirisson Island"
    _s("Material",                254),
    _s("Asset_Type",               50),
    _r("Length_m"),
    _i("Construction_Year"),
    _r("Replacement_Cost"),
    _i("Condition_Rating"),
    _r("Fair_Value_Valuation"),
    _r("Useful_Life"),
    _r("Remaining_Useful_Life"),
    _r("Residual_Value"),
    _s("Depreciation_Method_Rate", 50),   # rate string, e.g. "1.25%"
    _r("Depreciation_Expense"),
    _r("Accumulated_Depreciation"),
    _i("AASB13_Input_Level"),
    _s("Depreciation_Method",      50),   # "Straight Line" / "Diminishing Value"
    _d("Date_of_Inspection"),
    _s("Photo_1",                 254),
    _s("Photo_2",                 254),
    _s("Photo_3",                 254),
]:
    out_lyr.CreateField(fld)

print("[2/5] GeoPackage schema created.")


# ── 3. Copy geometry from source GPKG, join CSV attributes ────────────────────
ds_src  = ogr.Open(SRC_GPKG)
src_lyr = ds_src.GetLayerByName(LAYER_NAME)

written   = 0
no_csv    = []
no_geom   = []

for src_feat in src_lyr:
    fid  = src_feat.GetFID()
    geom = src_feat.GetGeometryRef()

    if geom is None:
        no_geom.append(fid)
        continue

    attrs = csv_rows.get(fid)
    if attrs is None:
        no_csv.append(fid)
        continue

    feat_out = ogr.Feature(out_lyr.GetLayerDefn())
    feat_out.SetGeometry(ogr.ForceToMultiLineString(geom.Clone()))

    for field, val in attrs.items():
        if val is None:
            continue
        feat_out.SetField(field, val)

    out_lyr.CreateFeature(feat_out)
    written += 1

ds_src = None
ds_out = None   # flush and close

# Patch the GPKG SRS table so QGIS reads EPSG:28350 (GDA94/MGA Zone 50) directly.
_conn = sqlite3.connect(OUT_GPKG)
_cur  = _conn.cursor()
_cur.execute(
    "SELECT srs_id FROM gpkg_geometry_columns WHERE table_name=?", (LAYER_NAME,)
)
_srs_row = _cur.fetchone()
if _srs_row:
    _cur.execute(
        """UPDATE gpkg_spatial_ref_sys
           SET srs_name                = 'GDA94 / MGA zone 50',
               organization            = 'EPSG',
               organization_coordsys_id = 28350,
               definition              = ?
           WHERE srs_id = ?""",
        (_GDA2020_MGA50_WKT, _srs_row[0]),
    )
    _conn.commit()
_conn.close()

print(f"[3/5] {written} features written — GPKG SRS forced to EPSG:28350.")
if no_csv:
    print(f"       WARNING — no CSV row for fid(s): {no_csv}")
if no_geom:
    print(f"       WARNING — no geometry for fid(s): {no_geom}")


# ── 4. Load layer into QGIS ───────────────────────────────────────────────────
vlyr = QgsVectorLayer(f"{OUT_GPKG}|layername={LAYER_NAME}", LAYER_NAME, "ogr")
assert vlyr.isValid(), f"Layer failed to load — check: {OUT_GPKG}"

_qgs_crs = QgsCoordinateReferenceSystem("EPSG:7854")
if not _qgs_crs.isValid():
    _qgs_crs = QgsCoordinateReferenceSystem("EPSG:28350")
vlyr.setCrs(_qgs_crs)

# Field aliases (display labels in attribute form)
ALIASES = {
    "Parent_Unit_ID":           "Parent Unit ID",
    "Unit_ID":                  "Unit ID *",
    "Child_Unit_ID":            "Child Unit ID (select parent)",
    "Location_Description":     "Location Description",
    "Location_Area":            "Location Area",
    "Material":                 "Material",
    "Asset_Type":               "Asset Type",
    "Length_m":                 "Length (m)",
    "Construction_Year":        "Construction Year",
    "Replacement_Cost":         "Replacement Cost ($)",
    "Condition_Rating":         "Condition Rating (1–5)",
    "Fair_Value_Valuation":     "Fair Value Valuation ($)",
    "Useful_Life":              "Useful Life (years)",
    "Remaining_Useful_Life":    "Remaining Useful Life (years)",
    "Residual_Value":           "Residual Value ($)",
    "Depreciation_Method_Rate": "Depreciation Method Rate",
    "Depreciation_Expense":     "Depreciation Expense ($)",
    "Accumulated_Depreciation": "Accumulated Depreciation ($)",
    "AASB13_Input_Level":       "AASB13 Input Level (1–3)",
    "Depreciation_Method":      "Depreciation Method",
    "Date_of_Inspection":       "Date of Inspection",
    "Photo_1":                  "Photo 1",
    "Photo_2":                  "Photo 2",
    "Photo_3":                  "Photo 3",
}
for fname, alias in ALIASES.items():
    idx = vlyr.fields().indexFromName(fname)
    if idx >= 0:
        vlyr.setFieldAlias(idx, alias)

# Must add to project BEFORE Value Relation widget setup (needs layer ID)
QgsProject.instance().addMapLayer(vlyr)


# ── 5. Widget configurations ──────────────────────────────────────────────────
def _idx(n):
    return vlyr.fields().indexFromName(n)

def value_map(name, values):
    cfg = {"map": [{str(v): str(v)} for v in values]}
    vlyr.setEditorWidgetSetup(_idx(name), QgsEditorWidgetSetup("ValueMap", cfg))

def date_widget(name):
    cfg = {"display_format": "yyyy-MM-dd", "field_format": "yyyy-MM-dd", "calendar_popup": True}
    vlyr.setEditorWidgetSetup(_idx(name), QgsEditorWidgetSetup("DateTime", cfg))

def attachment(name):
    cfg = {
        "DocumentViewer": 0,
        "FileWidget": True,
        "FileWidgetButton": True,
        "FileWidgetFilter": "Images (*.jpg *.jpeg *.png *.tif *.tiff)",
        "RelativeStorage": 1,   # paths relative to project file
        "StorageMode": 0,
    }
    vlyr.setEditorWidgetSetup(_idx(name), QgsEditorWidgetSetup("ExternalResource", cfg))

# Not-null constraint on Unit_ID
vlyr.setFieldConstraint(_idx("Unit_ID"), QgsFieldConstraints.ConstraintNotNull)

# Child_Unit_ID — Value Relation back to Unit_ID in this layer (self-referencing).
# Filter excludes features that are already children (prevents circular refs).
# Dropdown shows Location_Description so inspectors can identify the parent by name.
vlyr.setEditorWidgetSetup(_idx("Child_Unit_ID"), QgsEditorWidgetSetup("ValueRelation", {
    "Layer":            vlyr.id(),
    "Key":              "Unit_ID",
    "Value":            "Location_Description",
    "AllowMulti":       False,
    "AllowNull":        True,
    "FilterExpression": '"Child_Unit_ID" IS NULL OR "Child_Unit_ID" = \'\'',
    "NofColumns":       1,
    "OrderByValue":     True,
    "UseCompleter":     True,
}))

# Child feature default values (applyOnUpdate=False = creation only)
vlyr.setDefaultValueDefinition(
    _idx("Unit_ID"),
    QgsDefaultValue(
        "concat(current_parent_value('Unit_ID'), '_C', format_date(now(), 'yyMMddHHmm'))",
        False,
    )
)
vlyr.setDefaultValueDefinition(
    _idx("Parent_Unit_ID"),
    QgsDefaultValue("current_parent_value('Unit_ID')", False)
)
vlyr.setDefaultValueDefinition(
    _idx("Child_Unit_ID"),
    QgsDefaultValue("current_parent_value('Unit_ID')", False)
)
vlyr.setDefaultValueDefinition(
    _idx("Location_Description"),
    QgsDefaultValue("current_parent_value('Location_Description')", False)
)
vlyr.setDefaultValueDefinition(
    _idx("Location_Area"),
    QgsDefaultValue("current_parent_value('Location_Area')", False)
)
vlyr.setDefaultValueDefinition(
    _idx("Material"),
    QgsDefaultValue("current_parent_value('Material')", False)
)
vlyr.setDefaultValueDefinition(
    _idx("Asset_Type"),
    QgsDefaultValue("current_parent_value('Asset_Type')", False)
)

# Dropdowns
value_map("Asset_Type", ["Revetment", "Wall", "Gabion", "Beach", "Soft Measure", "Bioengineering"])
value_map("Condition_Rating", [1, 2, 3, 4, 5])
value_map("AASB13_Input_Level", [1, 2, 3])
value_map("Depreciation_Method", ["Straight Line", "Diminishing Value"])

# Date of Inspection — calendar picker, default today
date_widget("Date_of_Inspection")
vlyr.setDefaultValueDefinition(
    _idx("Date_of_Inspection"), QgsDefaultValue("to_date(now())")
)

# Photo attachment widgets
for p in ("Photo_1", "Photo_2", "Photo_3"):
    attachment(p)

print("[4/5] Widget configurations applied.")


# ── 6. Parent-child QGIS Relation (self-referencing) ─────────────────────────
rel = QgsRelation()
rel.setId("riverwall_child_parent")
rel.setName("Child Assets")
rel.setReferencingLayer(vlyr.id())          # child: holds Child_Unit_ID
rel.addFieldPair("Child_Unit_ID", "Unit_ID")
rel.setReferencedLayer(vlyr.id())           # parent: holds Unit_ID
QgsProject.instance().relationManager().addRelation(rel)


# ── 7. Save project ───────────────────────────────────────────────────────────
QgsProject.instance().setCrs(_qgs_crs)
QgsProject.instance().setFileName(QGS_PATH)

from qgis.utils import iface
iface.mapCanvas().setRotation(0)
iface.setActiveLayer(vlyr)
iface.zoomToActiveLayer()

QgsProject.instance().write()

print("[5/5] Project saved.")
print()
print(f"  Layer   : {LAYER_NAME}  ({written} features)")
print(f"  GPKG    : {OUT_GPKG}")
print(f"  Project : {QGS_PATH}")
print(f"  CRS     : GDA2020 / MGA Zone 50 (EPSG:7854 / fallback EPSG:28350)")
print()
print("Schema: 24 attribute fields — all sourced from riverwall_assets_attribute_update.csv")
print("Geometry: preserved exactly from V2 (Final)/riverwall_assets/riverwall_assets.gpkg")
