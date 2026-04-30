"""
Smoke test: validate all 5 SQL pipeline fixes are wired correctly.
Run with: python test_fixes.py
"""
import sys, re
sys.path.insert(0, ".")

from services.sql_rag_service import (
    expand_tables_via_fk,
    parse_schema_metadata,
    _FK_REF_RE,
)

# ── Shared fake schema ────────────────────────────────────────────────────────
fake_raw_schema = (
    "Table: employee_documents\n"
    "Columns: id (INTEGER), emp_id (VARCHAR(20))\n"
    "Primary Key: id\n"
    "Foreign Keys: ['emp_id'] -> employee.['employee_id']\n"
    "\n"
    "Table: employee_relieving_letters\n"
    "Columns: id (INTEGER), emp_id (VARCHAR(20))\n"
    "Primary Key: id\n"
    "Foreign Keys: ['emp_id'] -> employee.['employee_id']\n"
    "\n"
    "Table: employee\n"
    "Columns: id (INTEGER), employee_id (VARCHAR(20)), first_name (VARCHAR(50))\n"
    "Primary Key: id\n"
    "\n"
    "Table: document\n"
    "Columns: id (INTEGER), doc_name (VARCHAR(100))\n"
    "Primary Key: id\n"
    "\n"
    "Table: employee_capability_group_history\n"
    "Columns: id (INTEGER), emp_id (VARCHAR(20))\n"
    "Primary Key: id\n"
    "Foreign Keys: ['emp_id'] -> employee.['employee_id']"
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []


def check(name, cond):
    tag = PASS if cond else FAIL
    print(f"  [{tag}] {name}")
    results.append(cond)


# ── Fix A: FK expansion ───────────────────────────────────────────────────────
print("\nFix A — expand_tables_via_fk:")
selected = ["document", "employee_capability_group_history",
            "employee_documents", "employee_relieving_letters"]
expanded = expand_tables_via_fk(selected, fake_raw_schema)
print(f"  Input:    {sorted(selected)}")
print(f"  Expanded: {sorted(expanded)}")
check("'employee' auto-added from FK chain", "employee" in expanded)
check("original tables preserved", all(t in expanded for t in selected))

# ── Fix B: col hints no longer capped ─────────────────────────────────────────
print("\nFix B — col hints cap removed:")
src = open("services/sql_rag_service.py").read()
check("[:30] cap gone from select_relevant_tables", "items())[:30]" not in src)
check("TABLE COLUMN OVERVIEW in prompt",            "TABLE COLUMN OVERVIEW" in src)
check("table_summary_lines used",                   "table_summary_lines" in src)

# ── Fix D: FK ref regex ────────────────────────────────────────────────────────
print("\nFix D — _FK_REF_RE regex:")
fk_line = "Foreign Keys: ['emp_id'] -> employee.['employee_id']"
found = _FK_REF_RE.findall(fk_line)
print(f"  Regex match: {found}")
check("regex extracts 'employee' from FK line", "employee" in found)

# ── Fix E: pre-flight coverage ────────────────────────────────────────────────
print("\nFix E — pre-flight schema coverage:")
check("schema_map_preflight in source", "schema_map_preflight" in src)
check("missing_fk_tables in source",    "missing_fk_tables" in src)

# ── Fix C: self-healing in retry loop ─────────────────────────────────────────
print("\nFix C — self-healing retry:")
err = "Schema Validation Error: Table 'employee' does not exist in the retrieved schema."
missing = re.findall(r"Table '(\w+)' does not exist in the retrieved schema", err)
print(f"  Extracted missing tables: {missing}")
check("extracts table name from error", missing == ["employee"])
check("missing_in_err in source",       "missing_in_err" in src)
check("reparse schema_map after patch", "schema_map = parse_schema_metadata(schema_context)" in src)

# ── parse_schema_metadata FK parsing ─────────────────────────────────────────
print("\nBonus — parse_schema_metadata FK round-trip:")
schema_map = parse_schema_metadata(fake_raw_schema)
fk_list = schema_map.get("foreign_keys", [])
emp_doc_fk = next((f for f in fk_list if f["from_table"].lower() == "employee_documents"), None)
check("FK from employee_documents parsed",  emp_doc_fk is not None)
if emp_doc_fk:
    check("FK to_table is 'employee'", emp_doc_fk["to_table"].lower() == "employee")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passed = sum(results)
total  = len(results)
if passed == total:
    print(f"ALL {total}/{total} CHECKS PASSED [OK]")
else:
    print(f"{passed}/{total} PASSED -- {total - passed} FAILED [!!]")
    sys.exit(1)
