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

    // Elements for GSTR-3B Views
    const gstr3bQuestionnaire = document.getElementById('gstr3b-questionnaire');
    const gstr3bPrep = document.getElementById('gstr3b-prep');
    const gstr3bPayment = document.getElementById('gstr3b-payment');
    const gstr3bVerification = document.getElementById('gstr3b-verification');
    const gstr3bSuccess = document.getElementById('gstr3b-success');
    const otpModal = document.getElementById('otp-modal');

    const btnOpenGstr3b = document.getElementById('btn-open-gstr3b');
    const btnPrepGstr3b = document.getElementById('btn-prep-gstr3b');
    const btnCancelQuestionnaire = document.getElementById('btn-cancel-questionnaire');
    const btnNextQuestionnaire = document.getElementById('btn-next-questionnaire');
    const btnBackToDashboard3b = document.getElementById('btn-back-to-dashboard-3b');
    const btnProceedToPayment = document.getElementById('btn-proceed-to-payment');
    const btnBackToPrep = document.getElementById('btn-back-to-prep');
    const btnMakePayment = document.getElementById('btn-make-payment');
    const btnProceedToFile = document.getElementById('btn-proceed-to-file');
    const btnBackToPayment = document.getElementById('btn-back-to-payment');
    
    const declarationCheck = document.getElementById('declaration-check');
    const signatorySelect = document.getElementById('signatory-select');
    const btnFileDsc = document.getElementById('btn-file-dsc');
    const btnFileEvc = document.getElementById('btn-file-evc');
    
    const btnCancelOtp = document.getElementById('btn-cancel-otp');
    const btnVerifyOtp = document.getElementById('btn-verify-otp');
    const otpInput = document.getElementById('otp-input');
    const otpError = document.getElementById('otp-error');
    
    const btnSuccessClose = document.getElementById('btn-success-close');
    const gstr3bStatusBadge = document.getElementById('gstr3b-status-badge');

    // Navigation helper
    const showView = (from, to, breadcrumb) => {
        from.classList.remove('active');
        from.classList.add('hidden');
        to.classList.remove('hidden');
        to.classList.add('active');
        if (breadcrumb) {
            breadcrumbText.innerHTML = breadcrumb;
        }
    };

    // Open GSTR-3B from GSTR-2B view
    btnOpenGstr3b.addEventListener('click', () => {
        showView(gstr2bView, gstr3bQuestionnaire, 'Dashboard > Returns > <strong>GSTR-3B Questionnaire</strong>');
    });

    // Open GSTR-3B from Dashboard
    btnPrepGstr3b.addEventListener('click', () => {
        showView(dashboardView, gstr3bQuestionnaire, 'Dashboard > Returns > <strong>GSTR-3B Questionnaire</strong>');
    });

    // Cancel Questionnaire
    btnCancelQuestionnaire.addEventListener('click', () => {
        showView(gstr3bQuestionnaire, dashboardView, 'Dashboard > Returns > <strong>Returns Dashboard</strong>');
    });

    // Next Questionnaire
    btnNextQuestionnaire.addEventListener('click', () => {
        showView(gstr3bQuestionnaire, gstr3bPrep, 'Dashboard > Returns > <strong>GSTR-3B Prepare</strong>');
    });

    // Back to Dashboard from Prep
    btnBackToDashboard3b.addEventListener('click', () => {
        showView(gstr3bPrep, dashboardView, 'Dashboard > Returns > <strong>Returns Dashboard</strong>');
    });

    // Proceed to Payment
    btnProceedToPayment.addEventListener('click', () => {
        showView(gstr3bPrep, gstr3bPayment, 'Dashboard > Returns > <strong>GSTR-3B Payment</strong>');
    });

    // Back to Prep from Payment
    btnBackToPrep.addEventListener('click', () => {
        showView(gstr3bPayment, gstr3bPrep, 'Dashboard > Returns > <strong>GSTR-3B Prepare</strong>');
    });

    // Offset Math Logic
    btnMakePayment.addEventListener('click', () => {
        document.getElementById('offset-igst-itc').innerText = '₹12,000.00';
        document.getElementById('offset-igst-bal').innerText = '₹0.00';
        document.getElementById('offset-igst-bal').style.color = '#00a65a';

        document.getElementById('offset-cgst-itc').innerText = '₹6,000.00';
        document.getElementById('offset-cgst-bal').innerText = '₹0.00';
        document.getElementById('offset-cgst-bal').style.color = '#00a65a';

        document.getElementById('offset-sgst-itc').innerText = '₹6,000.00';
        document.getElementById('offset-sgst-bal').innerText = '₹0.00';
        document.getElementById('offset-sgst-bal').style.color = '#00a65a';

        document.getElementById('offset-cess-itc').innerText = '₹1,500.00';
        document.getElementById('offset-cess-bal').innerText = '₹0.00';
        document.getElementById('offset-cess-bal').style.color = '#00a65a';

        btnMakePayment.innerText = 'LIABILITY OFFSET SUCCESSFUL';
        btnMakePayment.disabled = true;
        btnMakePayment.style.background = '#ccc';
        btnMakePayment.style.cursor = 'not-allowed';

        // Enable Proceed to File button
        btnProceedToFile.disabled = false;
        btnProceedToFile.classList.remove('disabled');
        btnProceedToFile.style.cursor = 'pointer';
    });

    // Proceed to File
    btnProceedToFile.addEventListener('click', () => {
        showView(gstr3bPayment, gstr3bVerification, 'Dashboard > Returns > <strong>GSTR-3B Verification</strong>');
    });

    // Back to Payment from Verification
    btnBackToPayment.addEventListener('click', () => {
        showView(gstr3bVerification, gstr3bPayment, 'Dashboard > Returns > <strong>GSTR-3B Payment</strong>');
    });

    // Enable/Disable filing buttons based on verification checkbox and signatory select
    const toggleFilingButtons = () => {
        const isChecked = declarationCheck.checked;
        const hasSignatory = signatorySelect.value !== '';
        if (isChecked && hasSignatory) {
            btnFileEvc.disabled = false;
            btnFileEvc.classList.remove('disabled');
            btnFileEvc.style.background = '#00a65a';
            btnFileEvc.style.cursor = 'pointer';
        } else {
            btnFileEvc.disabled = true;
            btnFileEvc.classList.add('disabled');
            btnFileEvc.style.background = '#ccc';
            btnFileEvc.style.cursor = 'not-allowed';
        }
    };

    declarationCheck.addEventListener('change', toggleFilingButtons);
    signatorySelect.addEventListener('change', toggleFilingButtons);

    // EVC filing modal trigger
    btnFileEvc.addEventListener('click', () => {
        otpModal.classList.remove('hidden');
    });

    // Cancel EVC OTP modal
    btnCancelOtp.addEventListener('click', () => {
        otpModal.classList.add('hidden');
        otpError.classList.add('hidden');
        otpInput.value = '';
    });

    // Verify OTP
    btnVerifyOtp.addEventListener('click', () => {
        if (otpInput.value === '123456') {
            otpModal.classList.add('hidden');
            
            // Format today's date for GSTR-3B success screen
            const today = new Date();
            const dd = String(today.getDate()).padStart(2, '0');
            const mm = String(today.getMonth() + 1).padStart(2, '0');
            const yyyy = today.getFullYear();
            document.getElementById('current-filing-date').innerText = `${dd}/${mm}/${yyyy}`;

            showView(gstr3bVerification, gstr3bSuccess, 'Dashboard > Returns > <strong>GSTR-3B Filed</strong>');
        } else {
            otpError.classList.remove('hidden');
        }
    });

    // Back to dashboard after success
    btnSuccessClose.addEventListener('click', () => {
        showView(gstr3bSuccess, dashboardView, 'Dashboard > Returns > <strong>Returns Dashboard</strong>');
        
        // Update dashboard GSTR-3B status to Filed
        gstr3bStatusBadge.innerText = 'Filed';
        gstr3bStatusBadge.style.color = '#00a65a';
        btnPrepGstr3b.disabled = true;
        btnPrepGstr3b.style.background = '#ccc';
        btnPrepGstr3b.style.cursor = 'not-allowed';
        btnPrepGstr3b.innerText = 'FILED';
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
