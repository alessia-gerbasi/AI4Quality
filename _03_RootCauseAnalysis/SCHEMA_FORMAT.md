# Root Cause Analysis - Schema Format & Testing Guide

## Overview

Schemas are YAML files that define decision trees for diagnosing quality failures.
Each schema references patient/injection data + calculates derived variables, then traces through decisions to reach a diagnosis.

## File Structure

```
_03_RootCauseAnalysis/
  schemas/
    timing_schema.yaml                # Example: timing diagnosis
    [your_schema].yaml                # Add your own
  excel_loader.py                     # Load Excel data
  rule_engine.py                      # Evaluate schemas
  schema_to_mermaid.py                # Visualize as flowchart
  dashboard.py                        # Streamlit UI
  SCHEMA_FORMAT.md                    # This file
```

## Writing a Schema

### 1. Basic Structure

```yaml
name: "Schema Name"
description: "What this schema diagnoses"

variables:
  # Derived variables here

decisions:
  # Decision tree here

outcomes:
  # Diagnosis outcomes here
```

### 2. Variables Section

Define calculations and lookups from patient data.

**Column Reference**: Use `@column_name` to reference patient data columns
```yaml
variables:
  time_delta:
    calculation: "@acquisition_time - @injection_time"
    unit: "seconds"
```

**Boolean Logic**:
```yaml
variables:
  has_baseline:
    calculation: "@baseline_hu > 0"  # Returns True/False
```

**String Operations**:
```yaml
variables:
  access_label:
    calculation: "@access_type"  # Just copy a column value
```

**Lookup from Thresholds**:
```yaml
variables:
  expected_arterial_min:
    source: "roi_hu_timing_table"
    procedure: "@procedure_code"
    phase: "arteriosa"
    index: 0  # gets first value from [min_opt, max_opt, min_threshold, max_threshold]
```

### 3. Decisions Section

Decision nodes in the tree. Each has a question + condition. Use `if_true` and `if_false` to branch.

```yaml
decisions:
  root:
    question: "Is timing within window?"
    condition: "@time_delta >= 30 AND @time_delta <= 45"
    if_true: outcome_ok
    if_false: check_direction

  check_direction:
    question: "Too early or too late?"
    condition: "@time_delta < 30"
    if_true: outcome_early
    if_false: outcome_late
```

**Condition Syntax**:
- Comparison: `@var >= 30`, `@var == "femoral"`, `@var != "manual"`
- Boolean: `AND`, `OR`, `NOT`
- Examples:
  - `(@time_delta < 30) OR (@access_type == "arm")`
  - `(@has_baseline) AND (@baseline_hu > 0)`
  - `NOT (@bolus_tracking == "none")`

### 4. Outcomes Section

Terminal nodes with diagnosis label + clinician card. Labels are stored in database; cards are shown to clinicians.

```yaml
outcomes:
  outcome_ok:
    label: "timing_ok"  # Simple database label
    card:
      title: "✓ Title (emoji optional)"
      explanation: "Why this happened"
      impact: "What it means for quality"
      recommendations:
        - "Action 1"
        - "Action 2"
```

---

## Running the Dashboard

### Prerequisites

Install required packages:
```bash
pip install streamlit pandas pyyaml openpyxl
```

### Start Dashboard

```bash
cd /data/alessia.gerbasi/AI4Quality/_03_RootCauseAnalysis
streamlit run dashboard.py
```

Then open the browser URL shown (usually `http://localhost:8501`).

### First Run

1. Select schema from sidebar dropdown: `timing_schema`
2. Select a case from case dropdown
3. Left pane: See decision tree flowchart + decision trace
4. Right pane: See diagnosis label + clinician card + recommendations

---

## Refining Thresholds & Rules

### Update Thresholds

Thresholds are in `../config/common/ct_protocols.yaml` (project root: `config/common/ct_protocols.yaml`). They control what values trigger different diagnoses.

**Example: Change TACPEC arterial timing window**

Open `config/common/ct_protocols.yaml` and modify:
```yaml
procedures:
  TACPEC:
    phases:
      arteriosa:
        timing: [32, 42, 25, 50]  # Changed from [35, 40, 30, 45]
```

Format: `[min_optimal, max_optimal, min_acceptable_threshold, max_acceptable_threshold]`

After saving, re-run dashboard—it reloads the config automatically.

### Update Decision Logic

Modify `schemas/timing_schema.yaml` (or your schema file):

**To change a condition threshold**:
```yaml
# Before
condition: "@time_delta >= 30 AND @time_delta <= 45"

# After: tighter window
condition: "@time_delta >= 32 AND @time_delta <= 42"
```

**To add a new decision branch based on access type**:
```yaml
decisions:
  root:
    question: "What access type?"
    condition: "@access_type == 'femoral'"
    if_true: evaluate_femoral
    if_false: evaluate_arm

  evaluate_femoral:
    question: "Femoral: within 35-40 sec?"
    condition: "@time_delta >= 35 AND @time_delta <= 40"
    if_true: outcome_ok
    if_false: outcome_not_ok

  evaluate_arm:
    question: "Arm: within 40-45 sec?"
    condition: "@time_delta >= 40 AND @time_delta <= 45"
    if_true: outcome_ok
    if_false: outcome_not_ok
```

**To add a new outcome card**:
```yaml
outcomes:
  outcome_not_ok:
    label: "timing_outside_window"
    card:
      title: "⚠ Timing outside acceptable window"
      explanation: "Timing does not match protocol for this access type"
      impact: "Quality may be compromised"
      recommendations:
        - "Review bolus arrival time"
```

