"""JSON persistence layer for CampusLibrary."""

from __future__ import annotations
import csv
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

FILES = {
    "books": DATA_DIR / "books.json",
    "members": DATA_DIR / "members.json",
    "transactions": DATA_DIR / "transactions.json",
}

logging.basicConfig(
    filename=DATA_DIR / "campuslibrary.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


class StorageError(Exception):
    pass


def _ensure_file(name):
    if name not in FILES:
        raise ValueError("Unknown record collection")
    path = FILES[name]
    if not path.exists():
        atomic_write_json(path, [])
    return path


def atomic_write_json(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None

    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8",
            dir=path.parent, delete=False
        ) as temp:
            temp_name = temp.name
            json.dump(records, temp, indent=4)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())

        os.replace(temp_name, path)

    except OSError as exc:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)

        logging.exception("Save failed")
        raise StorageError(str(exc)) from exc


def load_records(name):
    path = _ensure_file(name)

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise StorageError("Invalid data format")

        if any(not isinstance(item, dict) for item in data):
            raise StorageError("Invalid record format")

        return data

    except json.JSONDecodeError as exc:
        logging.exception("Invalid JSON")
        raise StorageError(
            "Data file contains invalid JSON."
        ) from exc

    except OSError as exc:
        logging.exception("Read failed")
        raise StorageError(str(exc)) from exc


def save_records(name, records):
    atomic_write_json(_ensure_file(name), records)


def next_id(records):
    return max(
        (int(row.get("id", 0)) for row in records),
        default=0
    ) + 1


def import_books_csv(file_path):
    imported = 0
    errors = []
    books = load_records("books")

    try:
        with open(
            file_path, "r",
            newline="", encoding="utf-8-sig"
        ) as file:

            reader = csv.DictReader(file)
            required = {
                "title", "author", "category", "quantity"
            }

            if not reader.fieldnames or not required.issubset(
                set(reader.fieldnames)
            ):
                raise ValueError(
                    "CSV headers must be: title,author,category,quantity"
                )

            for line_no, row in enumerate(reader, start=2):
                try:
                    title = (row.get("title") or "").strip()
                    author = (row.get("author") or "").strip()
                    category = (row.get("category") or "").strip()
                    quantity = int(row.get("quantity", ""))

                    if not title or not author or not category:
                        raise ValueError("Empty book details")

                    if quantity < 1:
                        raise ValueError("Quantity must be positive")

                    books.append({
                        "id": next_id(books),
                        "title": title,
                        "author": author,
                        "category": category,
                        "quantity": quantity,
                        "available": quantity
                    })

                    imported += 1

                except (TypeError, ValueError) as exc:
                    errors.append(f"Line {line_no}: {exc}")

        if imported:
            save_records("books", books)
            logging.info("Imported %d books", imported)

    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))

    return imported, errors


def export_csv(name, file_path):
    records = load_records(name)

    if not records:
        return 0

    destination = Path(file_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(dict.fromkeys(
        key for record in records for key in record
    ))

    try:
        with destination.open(
            "w", newline="", encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(records)

    except OSError as exc:
        logging.exception("CSV export failed")
        raise StorageError(str(exc)) from exc

    logging.info("Exported %d records", len(records))
    return len(records)