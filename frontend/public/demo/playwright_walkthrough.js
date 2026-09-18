const { chromium } = require('playwright');

(async () => {
  // Launch the browser in non-headless mode so the user can watch the action
  const browser = await chromium.launch({ headless: false, slowMo: 4000 });
  const page = await browser.newPage();

  console.log('Navigating to local GST Portal simulation (Demo)...');
  await page.goto('http://localhost:3000/demo/index.html');

  // Verify dashboard view is active
  console.log('Verifying File Returns dashboard...');
  await page.waitForSelector('#dashboard-view.active');

  // --- Step 1: Run GSTR-2B Flow & Navigate to IMS ---
  console.log('Clicking the VIEW button on the GSTR-2B tile...');
  await page.click('#btn-view-gstr2b');

  console.log('Verifying GSTR-2B detailed statement is displayed...');
  await page.waitForSelector('#gstr2b-view.active');

  // Set dialog listener to handle the alert dialog on save
  page.on('dialog', async dialog => {
    console.log(`[Dialog Alert] Dismissing: "${dialog.message()}"`);
    await dialog.accept();
  });

  console.log('Clicking OPEN IMS DASHBOARD from GSTR-2B view...');
  await page.click('#btn-open-ims');

  console.log('Verifying IMS Dashboard view is active...');
  await page.waitForSelector('#ims-view.active');

  console.log('Checking initial IMS counts (Pending: 3)...');
  let pendingCount = await page.innerText('#ims-pending-action');
  console.log(`Initial IMS Pending Action Invoices: ${pendingCount}`);

  console.log('Accepting Invoice 1 (IGST ₹12,000.00)...');
  await page.click('#ims-row-1 .btn-accept');

  console.log('Accepting Invoice 2 (CGST/SGST ₹3,000.00 each)...');
  await page.click('#ims-row-2 .btn-accept');

  console.log('Rejecting Invoice 3 (CGST/SGST ₹3,000.00 each)...');
  await page.click('#ims-row-3 .btn-reject');

  console.log('Verifying updated IMS counts (Action Taken: 3, Pending: 0)...');
  let actionTaken = await page.innerText('#ims-action-taken');
  pendingCount = await page.innerText('#ims-pending-action');
  console.log(`IMS Action Taken: ${actionTaken}, Pending Action: ${pendingCount}`);

  console.log('Clicking SAVE ACTIONS...');
  await page.click('#btn-save-ims-actions');

  console.log('Returned to GSTR-2B detailed statement. Verifying dynamic calculations...');
  await page.waitForSelector('#gstr2b-view.active');

  // Verify GSTR-2B row values for ITC Available (Active Sub-tab)
  console.log('Checking GSTR-2B ITC Available sub-tab values...');
  await page.click('text=ITC available');
  let gstr2bIgst = await page.innerText('#gstr2b-itc-igst-val');
  let gstr2bCgst = await page.innerText('#gstr2b-itc-cgst-val');
  let gstr2bSgst = await page.innerText('#gstr2b-itc-sgst-val');
  console.log(`GSTR-2B ITC Available -> IGST: ₹${gstr2bIgst}, CGST: ₹${gstr2bCgst}, SGST: ₹${gstr2bSgst}`);

  // Verify GSTR-2B row values for ITC Rejected sub-tab
  console.log('Checking GSTR-2B ITC Rejected sub-tab values...');
  await page.click('text=ITC Rejected');
  let rejectedIgst = await page.innerText('#gstr2b-itc-igst-val');
  let rejectedCgst = await page.innerText('#gstr2b-itc-cgst-val');
  let rejectedSgst = await page.innerText('#gstr2b-itc-sgst-val');
  console.log(`GSTR-2B ITC Rejected -> IGST: ₹${rejectedIgst}, CGST: ₹${rejectedCgst}, SGST: ₹${rejectedSgst}`);

  // Click back to available
  await page.click('text=ITC available');

  // Move to GSTR-3B from GSTR-2B View
  console.log('Clicking OPEN GSTR-3B from GSTR-2B view...');
  await page.click('#btn-open-gstr3b');

  // --- Step 2: GSTR-3B Filing Questionnaire ---
  console.log('Arrived at GSTR-3B Questionnaire. Clicking NEXT...');
  await page.waitForSelector('#gstr3b-questionnaire.active');
  await page.click('#btn-next-questionnaire');

  // --- Step 3: GSTR-3B Prep Dashboard ---
  console.log('Arrived at GSTR-3B Prepare Dashboard. Scrolling down...');
  await page.waitForSelector('#gstr3b-prep.active');
  await page.evaluate(() => window.scrollBy(0, 400));
  
  console.log('Clicking PROCEED TO PAYMENT...');
  await page.click('#btn-proceed-to-payment');

  // --- Step 4: GSTR-3B Offset Liability / Payment ---
  console.log('Arrived at offset liability screen. Clicking MAKE PAYMENT...');
  await page.waitForSelector('#gstr3b-payment.active');
  await page.click('#btn-make-payment');

  console.log('Offset successful. Clicking PROCEED TO FILE...');
  await page.click('#btn-proceed-to-file');

  // --- Step 5: GSTR-3B Verification / Declaration ---
  console.log('Arrived at declaration screen. Checking checkbox...');
  await page.waitForSelector('#gstr3b-verification.active');
  await page.click('#declaration-check');

  console.log('Selecting authorized signatory...');
  await page.selectOption('#signatory-select', 'sign');

  console.log('Filing with EVC...');
  await page.click('#btn-file-evc');

  // --- Step 6: EVC OTP Modal ---
  console.log('OTP modal displayed. Typing 123456...');
  await page.waitForSelector('#otp-modal:not(.hidden)');
  await page.fill('#otp-input', '123456');

  console.log('Clicking VERIFY & FILE...');
  await page.click('#btn-verify-otp');

  // --- Step 7: GSTR-3B Success View ---
  console.log('Return filed successfully! Verifying Success Screen...');
  await page.waitForSelector('#gstr3b-success.active');

  console.log('Clicking BACK TO RETURNS DASHBOARD...');
  await page.click('#btn-success-close');

  // Verify back on dashboard and GSTR-3B shows Filed status
  await page.waitForSelector('#dashboard-view.active');
  const status = await page.innerText('#gstr3b-status-badge');
  console.log(`GSTR-3B final dashboard status is: ${status}`);

  // Close browser after a brief pause
  console.log('Walkthrough completed successfully! Closing browser...');
  await page.waitForTimeout(2000);
  await browser.close();
})();
