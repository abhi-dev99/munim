import os

filepath = 'frontend/src/app/components/SupplierHealth.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the outer container to force a fixed height so the table can scroll internally
old_outer = """    return (
      <div className="flex flex-col h-full w-full">
        <div className="sticky top-0 z-10 bg-[#f8fafc] pt-2 pb-4 space-y-4">"""

new_outer = """    return (
      <div className="flex flex-col h-[calc(100vh-120px)] w-full overflow-hidden">
        <div className="z-10 bg-[#f8fafc] pt-2 pb-4 space-y-4 flex-none">"""

if old_outer in content:
    content = content.replace(old_outer, new_outer)
else:
    print("WARNING: Outer container not found")

# 2. Update the table container to scroll internally
old_table = """        {/* Table */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">"""

new_table = """        {/* Table */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden flex-1 flex flex-col min-h-0 mb-4">
          <div className="overflow-auto flex-1">
            <table className="w-full text-sm border-collapse relative">
              <thead className="sticky top-0 z-20 bg-gray-50 shadow-sm">
                <tr className="border-b border-gray-100">"""

if old_table in content:
    content = content.replace(old_table, new_table)
else:
    print("WARNING: Table container not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SupplierHealth.js scrolling layout fixed")
