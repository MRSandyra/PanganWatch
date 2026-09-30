"""Export JSON Schema for Kafka message contracts."""

import json
from pathlib import Path

from panganwatch.stream.models import WeatherAlertV1, WeatherCurrentV1

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Exporting Kafka contracts...")

    # Export WeatherCurrentV1
    current_schema = WeatherCurrentV1.model_json_schema()
    current_schema["title"] = "WeatherCurrentV1"
    current_path = CONTRACTS_DIR / "weather_current_v1.json"
    current_path.write_text(json.dumps(current_schema, indent=2))
    print(f"  → {current_path}")

    # Export WeatherAlertV1
    alert_schema = WeatherAlertV1.model_json_schema()
    alert_schema["title"] = "WeatherAlertV1"
    alert_path = CONTRACTS_DIR / "weather_alert_v1.json"
    alert_path.write_text(json.dumps(alert_schema, indent=2))
    print(f"  → {alert_path}")

    print("Contracts exported successfully!")


if __name__ == "__main__":
    main()
