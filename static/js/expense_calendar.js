/* ===== EXPENSE CALENDAR SCRIPT ===== */

document.addEventListener('DOMContentLoaded', function() {
    initCalendar();
    setupModalHandlers();
});

// Initialize FullCalendar
function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        height: 'auto',
        events: function(info, successCallback, failureCallback) {
            fetch('/calendar-data')
                .then(res => res.json())
                .then(data => {
                    // Add amount to extendedProps for eventDidMount callback
                    const coloredEvents = data.map(event => {
                        return {
                            ...event,
                            extendedProps: {
                                amount: event.amount
                            }
                        };
                    });
                    
                    successCallback(coloredEvents);
                })
                .catch(err => {
                    console.error('Error fetching calendar data:', err);
                    failureCallback(err);
                });
        },
        eventDidMount: function(info) {
            // Apply colors dynamically based on amount during initial render and re-renders
            const amount = info.event.extendedProps.amount;
            let bgColor = '#d4edda'; // Light Green (₹0-₹200)
            let textColor = '#155724'; // Dark green text
            
            if (amount > 700) {
                bgColor = '#f8d7da'; // Dark Red (₹701+)
                textColor = '#721c24'; // Dark red text
            } else if (amount > 200) {
                bgColor = '#ffe5b4'; // Orange (₹201-₹700)
                textColor = '#b8860b'; // Dark orange text
            }
            
            // Apply styles directly to the event element with !important to override CSS
            const eventElement = info.el.querySelector('.fc-event-main') || info.el;
            eventElement.style.setProperty('background-color', bgColor, 'important');
            info.el.style.borderColor = bgColor;
            info.el.style.color = textColor;
            info.el.style.fontSize = '0.85rem';
            info.el.style.fontWeight = '500';
            
            // Remove or minimize border
            if (info.el.style.border) {
                info.el.style.border = 'none';
            }
            
            // Apply smooth hover effect - slightly darken color
            info.el.addEventListener('mouseenter', function() {
                this.style.opacity = '0.8';
                this.style.transform = 'scale(1.02)';
                this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
            });
            
            info.el.addEventListener('mouseleave', function() {
                this.style.opacity = '1';
                this.style.transform = 'scale(1)';
                this.style.boxShadow = 'none';
            });
        },
        eventClick: function(info) {
            handleDateClick(info.event.startStr);
        },
        dateClick: function(info) {
            handleDateClick(info.dateStr);
        }
    });
    
    calendar.render();
}

// Handle date click and show modal
function handleDateClick(dateStr) {
    fetch(`/calendar-day-details/${dateStr}`)
        .then(res => res.json())
        .then(data => {
            showExpenseModal(dateStr, data);
        })
        .catch(err => {
            console.error('Error fetching day details:', err);
            showExpenseModal(dateStr, []);
        });
}

// Display modal with expense details
function showExpenseModal(dateStr, expenses) {
    const modal = document.getElementById('expenseModal');
    const modalDate = document.getElementById('modalDate');
    const expensesList = document.getElementById('expensesList');
    const totalSpent = document.getElementById('totalSpent');
    
    // Format date
    const date = new Date(dateStr + 'T00:00:00');
    const formattedDate = date.toLocaleDateString('en-IN', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    modalDate.textContent = formattedDate;
    
    // Clear and populate expenses
    expensesList.innerHTML = '';
    let total = 0;
    
    if (expenses.length === 0) {
        expensesList.innerHTML = '<div class="no-expenses">No expenses recorded for this date.</div>';
        totalSpent.innerHTML = '';
    } else {
        expenses.forEach(exp => {
            const item = document.createElement('div');
            item.className = 'expense-item';
            item.innerHTML = `
                <span class="expense-description">${exp.description}</span>
                <span class="expense-amount">₹${exp.amount.toFixed(2)}</span>
            `;
            expensesList.appendChild(item);
            total += exp.amount;
        });
        
        totalSpent.innerHTML = `<strong>Total Spent: ₹${total.toFixed(2)}</strong>`;
    }
    
    modal.classList.add('show');
}

// Modal handlers
function setupModalHandlers() {
    const modal = document.getElementById('expenseModal');
    const closeBtn = document.querySelector('.close');
    const closeBtn2 = document.querySelector('.modal-close-btn');
    
    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
    closeBtn2.addEventListener('click', () => modal.classList.remove('show'));
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
}
