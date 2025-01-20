from main import get_work_days_between_dates


def test_working_days():
    start_date = "2025-01-06"
    end_date = "2025-01-10"
    assert get_work_days_between_dates(start_date, end_date) == 5

    start_date = "2025-01-20"
    end_date = "2025-01-24"
    assert get_work_days_between_dates(start_date, end_date) == 4
