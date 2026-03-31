"""
AI Service for Financial Insights
Integrates with Groq API for intelligent expense analysis
"""

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
import json
import config.config as config


def get_db():
    """Get database connection"""
    db = sqlite3.connect('expense_tracker.db')
    db.row_factory = sqlite3.Row
    return db


def generate_ai_insights(user_id):
    """
    Fetch and process user expenses for AI analysis
    
    Returns:
        dict: Structured summary of expenses
    """
    db = get_db()
    
    # Get current month
    current_month = datetime.now().strftime("%Y-%m")
    
    # Fetch expenses for current month
    expenses = db.execute(
        """SELECT category, description, amount, date 
           FROM expenses 
           WHERE user_id=? AND date LIKE ?
           ORDER BY date DESC""",
        (user_id, f"{current_month}%")
    ).fetchall()
    
    if not expenses:
        return {
            "total_spent": 0,
            "category_breakdown": {},
            "top_categories": [],
            "frequent_expenses": [],
            "transaction_count": 0
        }
    
    # Process data
    total_spent = 0
    category_breakdown = defaultdict(float)
    descriptions = []
    
    for exp in expenses:
        total_spent += exp['amount']
        category_breakdown[exp['category']] += exp['amount']
        descriptions.append(exp['description'].lower())
    
    # Get top categories
    top_categories = sorted(
        category_breakdown.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Get frequent keywords
    frequent_expenses = get_frequent_keywords(descriptions)
    
    return {
        "total_spent": round(total_spent, 2),
        "category_breakdown": dict(category_breakdown),
        "top_categories": [{"name": cat, "amount": round(amt, 2)} for cat, amt in top_categories],
        "frequent_expenses": frequent_expenses,
        "transaction_count": len(expenses),
        "month": current_month
    }


def get_frequent_keywords(descriptions):
    """Extract frequent keywords from expense descriptions"""
    keywords = defaultdict(int)
    
    # Common expense keywords
    expense_words = {
        "pizza", "burger", "food", "restaurant", "lunch", "dinner",
        "uber", "taxi", "auto", "bus", "train", "metro",
        "shopping", "clothes", "mall", "shoes", "dress",
        "movie", "cinema", "game", "netflix",
        "movie", "fruit", "vegetable", "medicine", "doctor"
    }
    
    for desc in descriptions:
        for word in desc.split():
            clean_word = word.lower().strip(".,!?;:")
            if clean_word in expense_words:
                keywords[clean_word] += 1
    
    # Return top 5 keywords
    top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
    return [{"keyword": kw, "count": cnt} for kw, cnt in top_keywords]


def get_ai_analysis(insights_data, analysis_type):
    """
    Call Groq API to get AI financial analysis
    """

    try:
        from groq import Groq
    except ImportError:
        return "⚠️ Groq library not installed. Please install it using: pip install groq"

    # Check API key
    if not hasattr(config, 'GROQ_API_KEY') or config.GROQ_API_KEY == "your_groq_api_key_here":
        return "⚠️ Groq API Key not configured. Please update config/config.py"

    try:
        client = Groq(api_key=config.GROQ_API_KEY)

        # ✅ Format data
        formatted_data = format_insights_for_prompt(insights_data)

        # ✅ Dynamic prompts
        if analysis_type == "financial":
            prompt = f"""
You are a professional financial advisor.

Analyze the user's complete financial activity in detail.

{formatted_data}

Provide:
- Detailed financial report
- Spending behavior insights
- Strengths and weaknesses
- Long-term financial health analysis

Avoid generic advice. Be specific to the data.
IMPORTANT:
Format the output in clean HTML.
Use <h3> for headings and <ul><li> for bullet points.
Do NOT use markdown like ** or *.
Use short paragraphs and spacing between sections.
"""

        elif analysis_type == "budget":
            prompt = f"""
You are an expert financial planner.

Based on the user's expense data:

{formatted_data}

Create a detailed monthly budget plan.

Include:
- Category-wise budget allocation
- Overspending areas
- Optimization strategy
- Practical restructuring plan

Give precise, actionable advice.
IMPORTANT:
Format the output in clean HTML.
Use <h3> for headings and <ul><li> for bullet points.
Do NOT use markdown like ** or *.
Use short paragraphs and spacing between sections.
"""

        elif analysis_type == "savings":
            prompt = f"""
You are a savings expert.

Analyze the data:

{formatted_data}

Provide:
- Personalized savings plan
- Realistic saving potential
- Wasteful spending areas
- Step-by-step improvement strategy

Make it practical and detailed.
IMPORTANT:
Format the output in clean HTML.
Use <h3> for headings and <ul><li> for bullet points.
Do NOT use markdown like ** or *.
Use short paragraphs and spacing between sections.
"""

        elif analysis_type == "spending":
            prompt = f"""
You are a financial behavior analyst.

Analyze:

{formatted_data}

Provide:
- Spending pattern analysis
- Bad habit identification
- Category-wise insights
- Behavioral patterns
- Control strategies

Make it analytical and insightful.
IMPORTANT:
Format the output in clean HTML.
Use <h3> for headings and <ul><li> for bullet points.
Do NOT use markdown like ** or *.
Use short paragraphs and spacing between sections.
"""

        else:
            prompt = f"Analyze this data:\n{formatted_data}"

        # ✅ Auto-select working model
        models = client.models.list()
        available_models = [m.id for m in models.data]

        preferred_models = [
            "llama-3.3-70b-versatile",
            "llama-3.3-8b-instant",
            "gemma2-9b-it"
        ]

        model_name = next((m for m in preferred_models if m in available_models), None)

        if not model_name:
            model_name = available_models[0]

        # ✅ API Call
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1500
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error calling Groq API: {str(e)}"
    
    
def format_insights_for_prompt(data):
    """Format insights data into readable text for AI prompt"""
    
    text = f"""
Month: {data.get('month', 'N/A')}
Total Spending: ₹{data.get('total_spent', 0)}
Number of Transactions: {data.get('transaction_count', 0)}

Category Breakdown:
"""
    
    for cat, amount in data.get('category_breakdown', {}).items():
        text += f"  - {cat}: ₹{amount:.2f}\n"
    
    text += "\nTop Spending Categories:\n"
    for cat_data in data.get('top_categories', []):
        text += f"  - {cat_data['name']}: ₹{cat_data['amount']}\n"
    
    if data.get('frequent_expenses'):
        text += "\nFrequent Expenses:\n"
        for exp in data.get('frequent_expenses', []):
            text += f"  - {exp['keyword'].capitalize()}: {exp['count']} times\n"
    
    return text
