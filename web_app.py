import os
import json
import csv
import io
import logging
from datetime import date, timedelta
from html import escape
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# CAMPUSLIBRARY WEB APPLICATION

PORT = 8000
DATA = "data"
os.makedirs(DATA, exist_ok=True)

BOOKS = os.path.join(DATA, "books.json")
MEMBERS = os.path.join(DATA, "members.json")
ISSUES = os.path.join(DATA, "transactions.json")

logging.basicConfig(
    filename=os.path.join(DATA, "library.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            result = json.load(f)
            return result if isinstance(result, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def save(path, items):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=4)

books = load(BOOKS)
members = load(MEMBERS)
issues = load(ISSUES)

def persist():
    save(BOOKS, books)
    save(MEMBERS, members)
    save(ISSUES, issues)

def fine(issue):
    if issue.get("returned"):
        return 0
    due = date.fromisoformat(issue["due_date"])
    return max(0, (date.today() - due).days) * 2

def safe(value):
    return escape(str(value))

# DESIGN

CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:Arial;background:#f1f5f9;color:#172554}
header{background:linear-gradient(120deg,#101b40,#2563eb);
color:white;padding:28px 35px}
header h1{margin:0;font-size:30px}
header p{color:#dbeafe}
nav{background:white;padding:16px;display:flex;flex-wrap:wrap;
gap:16px;box-shadow:0 2px 8px #ddd}
nav a{text-decoration:none;color:#1d4ed8;font-weight:bold}
main{max-width:1150px;margin:25px auto;padding:15px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}
.card,.panel{background:white;padding:22px;border-radius:13px;
box-shadow:0 3px 12px #0001;margin-bottom:18px}
.card h2{color:#2563eb;font-size:32px}
input{width:100%;padding:12px;margin:8px 0 15px;
border:1px solid #cbd5e1;border-radius:7px}
button{background:#2563eb;color:white;border:0;padding:11px 17px;
border-radius:7px;cursor:pointer}
button:hover{background:#1e40af}
table{width:100%;border-collapse:collapse;background:white}
th,td{padding:12px;text-align:left;border-bottom:1px solid #e2e8f0}
th{background:#dbeafe}
.notice{background:#dcfce7;color:#166534;padding:12px;border-radius:8px}
.error{background:#fee2e2;color:#991b1b;padding:12px;border-radius:8px}
.scroll{overflow-x:auto}
footer{text-align:center;color:#64748b;padding:25px}
@media(max-width:600px){main{padding:10px}table{font-size:12px}
th,td{padding:7px}}
"""

def layout(content, message=""):
    return f"""<!DOCTYPE html>
<html>
<head>
<title>CampusLibrary</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
</head>
<body>
<header>
<h1>📚 CampusLibrary</h1>
<p>Your Smart Digital Library Management System</p>
</header>
<nav>
<a href="/">Dashboard</a>
<a href="/?view=books">Books</a>
<a href="/?view=add">Add Book</a>
<a href="/?view=members">Members</a>
<a href="/?view=register">Register Member</a>
<a href="/?view=issue">Issue Book</a>
<a href="/?view=transactions">Transactions</a>
<a href="/?view=overdue">Overdue</a>
<a href="/?view=export">CSV Export</a>
</nav>
<main>
{f'<p class="notice">{safe(message)}</p>' if message else ''}
{content}
</main>
<footer>CampusLibrary © 2026 | Smart Library Management</footer>
</body>
</html>"""

def table(headers, rows):
    head = "".join(f"<th>{safe(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><tr>{head}</tr>{body}</table></div>'

# WEB SERVER

class LibraryServer(BaseHTTPRequestHandler):

    def respond(self, content, message=""):
        data = layout(content, message).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, message):
        self.send_response(303)
        self.send_header("Location", "/?msg=" + message.replace(" ", "%20"))
        self.end_headers()

    def form_data(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        return {k: v[0] for k, v in parse_qs(raw).items()}

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        view = params.get("view", ["dashboard"])[0]
        message = params.get("msg", [""])[0]

        if view == "dashboard":
            active = [i for i in issues if not i.get("returned")]
            overdue = sum(1 for i in active if fine(i) > 0)

            content = f"""
            <h2>Welcome to CampusLibrary 👋</h2>
            <p>Manage your library activities from one smart platform.</p>
            <div class="cards">
            <div class="card"><p>Total Book Titles</p><h2>{len(books)}</h2></div>
            <div class="card"><p>Available Copies</p>
            <h2>{sum(b['available'] for b in books)}</h2></div>
            <div class="card"><p>Registered Members</p><h2>{len(members)}</h2></div>
            <div class="card"><p>Active Issues</p><h2>{len(active)}</h2></div>
            <div class="card"><p>Overdue Books</p><h2>{overdue}</h2></div>
            </div>
            <div class="panel">
            <h3>✨ Library Services</h3>
            <p>📖 Book management and search</p>
            <p>👥 Member registration</p>
            <p>📤 Issue and return books</p>
            <p>⏰ Overdue tracking and fine calculation</p>
            <p>📊 Reports and CSV export</p>
            </div>"""

        elif view == "books":
            query = params.get("search", [""])[0].lower()
            found = [b for b in books if query in (
                b["id"] + b["title"] + b["author"] + b["category"]
            ).lower()]

            rows = []
            for b in found:
                action = f"""
                <form method="POST">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="id" value="{safe(b['id'])}">
                <button>Delete</button></form>"""
                rows.append([
                    safe(b["id"]), safe(b["title"]),
                    safe(b["author"]), safe(b["category"]),
                    str(b["available"]), action
                ])

            content = f"""
            <h2>📚 Book Collection</h2>
            <div class="panel">
            <form method="GET">
            <input type="hidden" name="view" value="books">
            <input name="search" placeholder="Search books">
            <button>Search</button>
            </form>
            {table(["ID","Title","Author","Category","Available","Action"], rows)}
            </div>"""

        elif view == "add":
            content = """
            <div class="panel"><h2>➕ Add New Book</h2>
            <form method="POST">
            <input type="hidden" name="action" value="add">
            Book ID<input name="id" required>
            Book Title<input name="title" required>
            Author<input name="author" required>
            Category<input name="category" required>
            Copies<input type="number" name="copies" min="1" value="1" required>
            <button>Add Book</button>
            </form></div>"""

        elif view == "members":
            rows = [[safe(m["id"]), safe(m["name"]), safe(m["email"])]
                    for m in members]
            content = "<h2>👥 Registered Members</h2><div class='panel'>" + \
                table(["Member ID","Name","Email"], rows) + "</div>"

        elif view == "register":
            content = """
            <div class="panel"><h2>👤 Register Member</h2>
            <form method="POST">
            <input type="hidden" name="action" value="register">
            Member ID<input name="id" required>
            Full Name<input name="name" required>
            Email<input type="email" name="email" required>
            <button>Register Member</button>
            </form></div>"""

        elif view == "issue":
            content = """
            <div class="panel"><h2>📤 Issue a Book</h2>
            <form method="POST">
            <input type="hidden" name="action" value="issue">
            Book ID<input name="book_id" required>
            Member ID<input name="member_id" required>
            <button>Issue Book</button>
            </form></div>"""

        elif view == "return":
            content = """
            <div class="panel"><h2>📥 Return a Book</h2>
            <form method="POST">
            <input type="hidden" name="action" value="return">
            Transaction ID<input type="number" name="transaction_id" min="1" required>
            <button>Return Book</button>
            </form></div>"""

        elif view == "transactions":
            rows = []
            for i, t in enumerate(issues):
                rows.append([
                    str(i + 1), safe(t["book_id"]),
                    safe(t["member_id"]), safe(t["issue_date"]),
                    safe(t["due_date"]),
                    "Returned" if t.get("returned") else "Issued",
                    "₹" + str(fine(t))
                ])
            content = "<h2>📋 Transactions</h2><div class='panel'>" + \
                table(["ID","Book","Member","Issue Date","Due Date",
                       "Status","Fine"], rows) + "</div>"

        elif view == "overdue":
            rows = []
            for i, t in enumerate(issues):
                if not t.get("returned") and fine(t) > 0:
                    rows.append([
                        str(i + 1), safe(t["book_id"]),
                        safe(t["member_id"]), safe(t["due_date"]),
                        "₹" + str(fine(t))
                    ])
            content = "<h2>⏰ Overdue Books</h2><div class='panel'>" + \
                table(["ID","Book","Member","Due Date","Fine"], rows) + "</div>"

        elif view == "export":
            content = """
            <div class="panel">
            <h2>📊 Export Library Records</h2>
            <p>Download your book records as a CSV file.</p>
            <a href="/download"><button>Download Books CSV</button></a>
            </div>"""

        else:
            content = "<h2>Page not found</h2>"

        self.respond(content, message)

    def do_POST(self):
        global books, members, issues

        data = self.form_data()
        action = data.get("action", "")

        try:
            if action == "add":
                book_id = data["id"].strip()
                if any(b["id"] == book_id for b in books):
                    raise ValueError("Book ID already exists")

                copies = int(data["copies"])
                if copies < 1:
                    raise ValueError("Copies must be at least one")

                books.append({
                    "id": book_id,
                    "title": data["title"].strip(),
                    "author": data["author"].strip(),
                    "category": data["category"].strip(),
                    "copies": copies,
                    "available": copies
                })
                message = "Book added successfully"

            elif action == "delete":
                book = next((b for b in books if b["id"] == data["id"]), None)
                if not book:
                    raise ValueError("Book not found")
                if book["available"] != book["copies"]:
                    raise ValueError("Cannot delete a book currently issued")
                books.remove(book)
                message = "Book deleted successfully"

            elif action == "register":
                member_id = data["id"].strip()
                if any(m["id"] == member_id for m in members):
                    raise ValueError("Member ID already exists")

                members.append({
                    "id": member_id,
                    "name": data["name"].strip(),
                    "email": data["email"].strip()
                })
                message = "Member registered successfully"

            elif action == "issue":
                book = next((b for b in books if b["id"] == data["book_id"]), None)
                member = next((m for m in members if m["id"] == data["member_id"]), None)

                if not book:
                    raise ValueError("Book ID not found")
                if not member:
                    raise ValueError("Member ID not found")
                if book["available"] < 1:
                    raise ValueError("No copies available")

                book["available"] -= 1
                today = date.today()

                issues.append({
                    "book_id": book["id"],
                    "member_id": member["id"],
                    "issue_date": today.isoformat(),
                    "due_date": (today + timedelta(days=14)).isoformat(),
                    "returned": False
                })
                message = "Book issued successfully"

            elif action == "return":
                index = int(data["transaction_id"]) - 1

                if index < 0 or index >= len(issues):
                    raise ValueError("Invalid transaction ID")

                transaction = issues[index]
                if transaction.get("returned"):
                    raise ValueError("Book already returned")

                transaction["returned"] = True
                transaction["return_date"] = date.today().isoformat()
                book = next(b for b in books if b["id"] == transaction["book_id"])
                book["available"] += 1
                message = "Book returned successfully. Fine: ₹" + str(fine(transaction))

            else:
                raise ValueError("Invalid action")

            persist()
            logging.info(message)
            self.redirect(message)

        except (ValueError, KeyError, StopIteration) as error:
            logging.warning(str(error))
            self.redirect("Error: " + str(error))

    def do_GET_download(self):
        pass

# CSV DOWNLOAD ROUTE

class CampusLibraryServer(LibraryServer):

    def do_GET(self):
        if urlparse(self.path).path == "/download":
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["id","title","author","category","copies","available"]
            )
            writer.writeheader()
            writer.writerows(books)

            data = output.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","text/csv")
            self.send_header(
                "Content-Disposition",
                'attachment; filename="campuslibrary_books.csv"'
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        super().do_GET()


# ---------------- START SERVER ----------------

if __name__ == "__main__":
    persist()
    server = HTTPServer(("127.0.0.1", PORT), CampusLibraryServer)

    print("=" * 45)
    print("       CAMPUSLIBRARY WEB APPLICATION")
    print("=" * 45)
    print("Server running successfully!")
    print("Open Chrome: http://127.0.0.1:8000")
    print("Press CTRL + C to stop the server")
    print("=" * 45)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCampusLibrary server stopped.")
        server.server_close()