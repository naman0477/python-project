"""CampusLibrary reports and dashboard."""

from services import (
    dashboard,
    category_report,
    overdue_transactions,
    transaction_history
)
from database import load_records


def print_dashboard():
    print("\n=== CAMPUSLIBRARY DASHBOARD ===")

    for label, value in dashboard().items():
        print(f"{label.replace('_', ' ').title():22}: {value}")


def print_books():
    books = load_records("books")

    print("\nID | TITLE | AUTHOR | CATEGORY | AVAILABLE / TOTAL")
    print("-" * 78)

    for b in books:
        print(
            f'{b["id"]} | {b["title"]} | {b["author"]} | '
            f'{b["category"]} | {b["available"]}/{b["quantity"]}'
        )

    if not books:
        print("No books found.")


def print_members():
    members = load_records("members")

    print("\nID | NAME | EMAIL | PHONE")
    print("-" * 65)

    for m in members:
        print(
            f'{m["id"]} | {m["name"]} | '
            f'{m["email"]} | {m.get("phone", "")}'
        )

    if not members:
        print("No members registered.")


def print_categories():
    print("\n=== CATEGORY REPORT ===")

    report = category_report()

    if not report:
        print("No category data available.")

    for category, count in report.items():
        print(f"{category:20} {count}")


def print_overdue():
    print("\n=== OVERDUE LOANS ===")

    books = {
        b["id"]: b["title"]
        for b in load_records("books")
    }

    members = {
        m["id"]: m["name"]
        for m in load_records("members")
    }

    rows = overdue_transactions()

    if not rows:
        print("No overdue books. Great!")

    for tx in rows:
        print(
            f'Loan #{tx["id"]}: '
            f'{books.get(tx["book_id"], "Unknown book")} | '
            f'{members.get(tx["member_id"], "Unknown member")} | '
            f'Due {tx["due_date"]} | '
            f'Estimated fine Rs. {tx["estimated_fine"]:.2f}'
        )


def print_history():
    print("\n=== TRANSACTION HISTORY ===")

    rows = transaction_history()

    if not rows:
        print("No transactions yet.")

    for tx in rows:
        print(
            f'#{tx["id"]} Book {tx["book_id"]} / '
            f'Member {tx["member_id"]} | {tx["status"]} | '
            f'Issued {tx["issue_date"]} | '
            f'Returned {tx["return_date"] or "-"} | '
            f'Fine Rs. {tx.get("fine", 0):.2f}'
        )