"""CampusLibrary main application."""

from database import (
    StorageError,
    import_books_csv,
    export_csv
)

from services import (
    LibraryError,
    add_book,
    update_book,
    delete_book,
    search_books,
    add_member,
    issue_book,
    return_book,
    load_sample_books
)

from reports import (
    print_dashboard,
    print_books,
    print_members,
    print_categories,
    print_overdue,
    print_history
)


def ask_text(prompt):
    return input(prompt).strip()


def ask_id(prompt):
    value = ask_text(prompt)

    try:
        number = int(value)

        if number < 1:
            raise ValueError

        return number

    except ValueError as exc:
        raise LibraryError(
            "Please enter a positive whole number."
        ) from exc


def show_menu():
    print("""
========== CAMPUSLIBRARY ==========

1. Dashboard
2. Add book
3. View all books
4. Update book
5. Delete book
6. Search books
7. Register member
8. View members
9. Issue a book
10. Return a book
11. Transaction history
12. Category report
13. Overdue books and fine estimate
14. Import books from CSV
15. Export records to CSV
16. Load sample books
17. Exit
""")


def run():
    print("Welcome to CampusLibrary!")

    while True:
        show_menu()
        choice = ask_text("Enter your choice (1-17): ")

        try:

            if choice == "1":
                print_dashboard()

            elif choice == "2":
                add_book(
                    ask_text("Title: "),
                    ask_text("Author: "),
                    ask_text("Category: "),
                    ask_id("Quantity: ")
                )
                print("Book added successfully.")

            elif choice == "3":
                print_books()

            elif choice == "4":
                update_book(
                    ask_id("Book ID: "),
                    ask_text("New title: "),
                    ask_text("New author: "),
                    ask_text("New category: ")
                )
                print("Book updated successfully.")

            elif choice == "5":
                delete_book(ask_id("Book ID: "))
                print("Book deleted successfully.")

            elif choice == "6":
                term = ask_text(
                    "Search title, author or category: "
                )

                rows = search_books(term)

                for b in rows:
                    print(
                        f'{b["id"]}. {b["title"]} by '
                        f'{b["author"]} '
                        f'({b["available"]}/{b["quantity"]} available)'
                    )

                if not rows:
                    print("No matching books.")

            elif choice == "7":
                add_member(
                    ask_text("Member name: "),
                    ask_text("Email: "),
                    ask_text("Phone (optional): ")
                )
                print("Member registered successfully.")

            elif choice == "8":
                print_members()

            elif choice == "9":
                issue_book(
                    ask_id("Book ID: "),
                    ask_id("Member ID: ")
                )
                print("Book issued successfully.")

            elif choice == "10":
                tx = return_book(
                    ask_id("Transaction ID: ")
                )
                print(
                    f'Book returned. Fine: Rs. {tx["fine"]:.2f}'
                )

            elif choice == "11":
                print_history()

            elif choice == "12":
                print_categories()

            elif choice == "13":
                print_overdue()

            elif choice == "14":
                path = ask_text("CSV file path: ")
                count, errors = import_books_csv(path)

                print(f"Imported {count} book(s).")

                for error in errors:
                    print(" -", error)

            elif choice == "15":
                kind = ask_text(
                    "Export books, members or transactions? "
                ).lower()

                if kind not in {
                    "books", "members", "transactions"
                }:
                    raise LibraryError(
                        "Choose books, members or transactions."
                    )

                path = ask_text(
                    "Output CSV filename: "
                )

                print(
                    f"Exported {export_csv(kind, path)} record(s)."
                )

            elif choice == "16":
                count = load_sample_books()

                if count:
                    print(f"Loaded {count} sample books.")
                else:
                    print("Books already exist. No duplicates added.")

            elif choice == "17":
                print("Thank you for using CampusLibrary!")
                break

            else:
                print("Choose a number from 1 to 17.")

        except (LibraryError, StorageError) as exc:
            print(f"Cannot complete request: {exc}")

        except (EOFError, KeyboardInterrupt):
            print("\nExiting CampusLibrary.")
            break

        except Exception as exc:
            import logging
            logging.exception("Unexpected application error")

            print(
                "An unexpected error occurred. "
                "Check data/campuslibrary.log."
            )

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    run()