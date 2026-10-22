
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

import yaml


# --------------------------------------------------
# Load configuration from openapi.yaml
# --------------------------------------------------

OPENAPI_FILE = (
    Path(__file__).resolve().parent.parent / "openapi.yaml"
)


def load_config():
    """Load analyzer rules from the OpenAPI specification."""

    if not OPENAPI_FILE.is_file():
        raise FileNotFoundError(
            f"OpenAPI specification not found: {OPENAPI_FILE}"
        )

    with OPENAPI_FILE.open("r", encoding="utf-8") as file:
        spec = yaml.safe_load(file)

    try:
        schemas = spec["components"]["schemas"]

        result_schema = schemas["AnalysisResult"]
        result_properties = result_schema["properties"]

        errors_schema = result_properties["errors_by_service"]
        errors_properties = errors_schema["properties"]

        primary_schema = errors_properties["primary"]
        primary_properties = primary_schema["properties"]
        primary_required = primary_schema.get("required", [])

    except (KeyError, TypeError) as exc:
        raise ValueError(
            "openapi.yaml is missing the expected "
            "AnalysisResult/errors_by_service/primary schema."
        ) from exc

    # The YAML defines the primary services.
    primary_services = list(primary_properties.keys())

    if not primary_services:
        raise ValueError(
            "At least one primary service must be defined in openapi.yaml."
        )

    if set(primary_required) != set(primary_services):
        raise ValueError(
            "Every primary service property must be listed "
            "in the primary schema's required field."
        )

    if primary_schema.get("additionalProperties") is not False:
        raise ValueError(
            "The primary schema must set additionalProperties: false."
        )

    # Read the valid log levels from an optional vendor extension.
    # If it is absent, use the default levels below.
    valid_levels = spec.get("x-log-analyzer", {}).get(
        "validLevels",
        [
            "ERROR",
            "INFO",
            "WARN",
            "WARNING",
            "DEBUG",
            "CRITICAL",
            "FATAL",
            "TRACE",
        ],
    )

    if not isinstance(valid_levels, list) or not all(
        isinstance(level, str) and level.strip()
        for level in valid_levels
    ):
        raise ValueError(
            "x-log-analyzer.validLevels must be a list of strings."
        )

    return (
        primary_services,
        {level.strip().upper() for level in valid_levels},
    )


PRIMARY_SERVICES, VALID_LEVELS = load_config()


# --------------------------------------------------
# Log format
# YYYY-MM-DD HH:MM:SS LEVEL SERVICE MESSAGE
# --------------------------------------------------

LOG_PATTERN = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2})\s+"
    r"(\S+)\s+"
    r"(\S+)"
    r"(?:\s+(.*))?\s*$"
)


# --------------------------------------------------
# Parse a log line
# --------------------------------------------------

def parse_line(line: str):
    """Parse and validate a log line."""

    match = LOG_PATTERN.fullmatch(line)

    if not match:
        return None

    date, time, raw_level, service, message = match.groups()

    # Validate real calendar date and time.
    try:
        datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M:%S",
        )
    except ValueError:
        return None

    # Support ERROR, **ERROR**, error, etc.
    level = raw_level.strip("*").upper()

    if level not in VALID_LEVELS:
        return None

    return date, time, level, service, message or ""


# --------------------------------------------------
# Explain invalid lines
# --------------------------------------------------

def diagnose_line(line: str) -> str:
    """Return a diagnostic explaining why a line was skipped."""

    parts = line.strip().split()

    if not parts:
        return "Empty line"

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]):
        return (
            f"Missing or invalid date field "
            f"(got '{parts[0]}', expected 'YYYY-MM-DD')"
        )

    if len(parts) == 1:
        return "Missing fields: time, level, and service"

    if not re.fullmatch(r"\d{2}:\d{2}:\d{2}", parts[1]):
        return (
            f"Missing or invalid time field "
            f"(got '{parts[1]}', expected 'HH:MM:SS')"
        )

    try:
        datetime.strptime(
            f"{parts[0]} {parts[1]}",
            "%Y-%m-%d %H:%M:%S",
        )
    except ValueError as exc:
        return f"Invalid calendar date/time: {exc}"

    if len(parts) == 2:
        return "Missing fields: log level and service"

    level = parts[2].strip("*").upper()

    if level not in VALID_LEVELS:
        return (
            f"Invalid log level '{parts[2]}' "
            f"(valid: {', '.join(sorted(VALID_LEVELS))})"
        )

    if len(parts) == 3:
        return "Missing field: service name"

    if not LOG_PATTERN.fullmatch(line):
        return "Malformed line structure or unrecognized tokens"

    return "Unknown parsing failure"


# --------------------------------------------------
# Analyze all log lines
# --------------------------------------------------

def analyze_lines(lines: Iterable[str]) -> dict:
    """
    Count ERROR entries and group services.

    Primary services come from openapi.yaml.
    All other encountered services go into secondary.
    Blank lines are ignored.
    """

    error_counts = Counter()
    seen_services = set()

    lines_processed = 0
    lines_skipped = 0
    skipped_details = []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        parsed = parse_line(line)

        if parsed is None:
            lines_skipped += 1

            skipped_details.append({
                "line": line_number,
                "content": line.strip()[:120],
                "error": diagnose_line(line),
            })
            continue

        _, _, level, service, _ = parsed

        lines_processed += 1
        seen_services.add(service)

        if level == "ERROR":
            error_counts[service] += 1

    # Every configured primary service is included,
    # even when its error count is zero.
    primary_set = set(PRIMARY_SERVICES)

    primary = {
        service: error_counts[service]
        for service in sorted(PRIMARY_SERVICES)
    }

    # Secondary services are discovered dynamically.
    secondary = {
        service: error_counts[service]
        for service in sorted(seen_services - primary_set)
    }

    # Highest ERROR count wins.
    # Alphabetical order breaks ties.
    offenders = [
        service
        for service, count in error_counts.items()
        if count > 0
    ]

    top_offender = (
        min(
            offenders,
            key=lambda service: (
                -error_counts[service],
                service.casefold(),
                service,
            ),
        )
        if offenders
        else None
    )

    return {
        "lines_processed": lines_processed,
        "lines_skipped": lines_skipped,
        "errors_by_service": {
            "primary": primary,
            "secondary": secondary,
        },
        "top_offender": top_offender,
        "skipped_details": (
            skipped_details if skipped_details else None
        ),
    }