

document.addEventListener('DOMContentLoaded', function() {
    initCalendar();
    setupModalHandlers();
});


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
           
            const amount = info.event.extendedProps.amount;
            let bgColor = '#d4edda'; 
            let textColor = '#155724'; 
            
            if (amount > 700) {
                bgColor = '#f8d7da';
                textColor = '#721c24'; 
            } else if (amount > 200) {
                bgColor = '#ffe5b4'; 
                textColor = '#b8860b';
            }
            
          
            const eventElement = info.el.querySelector('.fc-event-main') || info.el;
            eventElement.style.setProperty('background-color', bgColor, 'important');
            info.el.style.borderColor = bgColor;
            info.el.style.color = textColor;
            info.el.style.fontSize = '0.85rem';
            info.el.style.fontWeight = '500';
            
           
            if (info.el.style.border) {
                info.el.style.border = 'none';
            }
            
            
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


function showExpenseModal(dateStr, expenses) {
    const modal = document.getElementById('expenseModal');
    const modalDate = document.getElementById('modalDate');
    const expensesList = document.getElementById('expensesList');
    const totalSpent = document.getElementById('totalSpent');
    
   
    const date = new Date(dateStr + 'T00:00:00');
    const formattedDate = date.toLocaleDateString('en-IN', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    modalDate.textContent = formattedDate;
    
  
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
