document.addEventListener('DOMContentLoaded', () => {
    const dashboardView = document.getElementById('dashboard-view');
    const gstr2bView = document.getElementById('gstr2b-view');
    
    const btnViewGstr2b = document.getElementById('btn-view-gstr2b');
    const btnBack = document.getElementById('btn-back');
    const breadcrumbText = document.querySelector('.breadcrumb');
    const quarterSelect = document.getElementById('quarter-select');
    const periodSelect = document.getElementById('period-select');

    const quarterToMonths = {
        Q1: ['April', 'May', 'June'],
        Q2: ['July', 'August', 'September'],
        Q3: ['October', 'November', 'December'],
        Q4: ['January', 'February', 'March']
    };

    quarterSelect.addEventListener('change', (e) => {
        const selectedQuarter = e.target.value;
        const months = quarterToMonths[selectedQuarter] || [];
        periodSelect.innerHTML = '';
        months.forEach(month => {
            const option = document.createElement('option');
            option.value = month;
            option.textContent = month;
            periodSelect.appendChild(option);
        });
    });

    // Show GSTR-2B View
    btnViewGstr2b.addEventListener('click', () => {
        dashboardView.classList.remove('active');
        dashboardView.classList.add('hidden');
        
        gstr2bView.classList.remove('hidden');
        gstr2bView.classList.add('active');
        
        // Update breadcrumb visually if needed, though the static one already says GSTR-2B
        breadcrumbText.innerHTML = 'Dashboard > Returns > <strong>GSTR-2B</strong>';
    });

    // Back to Dashboard
    btnBack.addEventListener('click', () => {
        gstr2bView.classList.remove('active');
        gstr2bView.classList.add('hidden');
        
        dashboardView.classList.remove('hidden');
        dashboardView.classList.add('active');
        
        breadcrumbText.innerHTML = 'Dashboard > Returns > <strong>Returns Dashboard</strong>';
    });

    // Optional: Add some interactivity to tabs just for demo purposes
    const mainTabs = document.querySelectorAll('.main-tabs .tab');
    mainTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            mainTabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
        });
    });

    const subTabs = document.querySelectorAll('.sub-tabs .sub-tab');
    subTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            subTabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
        });
    });
});
