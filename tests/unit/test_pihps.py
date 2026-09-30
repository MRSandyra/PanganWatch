from __future__ import annotations

from panganwatch.sources import pihps


def test_status_is_not_used_with_no_dummy_data():
    assert pihps.STATUS == "not_used"
    assert "not used" in pihps.REASON.lower()


def test_main_without_status_flag_does_not_touch_db(monkeypatch, capsys):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("skip_run should not be called without --status")

    monkeypatch.setattr(pihps, "skip_run", fail_if_called)

    exit_code = pihps.main([])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "not_used" in captured.out


def test_main_with_status_flag_records_skip(monkeypatch):
    calls = []
    monkeypatch.setattr(
        pihps, "skip_run", lambda run_id, source, reason: calls.append((source, reason))
    )

    exit_code = pihps.main(["--status"])

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0][0] == "PIHPS"
