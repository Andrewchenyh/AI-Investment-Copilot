from pathlib import Path

from evals.store_results import get_eval_run, list_eval_runs, save_eval_run


def test_save_and_get_eval_run(tmp_path: Path) -> None:
    db_path = tmp_path / "eval_runs.sqlite3"
    payload = {
        "summary": {
            "total": 2,
            "passed": 1,
            "failed": 1,
            "pass_rate": 0.5,
        },
        "results": [
            {"id": "case_1", "passed": True},
            {"id": "case_2", "passed": False},
        ],
    }

    run_id = save_eval_run(payload, db_path=db_path)
    loaded = get_eval_run(run_id, db_path=db_path)

    assert loaded == payload


def test_list_eval_runs(tmp_path: Path) -> None:
    db_path = tmp_path / "eval_runs.sqlite3"
    payload = {
        "summary": {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "pass_rate": 1.0,
        },
        "results": [{"id": "case_1", "passed": True}],
    }

    save_eval_run(payload, db_path=db_path)

    runs = list_eval_runs(db_path=db_path)

    assert len(runs) == 1
    assert runs[0]["total"] == 1
    assert runs[0]["passed"] == 1
    assert runs[0]["failed"] == 0
    assert runs[0]["pass_rate"] == 1.0