# Expense Tracker Web Application

A complete AI Assisted Expense Tracker built with Python Flask, SQLite, HTML, CSS, JavaScript, Chart.js, and Web Speech API.

## Features

- User authentication (signup/login)
- Dashboard with expense summary
- Manual expense entry
- AI Chatbot (Nova) for voice/text expense addition
- Expense deletion via chatbot
- Charts for weekly, monthly, yearly views
- History with filters
- Profile page

## Setup

1. Install Python 3.x
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python app.py`
4. Open browser to `http://localhost:5000`

## Project Structure

```
expense_tracker/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── expense_tracker.db     # SQLite database (created automatically)
├── templates/             # HTML templates
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── weekly_records.html
│   ├── records.html (monthly)
│   ├── yearly_records.html
│   ├── history.html
│   └── profile.html
└── static/                # Static files
    ├── css/
    │   ├── style.css
    │   └── chatbot.css
    ├── js/
    │   ├── main.js
    │   └── chatbot.js
    └── images/
        └── default-avatar.png  # Add a default profile picture here
```

## Usage

1. Sign up with username, email, password
2. Log in
3. Add expenses manually or via chatbot
4. View charts and history
5. Use voice input with the microphone button in chatbot

## AI Chatbot Commands

- "I spent 200 rupees on pizza today using UPI"
- "I spent 500 yesterday using cash"
- "Delete today's expenses"
- "Delete all expense"

## New chatbot abilities:

Set monthly budget
Example: my monthly budget is 10000
Ask spending today
Example: how much did I spend today
Ask spending this month
Example: how much did I spend this month
Find highest category
Example: which category I spend most
Spending summary
Example: show my spending summary

Bot reply example:

Today's spending: ₹450
This month's spending: ₹5600
Top category: Shopping
Remaining budget: ₹4400
Budget warning (automatic) when adding expenses.


## Notes

- Passwords are hashed for security
- Speech recognition requires browser support
- Charts use Chart.js library
- Simple and beginner-friendly code