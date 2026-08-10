# StudentSense Windows Setup Guide

This guide shows how to set up and run StudentSense on Windows.

## 1. Create a virtual environment

Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
```

If `py` does not work, try:

```powershell
python -m venv .venv
```

## 2. Activate the virtual environment

In PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

In Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

If PowerShell blocks activation, run this once in PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the environment again.

## 3. Install dependencies

Install the Python packages used by the app:

```powershell
pip install -r requirements.txt
```


## 4. Apply the database migrations

Run the migrations so the SQLite database matches the current models:

```powershell
python manage.py migrate
```

## 5. Run the application

Start the Django development server:

```powershell
python manage.py runserver 0.0.0.0:8000
```

Open your browser and visit:

```text
http://127.0.0.1:8000
```

## Counselor demo account

Use this existing counselor account for the counselor dashboard during setup or demos:

- Username: `counselor_demo`
- Password: `StrongPass123!`

This account is already marked as a counselor in the database, so it can access the counselor dashboard and student detail pages.

## 10. Suggested demo order

If you are demoing the app on Windows, this order works well:

1. Open the home page banner
2. Open About and How To
3. Register a student account
4. Log in as the student
5. Complete the intake form
6. Show the result page
7. Show the progress/history page
8. Log out
9. Log in as a counselor
10. Open the counselor dashboard
11. Open a student detail page
12. End on the homepage

## 11. Project notes

- The homepage is the banner/landing page before login.
- The intake form includes guidance for each field.
- The app stores every submission as a new history entry.
- Counselors only see students with Moderate or High stress.

