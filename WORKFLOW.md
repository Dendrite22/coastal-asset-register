# Riverwall Asset Register — Project Workflow

**Project**: City of Perth Riverwall / Coastal Protection Asset Inspection  
**Last updated**: 2026-05-06  
**CRS**: GDA94 / MGA Zone 50 (EPSG:28350)  
**Format**: GeoPackage (riverwall_assets.gpkg) + QGIS project (riverwall_assets.qgs)

---

## Data Sources

| File | Description |
|---|---|
| `RiverwallForValuation/Riverwalls_For_InitialRecognition.shp` | Original spatial data — 37 parent polyline features |
| `RiverWalls_for_Valuation.xlsx` | Asset attributes — Unit ID, description, material, asset type, CoP comments |
| `Original Header Attributes.xlsx` | Target schema definition — 23 fields |

---

## 1. Initial QGIS Setup (run once)

1. Open QGIS
2. Open **Python Console** → **Show Editor** → open `build_riverwall_asset_layer.py`
3. Click **Run**
4. Script produces:
   - `riverwall_assets.gpkg` — 37 pre-filled parent features merged from shapefile + Excel
   - `riverwall_assets.qgs` — QGIS project with all widgets configured

**What is pre-filled on parent assets:**

| Field | Source |
|---|---|
| Unit ID | From shapefile/Excel |
| Unit Description | From Excel (preferred) |
| Location Description | From Excel (full text) |
| Total Length (m) | From shapefile (spatial measurement) |
| Material | From Excel |
| Asset Type | From Excel (normalised to schema values) |
| CoP Comments | From Excel Comments column |

**Valuation fields** (Replacement Cost, Fair Value, Useful Life, etc.) are left blank — completed during desktop assessment after field inspection.

---

## 2. QField Setup (before going to field)

### Install QFieldSync plugin
- QGIS → **Plugins → Manage and Install Plugins** → search **QFieldSync** → Install

### Configure and package
1. **Plugins → QFieldSync → Project Configuration**

| Layer | Setting |
|---|---|
| Riverwall_Assets | Offline editing |
| Google Hybrid (XYZ) | No action (streams over mobile data) |

2. **Plugins → QFieldSync → Package for QField**
   - Export to a local folder (e.g. `QField_Export/`)
   - Click **Create**

### Transfer to Android device
- Connect phone via USB
- Copy export folder to: `Android/data/ch.opengis.qfield/files/`
- Replace previous version if re-packaging

---

## 3. Field Collection — QField Workflow

### Open project
- QField app → **Open local file** → navigate to `riverwall_assets.qgs`

### View existing parent assets
- Tap any riverwall polyline to select it
- Tap **pencil icon** to open the attribute form
- All pre-filled fields are visible and editable

### Edit a parent asset
Fields editable in the field:
- **Condition Rating (1–5)** — dropdown
- **Asset Type** — dropdown (Revetment, Wall, Gabion, Beach, Soft Measure, Bioengineering)
- **Material** — free text
- **Inspection Notes** — free text
- **Photo 1 / 2 / 3** — tap camera icon to shoot or pick from gallery
- **Date of Valuation** — auto-fills today's date

### Create a child asset (sub-segment of a parent)
1. Tap the **parent polyline** to select it
2. Open the attribute form (pencil icon)
3. Scroll to the **Child Assets** section at the bottom
4. Tap **+**
5. Draw the child polyline on the map (tap vertices, double-tap to finish)
6. Child attribute form opens with these fields **auto-populated from parent**:
   - Child Unit ID (select parent) ← parent's Unit ID
   - Unit Description ← parent's Unit Description
   - Location Description ← parent's Location Description
   - Material ← parent's Material
   - Asset Type ← parent's Asset Type
   - Unit ID ← auto-generated: `{ParentID}_C{timestamp}` (e.g. `HeirissonCOPRVW01A_C2505141423`)
7. Fill in:
   - **Condition Rating** — dropdown
   - **Inspection Notes** — free text
   - **Photos** — tap camera icons (take photos HERE, inside the child form)
   - Rename **Unit ID** to a proper ID if required
8. Tap **tick/save**

> **Photo note**: Always take photos from within the child's own form — not from the parent form before tapping +. Photos are stored in the `files/` subfolder with auto-generated filenames linked to each feature via the GPKG.

### Create a new standalone asset
1. Tap **pencil/edit mode** button
2. Tap **+** (new feature)
3. Draw polyline on map
4. Fill all fields manually

---

## 4. Returning Data to Desktop

1. Connect phone via USB
2. Copy the **entire project folder** from the device to desktop
   - Copy to: `C:\Users\Damia\Documents\Projects\coastal-asset-register\`
   - Replace `riverwall_assets.gpkg` and the `files/` folder
3. Open QGIS → **Project → Open** → `riverwall_assets.qgs`

> **Important**: Copy the whole folder, not just the GPKG. Photos are separate files in `files/` — if only the GPKG is copied, photo links will be broken.

---

## 5. Photo Reconciliation (pending)

QField auto-names photos as:
```
riverwall-assets_20260506233032331_image_0001.jpg
```

This format does not include the Unit ID in the filename. The link between photo and asset is maintained inside the GPKG (Photo_1/2/3 fields store the relative file path).

**To view which photo belongs to which asset**: open the attribute table in QGIS — the Photo_1 field shows the filename for each feature.

**Post-processing rename script** *(to be written)*: will rename photos to `{Unit_ID}_Photo1.jpg` format and update GPKG references automatically after each field session.

---

## 6. Schema Reference

| Field | Type | Widget | Notes |
|---|---|---|---|
| Unit ID | Text | Text Edit | Required. Auto-generated for children |
| Child Unit ID | Text | Value Relation | Links child to parent Unit ID |
| Unit Description | Text | Text Edit | Pre-filled from source |
| Location Description | Text | Text Edit | Pre-filled from source |
| Total Length (m) | Decimal | Text Edit | Pre-filled from shapefile |
| Material | Text | Text Edit | Free text — pre-filled, editable |
| Asset Type | Text | Value Map | Revetment, Wall, Gabion, Beach, Soft Measure, Bioengineering |
| Construction Year | Integer | Text Edit | Manual entry |
| Replacement Cost – Gross Value | Decimal | Text Edit | Desktop valuation |
| Condition Rating (1–5) | Integer | Value Map | Field collected |
| Fair Value Valuation | Decimal | Text Edit | Desktop valuation |
| Useful Life | Integer | Text Edit | Desktop valuation |
| Remaining Useful Life | Integer | Text Edit | Desktop valuation |
| Residual Value | Decimal | Text Edit | Desktop valuation |
| Depreciation Method / Rate | Text | Value Map | Straight Line, Diminishing Value |
| Depreciation Expense | Decimal | Text Edit | Desktop valuation |
| Accumulated Depreciation | Decimal | Text Edit | Desktop valuation |
| Date of Valuation | Date | Date picker | Auto-fills today |
| Photo 1 / 2 / 3 | Text | Attachment | Field collected |
| CoP Comments | Text | Text Edit | Pre-filled from source Comments |
| Inspection Notes | Text | Text Edit | Free text — field collected |
