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
    # 1. Permission check
    if "Petrovise Finance" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Only Petrovise Finance users can release payments."), frappe.PermissionError)

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
    if latest_stock_list:
        # Fetch full document to include the child table (stock_details)
        latest_stock = frappe.get_doc("Daily Stock Log", latest_stock_list[0].name).as_dict()

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
            "name", "transaction_date", "grand_total", "status", 
            "custom_released", "custom_station", "custom_payment_slip"
        ],
        order_by="transaction_date desc",
        limit=5
    )

    # 6. Package and return the payload
    return {
        "customer": customer,
        "station_name": station,
        "credit_limit": flt(credit_limit),
        "lead_time": flt(station_details.get("lead_time", 0)),
        "minimum_stock": flt(station_details.get("minimum_stock", 0)),
        "latest_stock_log": latest_stock,
        "active_complaints": open_complaints,
        "pending_orders": pending_orders
    }