After editing, save and re-run the dashboard—the flowchart will update automatically.

---

## Testing a Schema

### Manual Test (Python)

Test a single patient case without the dashboard:

```python
from rule_engine import RuleEvaluator
from excel_loader import ExcelLoader

# Load Excel
loader = ExcelLoader('/data/alessia.gerbasi/DATA/CDI_NEXO_072026/0_files/Injection History Anonymized.xlsx')
case = loader.get_case('PATIENT_ID_123')  # Use actual patient ID

# Evaluate with schema
evaluator = RuleEvaluator(
    'schemas/timing_schema.yaml',
  '../config/common/ct_protocols.yaml'
)
result = evaluator.evaluate(case)

# Check results
print(f"Diagnosis Label: {result['diagnosis_label']}")
print(f"Decision Path:")
for step in result['decision_path']:
    print(f"  {step['node']}: {step['question']} → {step['result']}")
print(f"Card Title: {result['card']['title']}")
print(f"Recommendations: {result['card']['recommendations']}")
```

### Visual Test (Dashboard)

1. Run `streamlit run dashboard.py`
2. Select the schema you want to test
3. Select a patient case
4. Check the flowchart: is the highlighted path correct?
5. Check the diagnosis card: does it match your expectation?

### Common Issues

**"Column not found" Error**
→ Your Excel file has different column names than the schema expects. Either:
   - Rename columns in Excel to match `@column_name` references
   - Edit schema to use actual column names
   - Check available columns: `loader.df.columns`

**Condition always True/False**
→ Check syntax. Example:
   - ✓ Correct: `@time_delta >= 30` (numeric comparison)
   - ✗ Wrong: `@time_delta >= '30'` (comparing number to string)
   - ✓ Correct: `@access_type == 'femoral'` (string comparison)
   - ✗ Wrong: `@access_type == femoral` (missing quotes)

**Mermaid diagram doesn't match logic**
→ The diagram is auto-generated from the YAML. Check:
   - Decision node names are used in `if_true`/`if_false` branches
   - All outcome names match outcome definitions
   - No typos in node IDs

**Variable calculation fails**
→ Check variable definition:
   - Column exists in Excel
   - Math operations are valid (can't subtract strings)
   - Use parentheses for complex expressions: `(@a + @b) / @c`

---

## Excel Column Mapping

The schemas expect specific column names in Excel. If your file uses different names, either:

1. **Rename columns in Excel** to match the expected names, OR
2. **Edit schema** to use your actual column names

**Expected columns** (and what they represent):

- `patient_id` — Case identifier (string)
- `procedure_code` — TAC* code (TACPEC, TACCOR, etc.)
- `acquisition_time` — Time when scan started, in seconds from injection
- `injection_time` — Time when bolus injected (usually 0)
- `access_type` — "femoral" or "arm" (or other values your data has)
- `bolus_tracking` — "automatic", "manual", "none" (optional)
- `baseline_hu` — Baseline HU before contrast (optional)

**To find actual column names**:
```python
from excel_loader import ExcelLoader
loader = ExcelLoader('/path/to/Injection History.xlsx')
df = loader.load()
print(df.columns.tolist())  # See all column names
print(df.head(2))  # See first 2 rows
```

Then update schema `@column_name` references to match.

---

## Tips for Refinement

1. **Start simple**: Begin with 1 procedure, 1-2 decision branches
2. **Trace manually**: Pick 1 patient case from Excel, manually trace through the schema logic, verify it matches your clinical reasoning
3. **Use dashboard**: Visual flowchart helps spot logic errors quickly
4. **Iterate incrementally**: Change thresholds/conditions one at a time, test, repeat
5. **Document decisions**: Add comments in YAML if a threshold is based on specific clinical data

---

## Example: Adding a New Schema

1. **Create file**: `schemas/contrast_dose_schema.yaml`
2. **Define logic**: Design decision tree (what variables, conditions, outcomes?)
3. **Add to thresholds**: If needed, add new entries to `config/common/ct_protocols.yaml`
4. **Test**: Run dashboard, select the new schema, pick a case
5. **Refine**: Adjust thresholds/conditions based on results

---

## Advanced: Variable Calculations

### Math Operations

```yaml
variables:
  time_to_peak:
    calculation: "@acquisition_time - @injection_time + 15"
  ratio:
    calculation: "@arterial_hu / @venous_hu"
```

### String Comparisons

```yaml
variables:
  is_femoral:
    calculation: "@access_type == 'femoral'"  # Returns True/False
```

### Conditional Logic (If-Then-Else)

Not directly supported in variable calculation. Use decision nodes instead:
```yaml
decisions:
  check_access:
    question: "Femoral access?"
    condition: "@access_type == 'femoral'"
    if_true: outcome_femoral
    if_false: outcome_non_femoral
```

---

## Viewing Generated Flowcharts

Flowcharts are generated on-the-fly by the dashboard using Mermaid syntax. To save one as an image:

1. Run dashboard
2. Right-click on the flowchart
3. Select "Save image as..."

Or use the `schema_to_mermaid.py` directly:

```python
from schema_to_mermaid import SchemaMermaidConverter

converter = SchemaMermaidConverter('schemas/timing_schema.yaml')
converter.save_mermaid_md('schemas/timing_flowchart.md')
# Now open timing_flowchart.md in VS Code to see the diagram
```
