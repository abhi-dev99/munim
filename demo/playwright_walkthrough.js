const { chromium } = require('playwright');

(async () => {
  // Launch the browser in non-headless mode so the user can watch the action
  const browser = await chromium.launch({ headless: false, slowMo: 1500 });
  const page = await browser.newPage();

  console.log('Navigating to local GST Portal simulation...');
  await page.goto('http://localhost:3000');

  // Verify dashboard view is active
  console.log('Verifying File Returns dashboard...');
  await page.waitForSelector('#dashboard-view.active');

  // Click on GSTR-2B VIEW button
  console.log('Clicking the VIEW button on the GSTR-2B tile...');
  await page.click('#btn-view-gstr2b');

  // Verify GSTR-2B view is active
  console.log('Verifying GSTR-2B detailed statement is displayed...');
  await page.waitForSelector('#gstr2b-view.active');

  // Click on the different sub-tabs to demonstrate functionality
  console.log('Clicking through GSTR-2B sub-tabs...');
  
  console.log('Selecting "ITC Not Available" sub-tab...');
  await page.click('text=ITC Not Available');
  
  console.log('Selecting "ITC Reversal" sub-tab...');
  await page.click('text=ITC Reversal');
  
  console.log('Selecting "ITC Rejected" sub-tab...');
  await page.click('text=ITC Rejected');

  console.log('Selecting "ITC available" sub-tab...');
  await page.click('text=ITC available');

  // Click BACK TO DASHBOARD button
  console.log('Clicking "BACK TO DASHBOARD" to return...');
  await page.click('#btn-back');

  // Verify back on dashboard
  await page.waitForSelector('#dashboard-view.active');
  console.log('Successfully returned to the main dashboard.');

  // Close browser after a brief pause
  console.log('Walkthrough completed successfully! Closing browser...');
  await page.waitForTimeout(2000);
  await browser.close();
})();
