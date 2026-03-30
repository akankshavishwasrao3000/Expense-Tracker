from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import csv
from io import StringIO
from flask import Response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# store user budgets
user_budgets = {}

# Database setup
def get_db():
    db = sqlite3.connect('expense_tracker.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_pic TEXT
        )''')

        db.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        db.commit()

init_db()

# ---------------- HELPER FUNCTIONS ----------------

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap


def get_user_expenses(user_id, start_date=None, end_date=None):
    db = get_db()
    query = 'SELECT * FROM expenses WHERE user_id = ?'
    params = [user_id]

    if start_date and end_date:
        query += ' AND date BETWEEN ? AND ?'
        params.extend([start_date, end_date])

    query += ' ORDER BY date DESC'
    return db.execute(query, params).fetchall()


def parse_expense_message(message):

    amount_match = re.search(r'(\d+(?:\.\d+)?)', message)
    amount = float(amount_match.group(1)) if amount_match else 0

    message_lower = message.lower()

    categories = {
        "Food": ["pizza", "burger", "restaurant", "dinner", "lunch", "breakfast"],
        "Fruits": ["fruit", "apple", "banana", "mango", "orange"],
        "Transport": ["bus", "train", "metro", "uber", "ola", "auto", "petrol", "fuel"],
        "Shopping": ["shopping", "clothes", "dress", "shoes", "mall"],
        "Entertainment": ["movie", "cinema", "netflix", "game"],
        "Adventure": ["trekking", "climbing", "trip", "travel"],
        "Health": ["medicine", "hospital", "doctor"],
        "Education": ["book", "course", "fees"]
    }

    category = "General"

    for cat, keywords in categories.items():
        for word in keywords:
            if word in message_lower:
                category = cat
                break

    date = datetime.now().strftime('%Y-%m-%d')

    if "yesterday" in message_lower:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    payment_mode = "Cash"

    if "upi" in message_lower:
        payment_mode = "UPI"
    elif "card" in message_lower:
        payment_mode = "Card"
    elif "net banking" in message_lower:
        payment_mode = "Net Banking"

    return {
        "amount": amount,
        "category": category,
        "description": message,
        "date": date,
        "payment_mode": payment_mode
    }


# ---------------- ROUTES ----------------

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db()

        try:
            db.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                       (username, email, password))
            db.commit()

            flash('Account created successfully!', 'success')

            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            flash('Email already exists!', 'error')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        db = get_db()

        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):

            session['user_id'] = user['id']
            session['username'] = user['username']

            return redirect(url_for('dashboard'))

        else:
            flash('Invalid credentials!', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():

    user_id = session['user_id']

    expenses = get_user_expenses(user_id)

    total_expenses = sum(exp['amount'] for exp in expenses)

    current_month = datetime.now().strftime('%Y-%m')

    monthly_expenses = sum(exp['amount'] for exp in expenses if exp['date'].startswith(current_month))

    total_transactions = len(expenses)

    return render_template('dashboard.html',
                           username=session['username'],
                           total_expenses=total_expenses,
                           monthly_expenses=monthly_expenses,
                           total_transactions=total_transactions,
                           expenses=expenses)


@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():

    user_id = session['user_id']

    data = request.get_json()

    date = data['date']
    category = data['category']
    description = data['description']
    amount = float(data['amount'])
    payment_mode = data['payment_mode']
    entry_type = data['entry_type']

    db = get_db()

    db.execute('''INSERT INTO expenses (user_id, date, category, description, amount, payment_mode, entry_type)
                  VALUES (?, ?, ?, ?, ?, ?, ?)''',
               (user_id, date, category, description, amount, payment_mode, entry_type))

    db.commit()

    return jsonify({'success': True})


@app.route('/delete_expense/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):

    user_id = session['user_id']

    db = get_db()

    db.execute('DELETE FROM expenses WHERE id=? AND user_id=?', (expense_id, user_id))

    db.commit()

    return jsonify({'success': True})


# ---------------- CHATBOT ----------------

@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():

    user_id = session['user_id']

    message = request.get_json()['message'].lower()

    db = get_db()

    # -------- BUDGET SET --------
    if "budget" in message:

        amount_match = re.search(r'(\d+(?:\.\d+)?)', message)

        if not amount_match:
            return jsonify({"response": "Please specify your budget amount."})

        budget = float(amount_match.group(1))

        user_budgets[user_id] = budget

        return jsonify({"response": f"Monthly budget set to ₹{budget}."})


    # -------- SPENDING SUMMARY --------
    if "summary" in message:

        today = datetime.now().strftime("%Y-%m-%d")

        current_month = datetime.now().strftime("%Y-%m")

        today_total = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id=? AND date=?",
            (user_id, today)
        ).fetchone()[0] or 0

        month_total = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id=? AND date LIKE ?",
            (user_id, f"{current_month}%")
        ).fetchone()[0] or 0

        top_category = db.execute(
            """SELECT category, SUM(amount) as total
               FROM expenses
               WHERE user_id=?
               GROUP BY category
               ORDER BY total DESC
               LIMIT 1""",
            (user_id,)
        ).fetchone()

        category_name = top_category['category'] if top_category else "None"

        response = f"Today's spending: ₹{today_total}\nThis month's spending: ₹{month_total}\nTop category: {category_name}"

        if user_id in user_budgets:
            remaining = user_budgets[user_id] - month_total
            response += f"\nRemaining budget: ₹{remaining}"

        return jsonify({"response": response})


    # -------- SPENDING TODAY --------
    if "how much" in message and "today" in message:

        today = datetime.now().strftime("%Y-%m-%d")

        total = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id=? AND date=?",
            (user_id, today)
        ).fetchone()[0] or 0

        return jsonify({"response": f"You spent ₹{total} today."})


    # -------- SPENDING MONTH --------
    if "how much" in message and "month" in message:

        current_month = datetime.now().strftime("%Y-%m")

        total = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id=? AND date LIKE ?",
            (user_id, f"{current_month}%")
        ).fetchone()[0] or 0

        return jsonify({"response": f"You spent ₹{total} this month."})


    # -------- HIGHEST CATEGORY --------
    if "which category" in message:

        result = db.execute(
            """SELECT category, SUM(amount) as total
               FROM expenses
               WHERE user_id=?
               GROUP BY category
               ORDER BY total DESC
               LIMIT 1""",
            (user_id,)
        ).fetchone()

        if result:
            return jsonify({"response": f"Your highest spending category is {result['category']} with ₹{result['total']}."})

        return jsonify({"response": "No expenses found."})

    # -------- UPDATE EXPENSE --------
    if "update" in message or "change" in message or "modify" in message or "edit" in message:

        amount_match = re.search(r'(\d+(?:\.\d+)?)', message)

        if not amount_match:
            return jsonify({"response": "Please specify the new amount."})

        new_amount = float(amount_match.group(1))

        categories = {
            "Food": ["pizza", "burger", "restaurant", "dinner", "lunch", "breakfast", "food"],
            "Fruits": ["fruit", "apple", "banana", "mango", "orange"],
            "Transport": ["bus", "train", "metro", "uber", "ola", "auto", "petrol", "fuel"],
            "Shopping": ["shopping", "clothes", "dress", "shoes", "mall"],
            "Entertainment": ["movie", "cinema", "netflix", "game"],
            "Adventure": ["trekking", "climbing", "trip", "travel"],
            "Health": ["medicine", "hospital", "doctor"],
            "Education": ["book", "course", "fees"]
        }

        category = None

        for cat, keywords in categories.items():
            for word in keywords:
                if word in message:
                    category = cat
                    break
            if category:
                break

        if not category:
            return jsonify({"response": "Please mention the category to update."})

        if "yesterday" in message:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            date = datetime.now().strftime('%Y-%m-%d')

        # NEW DESCRIPTION
        new_description = f"{category} expense updated to {new_amount}"

        cursor = db.execute(
            """
            UPDATE expenses
            SET amount = ?, description = ?
            WHERE user_id = ? AND category = ? AND date = ?
            """,
            (new_amount, new_description, user_id, category, date)
        )

        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"response": f"No {category} expense found for {date}."})

        return jsonify({
            "response": f"{category} expense updated successfully to ₹{new_amount}."
        })

    # -------- DELETE EXPENSE --------
    if "delete" in message or "remove" in message:

        categories = {
            "Food": ["pizza", "burger", "restaurant", "dinner", "lunch", "breakfast", "food"],
            "Fruits": ["fruit", "apple", "banana", "mango", "orange"],
            "Transport": ["bus", "train", "metro", "uber", "ola", "auto", "petrol", "fuel"],
            "Shopping": ["shopping", "clothes", "dress", "shoes", "mall"],
            "Entertainment": ["movie", "cinema", "netflix", "game"],
            "Adventure": ["trekking", "climbing", "trip", "travel"],
            "Health": ["medicine", "hospital", "doctor"],
            "Education": ["book", "course", "fees"]
        }

        category = None

        for cat, keywords in categories.items():
            for word in keywords:
                if word in message:
                    category = cat
                    break
            if category:
                break

        if not category:
            return jsonify({"response": "Please mention the category to delete."})

        if "yesterday" in message:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            date = datetime.now().strftime('%Y-%m-%d')

        cursor = db.execute(
            """
            DELETE FROM expenses
            WHERE user_id = ? AND category = ? AND date = ?
            """,
            (user_id, category, date)
        )

        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"response": f"No {category} expense found to delete."})

        return jsonify({"response": f"{category} expense deleted successfully."})

    # -------- ADD EXPENSE --------
    expense_data = parse_expense_message(message)

    if expense_data['amount'] > 0:

        db.execute(
            '''INSERT INTO expenses (user_id, date, category, description, amount, payment_mode, entry_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id,
             expense_data['date'],
             expense_data['category'],
             expense_data['description'],
             expense_data['amount'],
             expense_data['payment_mode'],
             'Chatbot')
        )

        db.commit()

        response = f"Expense of ₹{expense_data['amount']} added successfully in {expense_data['category']} category."

        if user_id in user_budgets:

            current_month = datetime.now().strftime("%Y-%m")

            monthly_total = db.execute(
                "SELECT SUM(amount) FROM expenses WHERE user_id=? AND date LIKE ?",
                (user_id, f"{current_month}%")
            ).fetchone()[0] or 0

            budget = user_budgets[user_id]

            if monthly_total >= budget:
                response += "\n🚨 You exceeded your monthly budget!"

            elif monthly_total >= 0.8 * budget:
                response += "\n⚠ Warning: You used 80% of your monthly budget."

        return jsonify({"response": response})

    return jsonify({"response": "Could not understand your message."})


