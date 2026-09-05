import os

filepath = 'frontend/src/app/dashboard/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_tour = """  const startTour = () => {
    const driverObj = driver({
      showProgress: true,
      steps: [
        { popover: { title: 'Welcome to the CA Dashboard', description: 'Let us show you around your new workspace.', side: "bottom", align: 'start' } },
        { element: '#money-meter-top', popover: { title: 'ITC Metrics', description: 'These are your core ITC metrics. You can drag and drop these cards to reorder them based on what you want to see first!', side: "bottom", align: 'start' } },
        { element: '#money-meter-bottom', popover: { title: 'Quick Stats', description: 'Track your processed invoices and open issues. These are also fully drag-and-drop enabled.', side: "bottom", align: 'start' } },
        { element: '#right-panel', popover: { title: 'Right Panel Widgets', description: 'All the widgets on the right panel of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' } },
        { element: '#sidebar-nav-suppliers', popover: { title: 'Supplier Trust', description: 'Navigate here to monitor the risk profiles of all your suppliers and prevent blocked ITC.', side: "right", align: 'start' } },
        { element: '#sidebar-nav-actions', popover: { title: 'Action Queue', description: 'Any discrepancies or blocked ITC that require your immediate attention will be queued here.', side: "right", align: 'start' } },
        { element: '#sidebar-my-profile', popover: { title: 'My Profile', description: 'Click here to manage your clients and send WhatsApp reminders for missing GSTINs.', side: "right", align: 'start' } }
      ]
    });
    driverObj.drive();
  };"""

new_tour = """  const startTour = () => {
    const driverObj = driver({
      showProgress: true,
      steps: [
        { 
          popover: { title: 'Welcome to the CA Dashboard', description: 'Let us show you around your new workspace.', side: "bottom", align: 'start' },
          onHighlightStarted: () => { setActiveTab("money-meter"); }
        },
        { 
          element: '#money-meter-top', 
          popover: { title: 'ITC Metrics', description: 'These are your core ITC metrics. You can drag and drop these cards to reorder them based on what you want to see first!', side: "bottom", align: 'start' } 
        },
        { 
          element: '#money-meter-bottom', 
          popover: { title: 'Quick Stats', description: 'Track your processed invoices and open issues. These are also fully drag-and-drop enabled.', side: "bottom", align: 'start' } 
        },
        { 
          element: '#right-panel', 
          popover: { title: 'Right Panel Widgets', description: 'All the widgets on the right panel of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' } 
        },
        { 
          element: '#sidebar-nav-suppliers', 
          popover: { title: 'Supplier Trust', description: 'Monitor the risk profiles of all your suppliers here. We categorize them by compliance health so you know who is causing blocked ITC.', side: "right", align: 'start' },
          onHighlightStarted: () => { setActiveTab("suppliers"); }
        },
        { 
          element: '#sidebar-nav-actions', 
          popover: { title: 'Action Queue', description: 'This is your triage center. Any discrepancies, mismatching invoices, or blocked ITC that require your immediate attention will be queued here.', side: "right", align: 'start' },
          onHighlightStarted: () => { setActiveTab("actions"); }
        },
        { 
          element: '#sidebar-nav-reports', 
          popover: { title: 'Monthly Reports', description: 'Generate comprehensive GSTR-2B reconciliation reports and instantly export them to PDF for your clients.', side: "right", align: 'start' },
          onHighlightStarted: () => { setActiveTab("reports"); }
        },
        { 
          element: '#sidebar-my-profile', 
          popover: { title: 'My Profile', description: 'Manage your personal CA details and configure automated WhatsApp reminders for missing GSTINs right from this panel.', side: "right", align: 'start' },
          onHighlightStarted: () => { router.push('/dashboard/profile'); }
        }
      ]
    });
    driverObj.drive();
  };"""

if old_tour in content:
    content = content.replace(old_tour, new_tour)
else:
    print("WARNING: Old tour not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched driver.js tour in dashboard/page.js")
