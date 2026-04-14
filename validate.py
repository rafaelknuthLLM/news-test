#!/usr/bin/env python3
"""
AI-Cake Data Validator
Checks fetch output against schema.json before analysis.
Reports data quality issues so the reasoning layer knows what to trust.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.json"
OUTPUT_DIR = Path(__file__).parent / "output"


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_type(value, expected_type, field_name):
    """Check if a value matches the expected type."""
    issues = []
    if value is None:
        return issues  # None handled separately via nullable check

    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "object": dict,
        "array": list,
    }
    expected = type_map.get(expected_type)
    if expected and not isinstance(value, expected):
        issues.append(f"{field_name}: expected {expected_type}, got {type(value).__name__}")
    return issues


def validate_item(item, schema_def, source_name, index):
    """Validate a single data item against its schema definition."""
    issues = []
    prefix = f"{source_name}[{index}]"

    # Check required fields
    for field in schema_def.get("required_fields", []):
        if field not in item:
            issues.append(f"{prefix}: missing required field '{field}'")

    # Check expected fields
    for field, spec in schema_def.get("expected_fields", {}).items():
        if field not in item:
            continue

        value = item[field]

        # Handle nullable
        if value is None and spec.get("nullable"):
            continue
        if value is None and not spec.get("nullable"):
            issues.append(f"{prefix}.{field}: is null but not nullable")
            continue

        # Type check
        issues.extend(validate_type(value, spec.get("type", "string"), f"{prefix}.{field}"))

        # Min check
        if "min" in spec and isinstance(value, (int, float)):
            if value < spec["min"]:
                issues.append(f"{prefix}.{field}: value {value} below min {spec['min']}")

        # Valid values check
        if "valid_values" in spec and value not in spec["valid_values"]:
            issues.append(f"{prefix}.{field}: '{value}' not in valid values {spec['valid_values']}")

        # Nested object
        if spec.get("type") == "object" and isinstance(value, dict) and "fields" in spec:
            for subfield, subspec in spec["fields"].items():
                if subfield in value:
                    issues.extend(validate_type(
                        value[subfield], subspec.get("type", "string"),
                        f"{prefix}.{field}.{subfield}"
                    ))

        # Nested array
        if spec.get("type") == "array" and isinstance(value, list) and "item_fields" in spec:
            for j, arr_item in enumerate(value):
                for subfield, subspec in spec["item_fields"].items():
                    if subfield in arr_item:
                        issues.extend(validate_type(
                            arr_item[subfield], subspec.get("type", "string"),
                            f"{prefix}.{field}[{j}].{subfield}"
                        ))

    # Check for error field (indicates fetch failure)
    if "error" in item:
        issues.append(f"{prefix}: fetch error -- {item['error']}")

    return issues


def validate_section(data, section_name, schema_def):
    """Validate all items in a data section."""
    items = data.get(section_name, [])
    issues = []
    for i, item in enumerate(items):
        issues.extend(validate_item(item, schema_def, section_name, i))

    # Check for empty section
    if not items:
        issues.append(f"{section_name}: section is empty (0 items)")

    return issues, len(items)


def validate_completeness(data, expected_counts):
    """Check if we got a reasonable number of items from each source."""
    issues = []
    for section, (min_expected, description) in expected_counts.items():
        items = data.get(section, [])
        actual = len(items)
        if actual < min_expected:
            issues.append(
                f"COMPLETENESS: {section} has {actual} items, expected at least {min_expected} ({description})"
            )
        # Check for high error rate
        errors = sum(1 for item in items if "error" in item)
        if errors > 0:
            pct = (errors / max(actual, 1)) * 100
            issues.append(f"COMPLETENESS: {section} has {errors}/{actual} errors ({pct:.0f}%)")
    return issues


def main():
    schema = load_schema()

    # Find latest data files
    api_files = sorted(OUTPUT_DIR.glob("ai_cake_apis_*.json"), reverse=True)
    feed_files = sorted(OUTPUT_DIR.glob("ai_cake_feed_*.json"), reverse=True)

    if not api_files and not feed_files:
        print("No data files found in output/. Run fetch scripts first.", file=sys.stderr)
        return 1

    all_issues = []
    total_items = 0

    # Validate API data
    if api_files:
        api_file = api_files[0]
        print(f"Validating: {api_file.name}")
        with open(api_file, encoding="utf-8") as f:
            api_data = json.load(f)

        section_schemas = {
            "pypi": "pypi_item",
            "npm": "npm_item",
            "docker": "docker_item",
            "github": "github_item",
            "huggingface": "huggingface_item",
            "edgar": "edgar_item",
            "openrouter": "openrouter_item",
        }

        for section, schema_key in section_schemas.items():
            issues, count = validate_section(api_data, section, schema[schema_key])
            all_issues.extend(issues)
            total_items += count
            status = "OK" if not issues else f"{len(issues)} issues"
            print(f"  {section:>15}: {count:>4} items -- {status}")

        # Completeness check
        completeness_issues = validate_completeness(api_data, {
            "pypi": (8, "10 packages configured"),
            "npm": (5, "6 packages configured"),
            "docker": (4, "5 images configured"),
            "github": (8, "10 repos configured"),
            "huggingface": (10, "20 models requested"),
            "edgar": (5, "8 companies configured"),
            "openrouter": (50, "expected 200+ models"),
        })
        all_issues.extend(completeness_issues)

    # Validate feed data
    if feed_files:
        feed_file = feed_files[0]
        print(f"Validating: {feed_file.name}")
        with open(feed_file, encoding="utf-8") as f:
            feed_data = json.load(f)

        items = feed_data.get("items", [])
        feed_issues = []
        for i, item in enumerate(items):
            feed_issues.extend(validate_item(item, schema["feed_item"], "feed", i))
        all_issues.extend(feed_issues)
        total_items += len(items)

        research = sum(1 for i in items if i.get("category") == "research")
        github = sum(1 for i in items if i.get("category") == "github")
        status = "OK" if not feed_issues else f"{len(feed_issues)} issues"
        print(f"  {'feeds':>15}: {len(items):>4} items ({research} research, {github} releases) -- {status}")

    # Summary
    print(f"\n  Total items validated: {total_items}")
    print(f"  Issues found: {len(all_issues)}")

    if all_issues:
        print("\n  Issues:")
        for issue in all_issues[:30]:
            print(f"    - {issue}")
        if len(all_issues) > 30:
            print(f"    ... and {len(all_issues) - 30} more")

    # Write validation report as JSON (for the reasoning layer to consume)
    report = {
        "validated_at": datetime.now().isoformat(),
        "total_items": total_items,
        "total_issues": len(all_issues),
        "issues": all_issues,
        "data_quality": "clean" if len(all_issues) == 0 else "has_issues",
    }
    report_file = OUTPUT_DIR / "validation_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Report: {report_file}")

    return 0 if len(all_issues) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