# ---------------- ANALYTICS PAGES ----------------

@app.route('/weekly-records')
@login_required
def weekly_records():

    user_id = session['user_id']

    end_date = datetime.now()

    start_date = end_date - timedelta(days=7)

    expenses = get_user_expenses(user_id,
                                 start_date.strftime('%Y-%m-%d'),
                                 end_date.strftime('%Y-%m-%d'))

    daily_expenses = {}
    category_expenses = {}

    for exp in expenses:
        daily_expenses[exp['date']] = daily_expenses.get(exp['date'], 0) + exp['amount']
        category_expenses[exp['category']] = category_expenses.get(exp['category'], 0) + exp['amount']

    return render_template('weekly_records.html',
                           daily_expenses=daily_expenses,
                           category_expenses=category_expenses)


@app.route('/records')
@login_required
def records():

    user_id = session['user_id']

    current_month = datetime.now().strftime('%Y-%m')

    start_date = f"{current_month}-01"

    # Get last day of month
    next_month = datetime.now().replace(day=28) + timedelta(days=4)
    end_date = (next_month - timedelta(days=next_month.day)).strftime('%Y-%m-%d')

    expenses = get_user_expenses(user_id, start_date, end_date)

    weekly_expenses = {}
    category_expenses = {}

    for exp in expenses:
        # Calculate week number in month
        exp_date = datetime.strptime(exp['date'], '%Y-%m-%d')
        week_num = (exp_date.day - 1) // 7 + 1
        week_key = f"{week_num}"
        weekly_expenses[week_key] = weekly_expenses.get(week_key, 0) + exp['amount']
        category_expenses[exp['category']] = category_expenses.get(exp['category'], 0) + exp['amount']

    return render_template('records.html',
                           weekly_expenses=weekly_expenses,
                           category_expenses=category_expenses)


