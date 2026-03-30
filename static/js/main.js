// main.js - General JavaScript for the Expense Tracker

// Voice greeting on dashboard load
if (window.location.pathname === '/dashboard') {
    window.addEventListener('load', function() {
        // Get username from the page
        const usernameElement = document.querySelector('h1');
        const username = usernameElement ? usernameElement.textContent.replace('Hello ', '') : 'User';

        // Speak the greeting
        const speech = new SpeechSynthesisUtterance(`Welcome ${username}, I am Nova. Press the AI chatbot button to add expenses automatically.`);
        window.speechSynthesis.speak(speech);
    });
}

// Handle manual expense form submission
const expenseForm = document.getElementById('expenseForm');
if (expenseForm) {
    expenseForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(expenseForm);
        const data = {
            date: formData.get('date'),
            category: formData.get('category'),
            description: formData.get('description'),
            amount: parseFloat(formData.get('amount')),
            payment_mode: formData.get('payment_mode'),
            entry_type: 'Manual'
        };

        fetch('/add_expense', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Expense added successfully!');
                location.reload(); // Refresh to show new expense
            } else {
                alert('Error adding expense.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error adding expense.');
        });
    });
}

// Function to delete expense
function deleteExpense(expenseId) {
    if (confirm('Are you sure you want to delete this expense?')) {
        fetch(`/delete_expense/${expenseId}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Expense deleted successfully!');
                location.reload(); // Refresh to update the table
            } else {
                alert('Error deleting expense.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting expense.');
        });
    }
}