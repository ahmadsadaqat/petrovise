import frappe

def execute():
    if frappe.db.exists("DocType", "Fuel Station"):
        print("Fuel Station DocType already exists")
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "module": "Petrovise",
        "custom": 0,
        "name": "Fuel Station",
        "autoname": "FS-.####",
        "naming_rule": "Expression",
        "is_submittable": 0,
        "fields": [
            {
                "fieldname": "station_name",
                "fieldtype": "Data",
                "label": "Name",
                "reqd": 1,
                "in_list_view": 1
            },
            {
                "fieldname": "customer",
                "fieldtype": "Link",
                "label": "Customer",
                "options": "Customer"
            },
            {
                "fieldname": "column_break_1",
                "fieldtype": "Column Break"
            },
            {
                "fieldname": "area_location",
                "fieldtype": "Data",
                "label": "Area Location"
            },
            {
                "fieldname": "city",
                "fieldtype": "Data",
                "label": "City"
            },
            {
                "fieldname": "section_break_1",
                "fieldtype": "Section Break",
                "label": "Location & Stock Limits"
            },
            {
                "fieldname": "coordinates",
                "fieldtype": "Geolocation",
                "label": "Coordinates"
            },
            {
                "fieldname": "column_break_2",
                "fieldtype": "Column Break"
            },
            {
                "fieldname": "minimum_stock",
                "fieldtype": "Float",
                "label": "Minimum Stock"
            },
            {
                "fieldname": "lead_time",
                "fieldtype": "Float",
                "label": "Lead Time (Days)"
            },
            {
                "fieldname": "credit_limit",
                "fieldtype": "Currency",
                "label": "Credit Limit"
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1
            },
            {
                "role": "Petrovise ASM",
                "read": 1
            },
            {
                "role": "Petrovise Finance",
                "read": 1
            }
        ]
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Fuel Station DocType created successfully")
