document.addEventListener('DOMContentLoaded', () => {
    const dashboardView = document.getElementById('dashboard-view');
    const gstr2bView = document.getElementById('gstr2b-view');
    const imsView = document.getElementById('ims-view');
    
    const btnViewGstr2b = document.getElementById('btn-view-gstr2b');
    const btnBack = document.getElementById('btn-back');
    const btnOpenIms = document.getElementById('btn-open-ims');
    const btnBackToDashboardIms = document.getElementById('btn-back-to-dashboard-ims');
    
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

    // Open IMS Dashboard from GSTR-2B view
    btnOpenIms.addEventListener('click', () => {
        showView(gstr2bView, imsView, 'Dashboard > Returns > <strong>Invoice Management System (IMS)</strong>');
    });

    // Back to Dashboard from IMS view
    btnBackToDashboardIms.addEventListener('click', () => {
        showView(imsView, dashboardView, 'Dashboard > Returns > <strong>Returns Dashboard</strong>');
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
        // Calculate dynamic offset based on accepted ITC vs liability
        let acceptedIGST = 0;
        let acceptedCGST = 0;
        let acceptedSGST = 0;
        
        inwardSupplies.forEach(inv => {
            if (inv.action === 'accept') {
                if (inv.type === 'IGST') {
                    acceptedIGST += inv.tax;
                } else if (inv.type === 'CGST_SGST') {
                    acceptedCGST += inv.tax / 2;
                    acceptedSGST += inv.tax / 2;
                }
            }
        });

        // IGST Offset: Liability = 12000
        const igstLiab = 12000;
        const igstPaidITC = Math.min(igstLiab, acceptedIGST);
        const igstBal = 0; // Balance payable is paid via cash, so balance becomes 0
        const igstPaidCash = igstLiab - igstPaidITC;

        // CGST Offset: Liability = 6000
        const cgstLiab = 6000;
        const cgstPaidITC = Math.min(cgstLiab, acceptedCGST);
        const cgstBal = 0;
        const cgstPaidCash = cgstLiab - cgstPaidITC;

        // SGST Offset: Liability = 6000
        const sgstLiab = 6000;
        const sgstPaidITC = Math.min(sgstLiab, acceptedSGST);
        const sgstBal = 0;
        const sgstPaidCash = sgstLiab - sgstPaidITC;

        // Cess Offset: Liability = 1500
        const cessLiab = 1500;
        const cessPaidITC = 0; // Cess ITC is 0
        const cessBal = 0;
        const cessPaidCash = cessLiab;

        document.getElementById('offset-igst-itc').innerText = `₹${igstPaidITC.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('offset-igst-bal').innerText = '₹0.00';
        document.getElementById('offset-igst-bal').style.color = '#00a65a';

        document.getElementById('offset-cgst-itc').innerText = `₹${cgstPaidITC.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('offset-cgst-bal').innerText = '₹0.00';
        document.getElementById('offset-cgst-bal').style.color = '#00a65a';

        document.getElementById('offset-sgst-itc').innerText = `₹${sgstPaidITC.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('offset-sgst-bal').innerText = '₹0.00';
        document.getElementById('offset-sgst-bal').style.color = '#00a65a';

        document.getElementById('offset-cess-itc').innerText = '₹0.00';
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
        btnProceedToFile.style.background = '#00a65a';
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

    // Inward Supplies State for IMS
    const inwardSupplies = [
        { id: 1, gstin: '24AAFCK2304M1ZP', name: 'Balaji Hardware', invNo: 'INV-2024-001', date: '05/04/2026', taxable: 66666.67, tax: 12000.00, type: 'IGST', action: 'pending' },
        { id: 2, gstin: '29UATYY9012A1Z8', name: 'Surat Textiles', invNo: 'TX-9988', date: '12/04/2026', taxable: 33333.33, tax: 6000.00, type: 'CGST_SGST', action: 'pending' },
        { id: 3, gstin: '29UATYY9012A1Z8', name: 'Surat Textiles', invNo: 'TX-9989', date: '15/04/2026', taxable: 33333.33, tax: 6000.00, type: 'CGST_SGST', action: 'pending' }
    ];

    let activeGstr2bSubTab = 'ITC available';

    // IMS elements
    const imsActionButtons = document.querySelectorAll('.btn-ims-action');
    const imsTotalInvoicesEl = document.getElementById('ims-total-invoices');
    const imsActionTakenEl = document.getElementById('ims-action-taken');
    const imsPendingActionEl = document.getElementById('ims-pending-action');
    const btnSaveImsActions = document.getElementById('btn-save-ims-actions');

    function updateImsCounters() {
        let actionTaken = 0;
        let pendingAction = 0;
        inwardSupplies.forEach(inv => {
            if (inv.action === 'pending') {
                pendingAction++;
            } else {
                actionTaken++;
            }
        });
        imsTotalInvoicesEl.innerText = inwardSupplies.length.toString();
        imsActionTakenEl.innerText = actionTaken.toString();
        imsPendingActionEl.innerText = pendingAction.toString();
    }

    imsActionButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const rowId = parseInt(e.target.getAttribute('data-row'));
            const action = e.target.getAttribute('data-action');
            
            // Update state
            const invoice = inwardSupplies.find(inv => inv.id === rowId);
            if (invoice) {
                invoice.action = action;
            }

            // Update buttons visually in the same row
            const row = document.getElementById(`ims-row-${rowId}`);
            const buttons = row.querySelectorAll('.btn-ims-action');
            buttons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');

            // Update status text and color class
            const statusTextEl = document.getElementById(`ims-status-${rowId}`);
            statusTextEl.className = 'ims-status-text'; // reset classes
            
            if (action === 'accept') {
                statusTextEl.innerText = 'Accepted';
                statusTextEl.classList.add('status-accepted');
            } else if (action === 'reject') {
                statusTextEl.innerText = 'Rejected';
                statusTextEl.classList.add('status-rejected');
            } else {
                statusTextEl.innerText = 'Pending';
                statusTextEl.classList.add('status-pending');
            }

            updateImsCounters();
        });
    });

    // Sub-tab selection in GSTR-2B view
    const subTabs = document.querySelectorAll('.sub-tabs .sub-tab');
    subTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            subTabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            activeGstr2bSubTab = e.target.textContent.trim();
            updateGstr2bTable();
        });
    });

    function updateGstr2bTable() {
        let igstVal = 0;
        let cgstVal = 0;
        let sgstVal = 0;
        let cessVal = 0;

        if (activeGstr2bSubTab === 'ITC available') {
            inwardSupplies.forEach(inv => {
                if (inv.action === 'accept') {
                    if (inv.type === 'IGST') {
                        igstVal += inv.tax;
                    } else if (inv.type === 'CGST_SGST') {
                        cgstVal += inv.tax / 2;
                        sgstVal += inv.tax / 2;
                    }
                }
            });
        } else if (activeGstr2bSubTab === 'ITC Rejected') {
            inwardSupplies.forEach(inv => {
                if (inv.action === 'reject') {
                    if (inv.type === 'IGST') {
                        igstVal += inv.tax;
                    } else if (inv.type === 'CGST_SGST') {
                        cgstVal += inv.tax / 2;
                        sgstVal += inv.tax / 2;
                    }
                }
            });
        }
        
        document.getElementById('gstr2b-itc-igst-val').innerText = igstVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById('gstr2b-itc-cgst-val').innerText = cgstVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById('gstr2b-itc-sgst-val').innerText = sgstVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById('gstr2b-itc-cess-val').innerText = cessVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Save IMS Actions
    btnSaveImsActions.addEventListener('click', () => {
        // Recalculate GSTR-2B
        updateGstr2bTable();

        // Calculate accepted totals for GSTR-3B propagation
        let acceptedIGST = 0;
        let acceptedCGST = 0;
        let acceptedSGST = 0;

        inwardSupplies.forEach(inv => {
            if (inv.action === 'accept') {
                if (inv.type === 'IGST') {
                    acceptedIGST += inv.tax;
                } else if (inv.type === 'CGST_SGST') {
                    acceptedCGST += inv.tax / 2;
                    acceptedSGST += inv.tax / 2;
                }
            }
        });

        // Propagate to GSTR-3B Prep Dashboard Table 4
        document.getElementById('gstr3b-itc-igst').innerText = `₹${acceptedIGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('gstr3b-itc-cgst').innerText = `₹${acceptedCGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('gstr3b-itc-sgst').innerText = `₹${acceptedSGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('gstr3b-itc-cess').innerText = '₹0.00';

        // Propagate to GSTR-3B Payment Ledger
        document.getElementById('credit-igst').innerText = `₹${acceptedIGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('credit-cgst').innerText = `₹${acceptedCGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('credit-sgst').innerText = `₹${acceptedSGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById('credit-cess').innerText = '₹0.00';

        // Reset offset table display to reflect new inputs
        document.getElementById('offset-igst-itc').innerText = '₹0.00';
        document.getElementById('offset-igst-bal').innerText = '₹12,000.00';
        document.getElementById('offset-igst-bal').style.color = 'red';

        document.getElementById('offset-cgst-itc').innerText = '₹0.00';
        document.getElementById('offset-cgst-bal').innerText = '₹6,000.00';
        document.getElementById('offset-cgst-bal').style.color = 'red';

        document.getElementById('offset-sgst-itc').innerText = '₹0.00';
        document.getElementById('offset-sgst-bal').innerText = '₹6,000.00';
        document.getElementById('offset-sgst-bal').style.color = 'red';

        document.getElementById('offset-cess-itc').innerText = '₹0.00';
        document.getElementById('offset-cess-bal').innerText = '₹1,500.00';
        document.getElementById('offset-cess-bal').style.color = 'red';

        // Reset the Make Payment button
        btnMakePayment.innerText = 'MAKE PAYMENT / POST CREDIT TO LEDGER';
        btnMakePayment.disabled = false;
        btnMakePayment.style.background = '#2b5299';
        btnMakePayment.style.cursor = 'pointer';

        // Disable file button until offset clicked
        btnProceedToFile.disabled = true;
        btnProceedToFile.classList.add('disabled');
        btnProceedToFile.style.cursor = 'not-allowed';
        btnProceedToFile.style.background = '#ccc';

        alert('Actions saved successfully! GSTR-2B and GSTR-3B values have been updated based on your actions.');

        // Automatically show GSTR-2B view to proceed
        showView(imsView, gstr2bView, 'Dashboard > Returns > <strong>GSTR-2B</strong>');
    });

    // Initialize IMS state colors
    inwardSupplies.forEach(inv => {
        const statusTextEl = document.getElementById(`ims-status-${inv.id}`);
        statusTextEl.classList.add('status-pending');
        
        // Find default active pending buttons and style them
        const row = document.getElementById(`ims-row-${inv.id}`);
        const pendBtn = row.querySelector('.btn-pending');
        if (pendBtn) pendBtn.classList.add('active');
    });
    updateImsCounters();
    updateGstr2bTable();
});




