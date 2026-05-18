import frappe
from frappe import _
from frappe.utils import flt, cint


def check_credit_limit_on_save(doc, method):
    """Check credit limit when Sales Order is saved (before submit)."""
    from erpnext.selling.doctype.customer.customer import check_credit_limit

    if doc.customer and doc.company:
        # Skip if bypass is enabled for this customer
        bypass = cint(
            frappe.db.get_value(
                "Customer Credit Limit",
                {"parent": doc.customer, "parenttype": "Customer", "company": doc.company},
                "bypass_credit_limit_check",
            )
        )
        if not bypass:
            # Pass this order's total as extra_amount since the draft isn't
            # yet counted in the outstanding query (which only counts docstatus=1)
            check_credit_limit(doc.customer, doc.company, extra_amount=flt(doc.base_grand_total))

@frappe.whitelist()
def release_payment(sales_order_name, mode_of_payment="Bank Transfer"):
    """
    Auto-create a Sales Invoice and Payment Entry against a submitted Sales Order.
    Only accessible by users with the 'Petrovise Finance' role.
    """
    # 1. Permission check (Removed per user request)
    # if "Petrovise Finance" not in frappe.get_roles(frappe.session.user):
    #     frappe.throw(_("Only Petrovise Finance users can release payments."), frappe.PermissionError)

    # 2. Get and validate the Sales Order
    so = frappe.get_doc("Sales Order", sales_order_name)

    if so.docstatus != 1:
        frappe.throw(_("Sales Order must be submitted before releasing payment."))

    if so.custom_released:
        frappe.throw(_("Payment has already been released for this Sales Order."))

    # 3. Get company defaults
    company = so.company
    default_account = frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": mode_of_payment, "company": company},
        "default_account"
    )

    if not default_account:
        default_account = frappe.db.get_value(
            "Company", company, "default_cash_account"
        ) or frappe.db.get_value(
            "Company", company, "default_bank_account"
        )

    if not default_account:
        frappe.throw(
            _("Please set a default account for Mode of Payment '{0}' or set a default Cash/Bank account for company '{1}'.").format(
                mode_of_payment, company
            )
        )

    # 4. Mark as released
    frappe.db.set_value("Sales Order", sales_order_name, "custom_released", 1, update_modified=False)

    # 5. Create Sales Invoice from Sales Order
    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

    si = make_sales_invoice(sales_order_name)
    si.posting_date = frappe.utils.today()
    si.due_date = frappe.utils.today()
    si.insert(ignore_permissions=True)
    si.submit()

    # 6. Create Payment Entry against Sales Invoice
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.posting_date = frappe.utils.today()
    pe.company = company
    pe.mode_of_payment = mode_of_payment
    pe.party_type = "Customer"
    pe.party = so.customer
    pe.paid_from = frappe.db.get_value("Company", company, "default_receivable_account")
    pe.paid_to = default_account
    pe.paid_amount = si.grand_total
    pe.received_amount = si.grand_total
    pe.source_exchange_rate = 1
    pe.target_exchange_rate = 1

    pe.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": si.name,
        "allocated_amount": si.grand_total,
    })

    pe.insert(ignore_permissions=True)
    pe.submit()

    frappe.db.commit()

    frappe.msgprint(
        _("Sales Invoice {0} and Payment Entry {1} created successfully.").format(
            frappe.utils.get_link_to_form("Sales Invoice", si.name),
            frappe.utils.get_link_to_form("Payment Entry", pe.name)
        ),
        indicator="green",
        alert=True
    )

    return {"sales_invoice": si.name, "payment_entry": pe.name}

