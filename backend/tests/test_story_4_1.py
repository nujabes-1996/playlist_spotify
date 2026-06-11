import pytest
from unittest.mock import patch, MagicMock

from scheduler import bootstrap_user_job


# Story 10.4: the single global `sync_job` became one job per user (`sync_{user_id}`).
# These tests preserve 4.1's job-persistence/idempotency intent against bootstrap_user_job.


def test_bootstrap_with_cron_expr_registers_job():
    with patch("scheduler.scheduler.add_job") as mock_add_job, \
         patch("scheduler.scheduler.get_job", return_value=None):
        bootstrap_user_job(1, "0 * * * *")

    mock_add_job.assert_called_once()
    kwargs = mock_add_job.call_args.kwargs
    assert kwargs["id"] == "sync_1"
    assert kwargs["args"] == [1]
    assert kwargs["replace_existing"] is True
    assert kwargs["max_instances"] == 1
    assert kwargs["coalesce"] is True


def test_bootstrap_without_cron_expr_does_not_register_job():
    with patch("scheduler.scheduler.add_job") as mock_add_job, \
         patch("scheduler.scheduler.get_job", return_value=None):
        bootstrap_user_job(1, None)

    mock_add_job.assert_not_called()


def test_bootstrap_without_cron_expr_removes_existing_job():
    mock_job = MagicMock()
    with patch("scheduler.scheduler.get_job", return_value=mock_job), \
         patch("scheduler.scheduler.remove_job") as mock_remove:
        bootstrap_user_job(1, None)

    mock_remove.assert_called_once_with("sync_1")


def test_bootstrap_without_cron_expr_no_existing_job_does_nothing():
    with patch("scheduler.scheduler.get_job", return_value=None), \
         patch("scheduler.scheduler.remove_job") as mock_remove:
        bootstrap_user_job(1, None)

    mock_remove.assert_not_called()


def test_bootstrap_uses_crontab_trigger():
    from apscheduler.triggers.cron import CronTrigger
    with patch("scheduler.scheduler.add_job") as mock_add_job, \
         patch("scheduler.scheduler.get_job", return_value=None):
        bootstrap_user_job(1, "0 */6 * * *")

    args = mock_add_job.call_args.args
    trigger = args[1]
    assert isinstance(trigger, CronTrigger)
