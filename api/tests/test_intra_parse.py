"""Parsing of the 42 user payload: common-core cursus, projects, achievements."""

from __future__ import annotations

from types import SimpleNamespace

from app.intra import _parse_achievements, _parse_cursus, _parse_projects


def _user(**extra):
    return SimpleNamespace(model_extra=extra)


def test_parse_cursus_prefers_common_core():
    u = _user(
        cursus_users=[
            {"level": 3.0, "grade": "Pisciner", "cursus": {"slug": "c-piscine"}},
            {"level": 7.42, "grade": "Member", "cursus": {"slug": "42cursus"}},
        ]
    )
    assert _parse_cursus(u) == (7.42, "Member")


def test_parse_cursus_empty():
    assert _parse_cursus(_user()) == (None, None)


def test_parse_projects_common_core_only_current_first_then_recent():
    u = _user(
        cursus_users=[{"cursus_id": 21, "cursus": {"slug": "42cursus"}, "level": 7.0}],
        projects_users=[
            {"status": "finished", "final_mark": 125, "validated?": True, "cursus_ids": [21],
             "marked_at": "2025-01-01T00:00:00Z", "project": {"name": "libft"}},
            {"status": "in_progress", "cursus_ids": [21], "project": {"name": "minishell"}},
            {"status": "finished", "final_mark": 0, "validated?": False, "cursus_ids": [21],
             "marked_at": "2025-02-01T00:00:00Z", "project": {"name": "so_long"}},
            # Piscine project (cursus 9) must be excluded:
            {"status": "finished", "final_mark": 100, "validated?": True, "cursus_ids": [9],
             "marked_at": "2025-03-01T00:00:00Z", "project": {"name": "Exam Piscine"}},
        ],
    )
    projs = _parse_projects(u)
    assert [p.name for p in projs] == ["minishell", "so_long", "libft"]
    assert "Exam Piscine" not in [p.name for p in projs]
    libft = next(p for p in projs if p.name == "libft")
    assert libft.mark == 125 and libft.validated is True


def test_piscine_only_student_has_no_common_core_data():
    u = _user(
        cursus_users=[{"cursus_id": 9, "cursus": {"slug": "c-piscine"}, "level": 11.0}],
        projects_users=[{"status": "finished", "cursus_ids": [9], "project": {"name": "shell00"}}],
    )
    assert _parse_cursus(u) == (None, None)
    assert _parse_projects(u) == ()


def test_parse_achievements_dedup_and_names():
    u = _user(achievements=[{"name": "Welcome"}, {"name": "Welcome"}, {"name": "Rush 01"}, {}])
    assert _parse_achievements(u) == ("Welcome", "Rush 01")
