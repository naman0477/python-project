"""CampusLibrary business logic."""

from datetime import date, timedelta
import logging

from database import load_records, save_records, next_id

LOAN_DAYS = 14
FINE_PER_DAY = 2.0


class LibraryError(Exception):
    pass


def _required(value, field):
    cleaned = str(value).strip()

    if not cleaned:
        raise LibraryError(f"{field} cannot be empty.")

    if len(cleaned) > 100:
        raise LibraryError(f"{field} must be under 100 characters.")

    return cleaned


def _positive_int(value, field):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise LibraryError(
            f"{field} must be a whole number."
        ) from exc

    if number < 1:
        raise LibraryError(f"{field} must be at least 1.")

    return number


def add_book(title, author, category, quantity):
    books = load_records("books")

    record = {
        "id": next_id(books),
        "title": _required(title, "Title"),
        "author": _required(author, "Author"),
        "category": _required(category, "Category"),
        "quantity": _positive_int(quantity, "Quantity")
    }

    record["available"] = record["quantity"]

    books.append(record)
    save_records("books", books)

    logging.info("Book added: %s", record["id"])
    return record


def update_book(book_id, title, author, category):
    book_id = _positive_int(book_id, "Book ID")
    books = load_records("books")

    for book in books:
        if book["id"] == book_id:
            book.update(
                title=_required(title, "Title"),
                author=_required(author, "Author"),
                category=_required(category, "Category")
            )

            save_records("books", books)
            logging.info("Book updated: %s", book_id)
            return book

    raise LibraryError("Book ID was not found.")


def delete_book(book_id):
    book_id = _positive_int(book_id, "Book ID")
    books = load_records("books")

    book = next(
        (b for b in books if b["id"] == book_id),
        None
    )

    if book is None:
        raise LibraryError("Book ID was not found.")

    if book["available"] != book["quantity"]:
        raise LibraryError(
            "Cannot delete a book while copies are issued."
        )

    save_records(
        "books",
        [b for b in books if b["id"] != book_id]
    )

    logging.info("Book deleted: %s", book_id)


def search_books(keyword):
    term = str(keyword).strip().casefold()
    books = load_records("books")

    if not term:
        return books

    return [
        b for b in books
        if term in " ".join(
            str(b.get(k, ""))
            for k in ("title", "author", "category")
        ).casefold()
    ]


def add_member(name, email, phone=""):
    name = _required(name, "Name")
    email = _required(email, "Email").casefold()

    if "@" not in email or "." not in email.split("@")[-1]:
        raise LibraryError("Enter a valid email address.")

    members = load_records("members")

    if any(m["email"].casefold() == email for m in members):
        raise LibraryError(
            "A member with this email already exists."
        )

    member = {
        "id": next_id(members),
        "name": name,
        "email": email,
        "phone": str(phone).strip()
    }

    members.append(member)
    save_records("members", members)

    logging.info("Member registered: %s", member["id"])
    return member


def issue_book(book_id, member_id, today=None):
    book_id = _positive_int(book_id, "Book ID")
    member_id = _positive_int(member_id, "Member ID")

    books = load_records("books")
    members = load_records("members")

    book = next(
        (b for b in books if b["id"] == book_id),
        None
    )

    member = next(
        (m for m in members if m["id"] == member_id),
        None
    )

    if book is None:
        raise LibraryError("Book ID was not found.")

    if member is None:
        raise LibraryError("Member ID was not found.")

    if int(book["available"]) < 1:
        raise LibraryError("No copies are available.")

    transactions = load_records("transactions")
    today = today or date.today()

    transaction = {
        "id": next_id(transactions),
        "book_id": book_id,
        "member_id": member_id,
        "issue_date": today.isoformat(),
        "due_date": (
            today + timedelta(days=LOAN_DAYS)
        ).isoformat(),
        "return_date": None,
        "status": "Issued",
        "fine": 0.0
    }

    book["available"] = int(book["available"]) - 1

    save_records("books", books)

    transactions.append(transaction)
    save_records("transactions", transactions)

    logging.info("Book issued: transaction %s", transaction["id"])
    return transaction


def calculate_fine(due_date, return_date=None):
    due = date.fromisoformat(due_date)
    returned = return_date or date.today()

    overdue_days = max((returned - due).days, 0)

    return round(overdue_days * FINE_PER_DAY, 2)


def return_book(transaction_id, today=None):
    transaction_id = _positive_int(
        transaction_id, "Transaction ID"
    )

    transactions = load_records("transactions")
    books = load_records("books")

    transaction = next(
        (t for t in transactions if t["id"] == transaction_id),
        None
    )

    if transaction is None:
        raise LibraryError("Transaction was not found.")

    if transaction["status"] != "Issued":
        raise LibraryError("Book has already been returned.")

    book = next(
        (b for b in books if b["id"] == transaction["book_id"]),
        None
    )

    if book is None:
        raise LibraryError("Linked book record is missing.")

    today = today or date.today()
    fine = calculate_fine(transaction["due_date"], today)

    transaction.update(
        return_date=today.isoformat(),
        status="Returned",
        fine=fine
    )

    book["available"] = min(
        int(book["available"]) + 1,
        int(book["quantity"])
    )

    save_records("books", books)
    save_records("transactions", transactions)

    logging.info("Book returned: transaction %s", transaction_id)
    return transaction


def overdue_transactions(today=None):
    today = today or date.today()
    result = []

    for tx in load_records("transactions"):
        if (
            tx["status"] == "Issued"
            and date.fromisoformat(tx["due_date"]) < today
        ):
            item = dict(tx)
            item["estimated_fine"] = calculate_fine(
                tx["due_date"], today
            )
            result.append(item)

    return result


def dashboard():
    books = load_records("books")
    members = load_records("members")
    transactions = load_records("transactions")

    return {
        "titles": len(books),
        "total_copies": sum(b["quantity"] for b in books),
        "available_copies": sum(b["available"] for b in books),
        "issued_copies": sum(
            b["quantity"] - b["available"] for b in books
        ),
        "members": len(members),
        "active_loans": sum(
            t["status"] == "Issued" for t in transactions
        ),
        "overdue_loans": len(overdue_transactions())
    }


def category_report():
    report = {}

    for book in load_records("books"):
        category = book["category"]
        report[category] = (
            report.get(category, 0) + book["quantity"]
        )

    return dict(sorted(report.items()))


def transaction_history():
    return load_records("transactions")


def load_sample_books():
    if load_records("books"):
        return 0

    samples = [
        ("Python Programming", "Reema Thareja", "Programming", 5),
        ("Clean Code", "Robert C. Martin", "Software", 3),
        ("Database System Concepts", "Abraham Silberschatz", "Database", 4),
        ("Computer Networks", "Andrew Tanenbaum", "Networking", 2),
        ("Artificial Intelligence", "Stuart Russell", "AI", 3)
    ]

    for title, author, category, quantity in samples:
        add_book(title, author, category, quantity)

    return len(samples)