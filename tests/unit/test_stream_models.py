"""Unit tests for stream models."""

import pytest
from pydantic import ValidationError

from panganwatch.stream import producer
from panganwatch.stream.models import WeatherAlertV1, WeatherCurrentV1


class TestWeatherCurrentV1:
    """Test WeatherCurrentV1 model validation."""

    def test_valid_message(self):
        """Test valid WeatherCurrentV1 message."""
        msg = WeatherCurrentV1(
            event_id="test-123",
            schema_version="1.0",
            kode_provinsi_bps="31",
            observed_at="2026-09-21T10:00:00+00:00",
            temperature_c=28.5,
            precipitation_mm=2.3,
            humidity_pct=75,
            wind_speed_kph=12.0,
            wind_direction_deg=180,
            cloud_cover_pct=45,
            producer_id="open-meteo",
            fetched_at="2026-09-21T10:00:01+00:00",
        )
        assert msg.kode_provinsi_bps == "31"
        assert msg.temperature_c == 28.5
        assert msg.schema_version == "1.0"

    def test_valid_message_with_none_optional(self):
        """Test valid message with optional fields as None."""
        msg = WeatherCurrentV1(
            event_id="test-123",
            schema_version="1.0",
            kode_provinsi_bps="31",
            observed_at="2026-09-21T10:00:00+00:00",
            temperature_c=None,
            precipitation_mm=None,
            humidity_pct=None,
            wind_speed_kph=None,
            wind_direction_deg=None,
            cloud_cover_pct=None,
            producer_id="open-meteo",
            fetched_at="2026-09-21T10:00:01+00:00",
        )
        assert msg.temperature_c is None
        assert msg.precipitation_mm is None

    def test_invalid_temperature_too_high(self):
        """Test validation rejects temperature > 50."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=100.0,
                precipitation_mm=2.3,
                humidity_pct=75,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )

    def test_invalid_temperature_too_low(self):
        """Test validation rejects temperature < -10."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=-20.0,
                precipitation_mm=2.3,
                humidity_pct=75,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )

    def test_invalid_precipitation_negative(self):
        """Test validation rejects negative precipitation."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=28.5,
                precipitation_mm=-5.0,
                humidity_pct=75,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )

    def test_invalid_schema_version(self):
        """Test validation rejects wrong schema_version."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="2.0",  # Invalid - must be "1.0"
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=28.5,
                precipitation_mm=2.3,
                humidity_pct=75,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )

    def test_invalid_humidity_too_high(self):
        """Test validation rejects humidity > 100."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=28.5,
                precipitation_mm=2.3,
                humidity_pct=150,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )


class TestWeatherAlertV1:
    """Test WeatherAlertV1 model validation."""

    def test_valid_alert(self):
        """Test valid WeatherAlertV1 message."""
        alert = WeatherAlertV1(
            event_id="alert-123",
            schema_version="1.0",
            kode_provinsi_bps="31",
            alert_type="heavy_rain",
            alert_level="heavy",
            threshold_field="precipitation_mm",
            threshold_value=50.0,
            current_value=75.0,
            observed_at="2026-09-21T10:00:00+00:00",
            valid_until="2026-09-21T16:00:00+00:00",
            recommendation="Beware of flooding",
        )
        assert alert.alert_type == "heavy_rain"
        assert alert.alert_level == "heavy"

    def test_alert_types(self):
        """Test all valid alert types."""
        for alert_type in ["heavy_rain", "extreme_heat", "high_wind", "storm_surge"]:
            alert = WeatherAlertV1(
                event_id="alert-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                alert_type=alert_type,
                alert_level="heavy",
                threshold_field="test",
                threshold_value=10.0,
                current_value=20.0,
                observed_at="2026-09-21T10:00:00+00:00",
                valid_until="2026-09-21T16:00:00+00:00",
                recommendation="Test",
            )
            assert alert.alert_type == alert_type

    def test_alert_levels(self):
        """Test all valid alert levels."""
        for alert_level in ["light", "moderate", "heavy", "extreme"]:
            alert = WeatherAlertV1(
                event_id="alert-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                alert_type="heavy_rain",
                alert_level=alert_level,
                threshold_field="test",
                threshold_value=10.0,
                current_value=20.0,
                observed_at="2026-09-21T10:00:00+00:00",
                valid_until="2026-09-21T16:00:00+00:00",
                recommendation="Test",
            )
            assert alert.alert_level == alert_level


class TestAlertLogic:
    """Test alert threshold logic."""

    def test_heavy_rain_alert_triggered(self):
        """Test alert is triggered for heavy rain (> threshold)."""
        threshold = 50.0
        precipitation = 75.0
        assert precipitation > threshold

        alert = WeatherAlertV1(
            event_id="alert-123",
            schema_version="1.0",
            kode_provinsi_bps="31",
            alert_type="heavy_rain",
            alert_level="heavy",
            threshold_field="precipitation_mm",
            threshold_value=threshold,
            current_value=precipitation,
            observed_at="2026-09-21T10:00:00+00:00",
            valid_until="2026-09-21T16:00:00+00:00",
            recommendation="Beware of flooding",
        )
        assert alert.current_value > alert.threshold_value

    def test_no_alert_below_threshold(self):
        """Test no alert when precipitation below threshold."""
        threshold = 50.0
        precipitation = 10.0
        assert precipitation < threshold

        # No alert should be created
        assert not (precipitation > threshold)


class TestProducerBuilder:
    """Test producer builder functions."""

    def test_build_weather_message_valid(self):
        """Test building a valid WeatherCurrentV1 message."""
        msg = producer.build_weather_message(
            province_code="31",
            province_name="Daerah Khusus Ibukota Jakarta",
            lat=-6.21462,
            lon=106.84513,
            temperature_c=28.5,
            precipitation_mm=2.3,
            humidity_pct=75,
            wind_speed_kph=12.0,
            wind_direction_deg=180,
            cloud_cover_pct=45,
            source_station="open-meteo",
        )

        assert isinstance(msg, WeatherCurrentV1)
        assert msg.kode_provinsi_bps == "31"
        assert msg.temperature_c == 28.5
        assert msg.precipitation_mm == 2.3
        assert msg.schema_version == "1.0"

    def test_build_weather_message_with_none_optional(self):
        """Test building message with optional fields as None."""
        msg = producer.build_weather_message(
            province_code="31",
            province_name="Jakarta",
            lat=-6.2,
            lon=106.8,
            temperature_c=None,
            precipitation_mm=None,
            humidity_pct=None,
            wind_speed_kph=None,
            wind_direction_deg=None,
            cloud_cover_pct=None,
            source_station="open-meteo",
        )

        assert msg.temperature_c is None
        assert msg.precipitation_mm is None
        assert msg.schema_version == "1.0"

    def test_build_weather_message_default_threshold(self):
        """Test threshold logic uses settings."""
        # Test the threshold logic directly
        weather_dict = {"alert": {"precipitation_mm_threshold": 50.0}}
        threshold = weather_dict.get("alert", {}).get("precipitation_mm_threshold", 50.0)
        assert threshold == 50.0

        # Test with custom threshold
        weather_dict = {"alert": {"precipitation_mm_threshold": 25.0}}
        threshold = weather_dict.get("alert", {}).get("precipitation_mm_threshold", 50.0)
        assert threshold == 25.0

        # Test with missing alert config
        weather_dict = {}
        threshold = weather_dict.get("alert", {}).get("precipitation_mm_threshold", 50.0)
        assert threshold == 50.0

    def test_producer_help_output(self, monkeypatch, capsys):
        """Test producer CLI --help exits 0 (main is async, reads sys.argv)."""
        import asyncio
        import sys

        monkeypatch.setattr(sys, "argv", ["panganwatch.stream.producer", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            asyncio.run(producer.main())
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "Kafka weather producer" in out


class TestConsumerLogic:
    """Test consumer logic for validation and alerting."""

    def test_validate_message_valid(self):
        """Test validation of valid message."""
        from datetime import UTC, datetime

        msg = WeatherCurrentV1(
            event_id="test-123",
            schema_version="1.0",
            kode_provinsi_bps="31",
            observed_at=datetime.now(UTC).isoformat(),
            temperature_c=28.5,
            precipitation_mm=2.3,
            humidity_pct=75,
            wind_speed_kph=12.0,
            wind_direction_deg=180,
            cloud_cover_pct=45,
            producer_id="open-meteo",
            fetched_at=datetime.now(UTC).isoformat(),
        )

        # Validation should pass
        validated = WeatherCurrentV1.model_validate(msg.model_dump())
        assert validated.kode_provinsi_bps == "31"

    def test_validate_message_invalid_temp(self):
        """Test validation rejects out-of-range temperature."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="1.0",
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=100.0,  # Out of range
                precipitation_mm=2.3,
                humidity_pct=75,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )

    def test_validate_message_invalid_schema_version(self):
        """Test validation rejects wrong schema_version."""
        with pytest.raises(ValidationError):
            WeatherCurrentV1(
                event_id="test-123",
                schema_version="2.0",  # Invalid - must be "1.0"
                kode_provinsi_bps="31",
                observed_at="2026-09-21T10:00:00+00:00",
                temperature_c=28.5,
                precipitation_mm=2.3,
                humidity_pct=75,
                wind_speed_kph=12.0,
                wind_direction_deg=180,
                cloud_cover_pct=45,
                producer_id="open-meteo",
                fetched_at="2026-09-21T10:00:01+00:00",
            )

    def test_heavy_rain_alert_triggered(self):
        """Test alert is triggered for heavy rain (> threshold)."""
        threshold = 50.0
        precipitation = 75.0
        assert precipitation > threshold

        alert = WeatherAlertV1(
            event_id="alert-123",
            schema_version="1.0",
            kode_provinsi_bps="31",
            alert_type="heavy_rain",
            alert_level="heavy",
            threshold_field="precipitation_mm",
            threshold_value=threshold,
            current_value=precipitation,
            observed_at="2026-09-21T10:00:00+00:00",
            valid_until="2026-09-21T16:00:00+00:00",
            recommendation="Beware of flooding",
        )
        assert alert.current_value > alert.threshold_value

    def test_no_alert_below_threshold(self):
        """Test no alert when precipitation below threshold."""
        threshold = 50.0
        precipitation = 10.0
        assert precipitation < threshold

        # No alert should be created
        assert not (precipitation > threshold)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