@app.route('/yearly-records')
@login_required
def yearly_records():

    user_id = session['user_id']

    current_year = datetime.now().strftime('%Y')

    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"

    expenses = get_user_expenses(user_id, start_date, end_date)

    monthly_expenses = {}
    category_expenses = {}

    for exp in expenses:
        month = exp['date'][:7]  # YYYY-MM
        monthly_expenses[month] = monthly_expenses.get(month, 0) + exp['amount']
        category_expenses[exp['category']] = category_expenses.get(exp['category'], 0) + exp['amount']

    return render_template('yearly_records.html',
                           monthly_expenses=monthly_expenses,
                           category_expenses=category_expenses)


@app.route('/history')
@login_required
def history():

    user_id = session['user_id']

    expenses = get_user_expenses(user_id)

    return render_template('history.html', expenses=expenses)


@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    db = get_db()

    user = db.execute(
        'SELECT * FROM users WHERE id=?',
        (user_id,)
    ).fetchone()

    return render_template('profile.html', user=user)

@app.route('/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():

    if 'profile_pic' not in request.files:
        return redirect(url_for('profile'))

    file = request.files['profile_pic']

    if file.filename == '':
        return redirect(url_for('profile'))

    filename = f"user_{session['user_id']}.png"

    filepath = os.path.join('static/profile_pics', filename)
    file.save(filepath)

    db = get_db()
    db.execute(
        "UPDATE users SET profile_pic=? WHERE id=?",
        (filename, session['user_id'])
    )
    db.commit()

    flash("Profile picture updated successfully!", "success")

    return redirect(url_for('profile'))

@app.route('/export-csv')
@login_required
def export_csv():

    user_id = session['user_id']
    expenses = get_user_expenses(user_id)

    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Date', 'Category', 'Description', 'Amount', 'Payment Mode'])

    for exp in expenses:
        writer.writerow([
            # Prepend space to prevent Excel from auto-formatting as Date which causes ##### due to col width
            f" {exp['date']}",
            exp['category'],
            exp['description'],
            f"{float(exp['amount']):.2f}",
            exp['payment_mode']
        ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expense_report.csv"}
    )

@app.route('/export-pdf')
@login_required
def export_pdf():

    user_id = session['user_id']
    expenses = get_user_expenses(user_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center alignment
    
    normal_style = styles['Normal']
    normal_style.fontSize = 11

    # 1. Title
    elements.append(Paragraph("Expense Report", title_style))
    elements.append(Spacer(1, 0.25 * inch))

    # 2. User info
    username = session.get('username', 'User')
    current_date = datetime.now().strftime('%Y-%m-%d')
    elements.append(Paragraph(f"<b>Username:</b> {username}", normal_style))
    elements.append(Paragraph(f"<b>Report Date:</b> {current_date}", normal_style))
    elements.append(Spacer(1, 0.15 * inch))

    # 3. Summary section
    total_expenses = sum(exp['amount'] for exp in expenses)
    current_month = datetime.now().strftime('%Y-%m')
    monthly_expenses = sum(exp['amount'] for exp in expenses if exp['date'].startswith(current_month))

    elements.append(Paragraph(f"<b>Total Expenses:</b> {total_expenses:.2f}", normal_style))
    elements.append(Paragraph(f"<b>Monthly Expense:</b> {monthly_expenses:.2f}", normal_style))
    elements.append(Spacer(1, 0.3 * inch))

    # 4 & 5. Table
    data = [['Date', 'Category', 'Description', 'Amount', 'Payment Mode']]
    for exp in expenses:
        data.append([
            str(exp['date']),
            str(exp['category']),
            Paragraph(str(exp['description']), normal_style),
            f"{float(exp['amount']):.2f}",
            str(exp['payment_mode'])
        ])

    table = Table(data, colWidths=[1.1*inch, 1.2*inch, 2.2*inch, 1*inch, 1.3*inch], hAlign='CENTER')
    t_style = TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    table.setStyle(t_style)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment;filename=expense_report.pdf'}
    )


if __name__ == '__main__':
    app.run(debug=True)