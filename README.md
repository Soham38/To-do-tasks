# 📋 Simple Tasks - Full-Stack Task Management Platform

A responsive, full-stack task management web application built with **Flask**, **SQLAlchemy**, and vanilla JavaScript. Features instant anonymous guest lists with shareable UUIDs, user authentication, drag-and-drop reordering, minute-level due-date scheduling, browser notifications, and complete automated test coverage with `pytest`.

---

## ✨ Features

- **Guest & Account Modes:**
  - **Guest Mode:** Instant, friction-free lists assigned unique UUIDs without requiring signup.
  - **Account Mode:** Secure user registration and login with `werkzeug.security` password hashing and a private multi-list workspace dashboard.
- **Dynamic Task Interactions:**
  - Drag-and-drop task reordering powered by [SortableJS](https://sortablejs.github.io/Sortable/).
  - Real-time priority tags (`High`, `Normal`, `Low`) and inline editable list titles.
  - Asynchronous DOM updates via native `fetch` REST API calls (no full-page reloads).
- **Scheduling & Alerts:**
  - Exact date and time assignment via `datetime-local` inputs.
  - Native browser desktop notifications with automated minute-level alert checking for upcoming due tasks.
- **Data Portability:**
  - One-click `.txt` file export formatting formatted markdown-style task checklists.
- **Production-Ready & Tested:**
  - Automated unit and integration test suite using `pytest` running against an isolated in-memory database.
  - Configured for production deployment with Gunicorn and PostgreSQL compatibility.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.13, Flask, Flask-Login, Flask-SQLAlchemy
- **Database:** SQLite (Development / In-Memory Testing), PostgreSQL (Production)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+), SortableJS
- **Testing:** Pytest
- **Deployment:** Gunicorn, Render

---

## 📁 Project Structure

```text
To-do-tasks/
├── instance/               # Local SQLite database instances
├── static/
│   └── style.css          # Core responsive styling
├── templates/
│   ├── base.html          # Base layout wrapper
│   ├── index.html         # Landing page & feature showcase
│   ├── list.html          # Dynamic task board interface
│   ├── dashboard.html     # User account management dashboard
│   ├── login.html         # User sign-in interface
│   └── register.html      # User registration interface
├── conftest.py            # Pytest client and in-memory DB fixtures
├── main.py                # Flask application, models, and API endpoints
├── test_app.py            # Automated unit and integration tests
├── Procfile               # Production WSGI startup definition
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation