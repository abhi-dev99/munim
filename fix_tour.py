import os

# 1. Update Sidebar.js to inject IDs for the tour
sidebar_path = 'frontend/src/app/components/Sidebar.js'
with open(sidebar_path, 'r', encoding='utf-8') as f:
    sidebar_content = f.read()

# The nav items are mapped over here:
old_nav_button = """<button
              key={item.id}
              onClick={() => onSwitchTab(item.id)}"""
new_nav_button = """<button
              key={item.id}
              id={`sidebar-nav-${item.id}`}
              onClick={() => onSwitchTab(item.id)}"""

if old_nav_button in sidebar_content:
    sidebar_content = sidebar_content.replace(old_nav_button, new_nav_button)

# The profile button:
old_profile_button = """className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full text-sm font-semibold ${pathname === "/dashboard/profile" ? "bg-emerald-50 text-emerald-600 font-bold" : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"}`}'"""
# It might not match exactly, let's use replace instead
sidebar_content = sidebar_content.replace('onClick={() => router.push("/dashboard/profile")}', 'id="sidebar-my-profile"\n            onClick={() => router.push("/dashboard/profile")}')

with open(sidebar_path, 'w', encoding='utf-8') as f:
    f.write(sidebar_content)


# 2. Update dashboard/page.js
dashboard_path = 'frontend/src/app/dashboard/page.js'
with open(dashboard_path, 'r', encoding='utf-8') as f:
    dashboard_content = f.read()

# Add ID to right panel container
old_right_rail = """<div className="hidden lg:flex w-80 flex-col bg-white border-l border-gray-200">"""
new_right_rail = """<div id="right-panel" className="hidden lg:flex w-80 flex-col bg-white border-l border-gray-200">"""
if old_right_rail in dashboard_content:
    dashboard_content = dashboard_content.replace(old_right_rail, new_right_rail)

# Update driver.js tour steps
old_tour = """  const startTour = () => {
    const driverObj = driver({
      showProgress: true,
      steps: [
        { popover: { title: 'Welcome to the CA Dashboard', description: 'Let us show you around your new workspace.', side: "bottom", align: 'start' } },
        { element: '#money-meter-top', popover: { title: 'ITC Metrics', description: 'These are your core ITC metrics. You can drag and drop these cards to reorder them based on what you want to see first!', side: "bottom", align: 'start' } },
        { element: '#money-meter-bottom', popover: { title: 'Quick Stats', description: 'Track your processed invoices and open issues. These are also fully drag-and-drop enabled.', side: "bottom", align: 'start' } },
        { popover: { title: 'Right Rail Widgets', description: 'All the widgets on the right side of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' } }
      ]
    });
    driverObj.drive();
  };"""

new_tour = """  const startTour = () => {
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

if old_tour in dashboard_content:
    dashboard_content = dashboard_content.replace(old_tour, new_tour)

with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(dashboard_content)

print("Tour patched.")
