# Moneta — Personal Finance Tracker

Moneta is a full-stack personal finance tracker. Every user has their own
account, their own transactions, and their own low-balance alert — all
backed by a real Python server and a real database, not just local
browser storage.

## Features

- **Accounts with real security** — sign up and log in with email +
  password. Passwords are hashed with PBKDF2-SHA256 (`werkzeug.security`)
  before they're stored; the app never keeps a plain-text password.
- **Session-based authentication** via Flask-Login — dashboard and API
  routes are protected with `@login_required`, and every query is scoped
  to `current_user`, so one account can never see another's data.
- **Live balance dashboard** — animated balance, income and expense
  totals, and a category breakdown ring for spending.
- **Low balance alerts** — set your own alert threshold; a banner and a
  pop-up notice appear automatically the moment your balance drops
  below it.
- **Full transaction CRUD** — add and delete income/expense entries
  through a JSON API, backed by a SQLite database via SQLAlchemy.
- **Dark/light theme toggle**, responsive layout, and a distinct
  ledger-inspired visual design (not a generic admin template).

## Tech stack

| Layer     | Choice                                   |
|-----------|-------------------------------------------|
| Backend   | Python, Flask                             |
| Database  | SQLite via Flask-SQLAlchemy               |
| Auth      | Flask-Login + Werkzeug password hashing   |
| Frontend  | HTML (Jinja2 templates), vanilla JS, CSS  |
| Fonts/Icons | Google Fonts (Fraunces, Inter), Font Awesome 6 |

## Project structure

```
moneta/
├── app.py                 # Flask app: routes, auth, JSON API
├── models.py               # SQLAlchemy models (User, Transaction)
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   └── dashboard.html
└── static/
    ├── css/style.css
    └── js/
        ├── auth.js         # password show/hide toggle
        └── dashboard.js     # dashboard <-> API logic
```

## Getting started

1. **Clone the repo and enter the folder**
   ```bash
   git clone https://github.com/<your-username>/moneta.git
   cd moneta
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **(Optional but recommended) set a secret key**
   ```bash
   export SECRET_KEY="replace-with-a-long-random-string"   # Windows: set SECRET_KEY=...
   ```
   If you skip this, a development key is used automatically — fine for
   testing locally, but replace it before deploying anywhere public.

4. **Run the app**
   ```bash
   python app.py
   ```
   The database (`moneta.db`) is created automatically on first run.

5. **Open** `http://127.0.0.1:5000` in your browser, create an account,
   and start adding entries.

## How the low-balance alert works

Each account has an `alert_threshold` (default ₹5,000, editable from the
dashboard). Every time the dashboard loads or a transaction changes the
balance, the frontend checks the latest balance against that threshold.
If the balance drops below it, a banner appears under the header and a
one-time pop-up notice is shown — it won't nag on every refresh, only
when the balance newly crosses the line.

## Security notes

- Passwords are hashed, never stored or logged in plain text.
- Session cookies are marked `HttpOnly` and `SameSite=Lax`.
- All data-changing routes require an authenticated session
  (`@login_required`) and are scoped to `current_user.id`.
- `debug=True` in `app.py` is for local development only — turn it off
  and set `SESSION_COOKIE_SECURE = True` before deploying over HTTPS.

## Possible next steps

- Add CSRF protection (e.g. Flask-WTF) on the auth forms.
- Add email verification / password reset flow.
- Add monthly/category spending charts and CSV export.
- Move from SQLite to PostgreSQL for a production deployment.

## License

Free to use and modify for learning and personal projects.
