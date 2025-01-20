import argparse

import numpy as np
import requests
from business import calendar
from prettytable import PrettyTable
from requests.auth import HTTPBasicAuth

from company_holidays import get_company_holidays
from settings import Settings

PTS_KEY = "customfield_10026"

settings = Settings()

headers = {"Accept": "application/json"}
auth = HTTPBasicAuth(settings.USERNAME, settings.API_TOKEN)

product_status = [
    "Ready for Product Acceptance",
    "Selected for Engineering",
]

dev_status = [
    "In Progress",
    # "In Review",
    "In QA",
    "Blocked",
    "Ready for Demo Environment",
    "Ready for Deploy",
    "In Staging",
    "Ready for QA deploy",
]

start_status = [
    "Product Scoping",
    # "In Progress",
]

done_status = [
    "Done",
    "In Review",
]

cal = calendar.Calendar(holidays=get_company_holidays())

cycle_time = {}
cycle_time_extras = {}


# working days between, include start
def get_work_days_between_dates(start_date: str, end_date: str) -> int:
    return cal.business_days_between(start_date, end_date) + 1


def find_first_start_date(status_change_items) -> str:
    for item in status_change_items:
        if item.get("toString") in dev_status:
            return item.get("created")
    return None


def find_last_end_date(status_change_items) -> str:
    for item in reversed(status_change_items):
        if item.get("toString") in done_status:
            return item.get("created")
    return status_change_items[0].get("created")


def process_tickets(tickets):
    table = PrettyTable()
    table.field_names = ["Ticket", "Summary", "From", "To", "Pts", "Days"]

    for ticket in tickets:
        ticket_changelog = get_ticket_changelog(ticket)
        tocket_changelog_values = ticket_changelog.get("values", [])

        status_change_items = [
            {"created": value.get("created"), **item}
            for value in tocket_changelog_values
            for item in value.get("items")
            if item.get("field") == "status"
        ]

        start_date = find_first_start_date(status_change_items)
        end_date = find_last_end_date(status_change_items)
        if not start_date or not end_date:
            print(f"Missing start date or end date for {ticket.get('key')}")
            continue

        days = get_work_days_between_dates(start_date=start_date, end_date=end_date)
        pts = ticket.get("fields").get(PTS_KEY)
        if days is None:
            print(
                f"{ticket.get('key')} - {ticket.get('fields').get('summary')} - {days}"
            )

        if pts is None:
            pts = 0

        cycle_time.setdefault(int(pts), [])
        cycle_time[pts].append(
            {"key": ticket.get("key"), "pts": int(pts), "days": days}
        )

        table.add_row(
            [
                ticket.get("key"),
                ticket.get("fields").get("summary"),
                start_date,
                end_date,
                int(pts),
                days,
            ]
        )

    print(table)


def calculate_dev_days(status_change_items, idx, item) -> int:
    last_status_date = status_change_items[idx - 1].get("created")
    current_status_date = item.get("created")
    dev_days = get_work_days_between_dates(last_status_date, current_status_date)
    return dev_days


def get_ticket_changelog(ticket):
    changelog_response = requests.get(
        f"{ticket.get('self')}/changelog", headers=headers, auth=auth
    )
    ticket_data = changelog_response.json()
    return ticket_data


def get_ticket_list(team: str):
    url = f"{settings.BASE_URL}/rest/api/3/search"

    query = {
        "jql": f'project = "AX" and type=story and summary !~ spike and status in (done, "in production") and "Start date[Date]" is not EMPTY and "Done Timestamp[Time stamp]" > startOfMonth(-3) and "Done Timestamp[Time stamp]" < startOfMonth() and "Team[Dropdown]" = "{team}" ORDER BY cf[10096], assignee, cf[10054] DESC',
    }

    response = requests.get(url, headers=headers, auth=auth, params=query)
    ticket_repsone = response.json()
    tickets = ticket_repsone.get("issues")
    return tickets


def build_cycle_time():
    table = PrettyTable()
    table.field_names = [
        "PTS",
        "Max",
        "Min",
        "Mean",
        "Median",
        "Std",
        "25th",
        "50th",
        "75th",
    ]
    for key, value in sorted(cycle_time.items(), key=lambda x: x[0]):
        days = [item.get("days") for item in value]

        table.add_row(
            [
                key,
                np.max(days),
                np.min(days),
                np.mean(days),
                np.median(days),
                np.std(days),
                np.percentile(days, 25),
                np.percentile(days, 50),
                np.percentile(days, 75),
            ]
        )

    print(table)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--team",
        type=str,
        required=False,
        choices=["Apptimus Prime", "Dusty Knights"],
        default="Apptimus Prime",
    )
    args = argparser.parse_args()

    tickets = get_ticket_list(team=args.team)
    process_tickets(tickets)
    build_cycle_time()
