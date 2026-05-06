# =============================================================================
# Coastal Asset Register — QGIS Layer Builder
# Paste the entire contents of this file into the QGIS Python Console and run.
#
# Outputs:
#   <PROJECT_DIR>/coastal_assets.gpkg   — GeoPackage with polyline layer
#   <PROJECT_DIR>/coastal_assets.qgs    — QGIS project file
# =============================================================================

from osgeo import ogr, osr
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsEditorWidgetSetup,
    QgsDefaultValue,
    QgsFieldConstraints,
    QgsCoordinateReferenceSystem,
)
import os

# ── CONFIG — review before running ───────────────────────────────────────────
PROJECT_DIR = r"C:\Users\Damia\Documents\Projects\coastal-asset-register"
GPKG_NAME   = "coastal_assets.gpkg"
LAYER_NAME  = "Shoreline_Assets"
QGS_NAME    = "coastal_assets.qgs"

# Edit this list to match your material types before running
MATERIALS = [
    "Concrete",
    "Rock / Rubble",
    "Steel",
    "Timber",
    "Geotextile",
    "Sand",
    "Vegetation",
    "PVC / HDPE",
    "Aluminium",
    "Masonry",
]
# ─────────────────────────────────────────────────────────────────────────────

gpkg_path    = os.path.join(PROJECT_DIR, GPKG_NAME)
project_path = os.path.join(PROJECT_DIR, QGS_NAME)
os.makedirs(PROJECT_DIR, exist_ok=True)

# ── 1. Create GeoPackage via OGR ─────────────────────────────────────────────
drv = ogr.GetDriverByName("GPKG")
if os.path.exists(gpkg_path):
    drv.DeleteDataSource(gpkg_path)

ds = drv.CreateDataSource(gpkg_path)

srs = osr.SpatialReference()
srs.ImportFromEPSG(7844)          # GDA2020

lyr = ds.CreateLayer(LAYER_NAME, srs, ogr.wkbMultiLineString)

def _str(name, width=255):
    f = ogr.FieldDefn(name, ogr.OFTString); f.SetWidth(width); return f

def _real(name):
    return ogr.FieldDefn(name, ogr.OFTReal)

def _int(name):
    return ogr.FieldDefn(name, ogr.OFTInteger)

def _date(name):
    return ogr.FieldDefn(name, ogr.OFTDate)

for field in [
    _str("Unit_ID"),
    _str("Child_Unit_ID"),
    _str("Unit_Description"),
    _str("Location_Description"),
    _real("Total_Length_m"),
    _str("Material"),
    _str("Asset_Type"),
    _int("Construction_Year"),
    _real("Replacement_Cost_Gross"),
    _int("Condition_Rating"),
    _real("Fair_Value_Valuation"),
    _int("Useful_Life"),
    _int("Remaining_Useful_Life"),
    _real("Residual_Value"),
    _str("Depreciation_Method_Rate"),
    _real("Depreciation_Expense"),
    _real("Accumulated_Depreciation"),
    _date("Date_of_Valuation"),
    _str("Photo_1"),
    _str("Photo_2"),
    _str("Photo_3"),
]:
    lyr.CreateField(field)

ds = None  # flush / close
print(f"[1/3] GeoPackage created: {gpkg_path}")

# ── 2. Load layer into QGIS ──────────────────────────────────────────────────
vlyr = QgsVectorLayer(f"{gpkg_path}|layername={LAYER_NAME}", LAYER_NAME, "ogr")
assert vlyr.isValid(), "Layer failed to load — check the GPKG path."

# ── 3. Field aliases (display labels in forms) ───────────────────────────────
aliases = {
    "Unit_ID":                  "Unit ID",
    "Child_Unit_ID":            "Child Unit ID",
    "Unit_Description":         "Unit Description",
    "Location_Description":     "Location Description",
    "Total_Length_m":           "Total Length (linear m)",
    "Material":                 "Material",
    "Asset_Type":               "Asset Type",
    "Construction_Year":        "Construction Year",
    "Replacement_Cost_Gross":   "Replacement Cost – Gross Value",
    "Condition_Rating":         "Condition Rating (1–5)",
    "Fair_Value_Valuation":     "Fair Value Valuation",
    "Useful_Life":              "Useful Life",
    "Remaining_Useful_Life":    "Remaining Useful Life",
    "Residual_Value":           "Residual Value",
    "Depreciation_Method_Rate": "Depreciation Method / Rate",
    "Depreciation_Expense":     "Depreciation Expense",
    "Accumulated_Depreciation": "Accumulated Depreciation",
    "Date_of_Valuation":        "Date of Valuation",
    "Photo_1":                  "Photo 1",
    "Photo_2":                  "Photo 2",
    "Photo_3":                  "Photo 3",
}

for fname, alias in aliases.items():
    idx = vlyr.fields().indexFromName(fname)
    if idx >= 0:
        vlyr.setFieldAlias(idx, alias)

# ── 4. Widget configurations ─────────────────────────────────────────────────

def _idx(name):
    return vlyr.fields().indexFromName(name)

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
        "RelativeStorage": 1,   # relative to project file
        "StorageMode": 0,       # store file path
    }
    vlyr.setEditorWidgetSetup(_idx(name), QgsEditorWidgetSetup("ExternalResource", cfg))

# Not-null constraint on Unit_ID
vlyr.setFieldConstraint(_idx("Unit_ID"), QgsFieldConstraints.ConstraintNotNull)

# Dropdown widgets
value_map("Material",                 MATERIALS)
value_map("Asset_Type",               ["Revetment", "Wall", "Gabion", "Beach", "Soft Measure", "Bioengineering"])
value_map("Condition_Rating",         [1, 2, 3, 4, 5])
value_map("Depreciation_Method_Rate", ["Straight Line", "Diminishing Value"])

# Date with default = today
date_widget("Date_of_Valuation")
vlyr.setDefaultValueDefinition(_idx("Date_of_Valuation"), QgsDefaultValue("to_date(now())"))

# Photo attachment widgets
for photo in ("Photo_1", "Photo_2", "Photo_3"):
    attachment(photo)

# ── 5. Save project ──────────────────────────────────────────────────────────
QgsProject.instance().addMapLayer(vlyr)
QgsProject.instance().setCrs(QgsCoordinateReferenceSystem("EPSG:7844"))
QgsProject.instance().setFileName(project_path)
QgsProject.instance().write()

print(f"[2/3] Layer configured and added to QGIS.")
print(f"[3/3] Project saved: {project_path}")
print("\nDone. Open the Attribute Form (F6) on a new feature to verify dropdowns.")