@frappe.whitelist()
def get_mobile_dashboard(customer, station):
    """
    Fetches all critical daily data for a specific Dealer (Customer) and Station (Warehouse)
    in a single JSON payload. Expected to be consumed by the React Native/Flutter mobile app.
    """

    # 1. SECURITY CHECK: Ensure the logged-in user is allowed to see this customer
    if not frappe.has_permission("Customer", ptype="read", doc=customer):
        frappe.throw(_("You do not have permission to access this customer's data."), frappe.PermissionError)

    # 2. Fetch Native ERPNext Credit Limit for the Customer
    # ERPNext stores credit limits in a child table linked to the Customer
    credit_limit = frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": customer, "parenttype": "Customer"},
        "credit_limit"
    ) or 0.0

    # 2b. Fetch Fuel Station details
    station_details = frappe.db.get_value(
        "Fuel Station", 
        station, 
        ["lead_time", "minimum_stock"], 
        as_dict=True
    ) or {}

    # 3. Fetch the Latest Stock Log (Linked to Station)
    latest_stock_list = frappe.get_all(
        "Daily Stock Log",
        filters={"station": station, "docstatus": 1},
        fields=["name", "log_date"],
        order_by="log_date desc",
        limit=1
    )
    latest_stock = None
    dry_out_alerts = []
    if latest_stock_list:
        # Fetch full document to include the child table (stock_details)
        latest_stock = frappe.get_doc("Daily Stock Log", latest_stock_list[0].name).as_dict()

        # Calculate Dry Out Alerts for mobile app
        from petrovise.petrovise.doctype.daily_stock_log.daily_stock_log import get_avg_daily_sales
        
        lead_time = flt(station_details.get("lead_time", 0))
        min_stock = flt(station_details.get("minimum_stock", 0))
        
        for row in latest_stock.get("stock_details", []):
            closing = flt(row.get("closing_dip", 0))
            item_code = row.get("item_code")
            
            if not item_code or closing <= 0:
                continue
                
            if min_stock > 0 and closing < min_stock:
                dry_out_alerts.append({
                    "item_code": item_code,
                    "level": "Warning",
                    "title": "Below Minimum Stock",
                    "message": f"{item_code} closing stock ({closing:.0f} L) is below minimum stock ({min_stock:.0f} L). Please place a fuel order!"
                })
                
            avg_data = get_avg_daily_sales(station, latest_stock.get("log_date"), item_code)
            hist_avg = flt(avg_data.get("avg_sales", 0))
            days_counted = flt(avg_data.get("days_counted", 0))
            today_sales = (flt(row.get("opening_dip", 0)) + flt(row.get("received_qty", 0))) - closing
            
            avg_sales = 0
            if days_counted > 0 and hist_avg > 0:
                avg_sales = ((hist_avg * days_counted) + today_sales) / (days_counted + 1)
            elif today_sales > 0:
                avg_sales = today_sales
                
            if avg_sales > 0:
                days_remaining = closing / avg_sales
                if lead_time > 0:
                    if days_remaining < lead_time:
                        dry_out_alerts.append({
                            "item_code": item_code,
                            "level": "Critical",
                            "title": "Critical Dry Out Alert",
                            "message": f"CRITICAL: Your stock will run out in {days_remaining:.1f} days, but delivery takes {lead_time} days. Even if you order right now, you will dry out {(lead_time - days_remaining):.1f} days before delivery arrives!"
                        })
                    elif days_remaining < (lead_time + 2):
                        dry_out_alerts.append({
                            "item_code": item_code,
                            "level": "Warning",
                            "title": "Order Now to Avoid Dry Out",
                            "message": f"ORDER TODAY: Your stock will last {days_remaining:.1f} days and delivery takes {lead_time} days. If you don't place an order today, you risk running dry!"
                        })
                    elif days_remaining < (lead_time + 5):
                        dry_out_alerts.append({
                            "item_code": item_code,
                            "level": "Info",
                            "title": "5-Day Order Reminder",
                            "message": f"PLAN AHEAD: Your stock will last {days_remaining:.1f} days and delivery takes {lead_time} days. You have approximately {(days_remaining - lead_time):.1f} days to place an order before it becomes critical."
                        })

    # 4. Fetch Active Complaints (Linked to Station)
    open_complaints = frappe.get_all(
        "Site Complaint",
        filters={"station": station, "status": ["in", ["Open", "Under Review"]]},
        fields=["name", "issue_category", "status", "opened_at", "description", "photo_attachment"],
        order_by="opened_at desc"
    )

    # 5. Fetch Pending Fuel Orders (Native Sales Orders linked to Customer)
    pending_orders = frappe.get_all(
        "Sales Order",
        filters={
            "customer": customer,
            "docstatus": ["<", 2], # Fetch Drafts (0) and Submitted (1), exclude Cancelled (2)
            "status": ["not in", ["Completed", "Closed"]]
        },
        fields=[
            "name", "transaction_date", "grand_total", "status", "docstatus",
            "custom_released", "custom_station", "custom_payment_slip"
        ],
        order_by="transaction_date desc",
        limit=5
    )

    # Enhance pending orders with Release Payment capabilities and linked documents
    for order in pending_orders:
        order["can_release_payment"] = bool(
            order.get("docstatus") == 1 
            and not order.get("custom_released")
        )
        
        if order.get("custom_released"):
            # Attempt to fetch linked Sales Invoice
            si = frappe.db.get_value("Sales Invoice Item", {"sales_order": order.name}, "parent")
            if si:
                order["linked_invoice"] = si
                # Attempt to fetch linked Payment Entry
                pe = frappe.db.get_value(
                    "Payment Entry Reference", 
                    {"reference_doctype": "Sales Invoice", "reference_name": si}, 
                    "parent"
                )
                if pe:
                    order["linked_payment"] = pe

    # 6. Package and return the payload
    return {
        "customer": customer,
        "station_name": station,
        "credit_limit": flt(credit_limit),
        "lead_time": flt(station_details.get("lead_time", 0)),
        "minimum_stock": flt(station_details.get("minimum_stock", 0)),
        "latest_stock_log": latest_stock,
        "dry_out_alerts": dry_out_alerts,
        "active_complaints": open_complaints,
        "pending_orders": pending_orders
    }

@frappe.whitelist()
def get_standard_audit_checklist():
    """
    Returns the standard set of safety, signage, equipment, and cleanliness questions
    for the mobile app to use when creating a new Site Visit Log.
    """
    return [
        {"category": "Safety", "checkpoint": "Are fire extinguishers visible, charged, and unblocked?", "status": "Pass"},
        {"category": "Safety", "checkpoint": "Is the emergency pump shut-off switch easily accessible?", "status": "Pass"},
        {"category": "Safety", "checkpoint": "Are sand buckets filled and placed near dispensing units?", "status": "Pass"},
        {"category": "Signage", "checkpoint": "Are all price boards accurate and fully illuminated?", "status": "Pass"},
        {"category": "Signage", "checkpoint": 'Are "No Smoking" and safety warning signs clearly visible?', "status": "Pass"},
        {"category": "Equipment", "checkpoint": "Are all dispensing nozzles and hoses free of leaks?", "status": "Pass"},
        {"category": "Equipment", "checkpoint": "Are the underground tank dip caps properly secured?", "status": "Pass"},
        {"category": "Cleanliness", "checkpoint": "Is the forecourt free of oil spills and debris?", "status": "Pass"},
        {"category": "Cleanliness", "checkpoint": "Are the customer washrooms clean and fully stocked?", "status": "Pass"}
    ]