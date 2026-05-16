import frappe
from frappe.model.document import Document
from frappe.utils import flt

class DailyStockLog(Document):
    def before_save(self):
        # 1. Check if we have the necessary data
        if self.station and self.log_date:
            prev_log = frappe.get_all(
                "Daily Stock Log",
                filters={
                    "station": self.station,
                    "log_date": ("<", self.log_date),
                    "docstatus": 1
                },
                fields=["name"],
                order_by="log_date desc",
                limit=1
            )

            # 2. Build a dictionary of yesterday's closing dips
            prev_dips = {}
            if prev_log:
                # FIXED: Added to access the first dictionary in the list
                prev_items = frappe.get_all(
                    "Daily Stock Item",
                    filters={"parent": prev_log[0].name},
                    fields=["item_code", "closing_dip"]
                )
                for item in prev_items:
                    prev_dips[item.item_code] = item.closing_dip

            # 3. Loop through today's rows
            if self.get("stock_details"):
                for row in self.stock_details:
                    # Apply previous dip
                    row.opening_dip = prev_dips.get(row.item_code, 0)

                    # Ensure numbers
                    opening = flt(row.opening_dip)
                    received = flt(row.received_qty)
                    closing = flt(row.closing_dip)

                    total_available = opening + received

                    # Validate
                    if closing > total_available:
                        frappe.throw(f"Row {row.idx}: Closing dip ({closing}) cannot be greater than total available stock ({total_available}) for {row.item_code}.")

                    # Calculate Daily Sales on Save
                    row.daily_sales = total_available - closing

@frappe.whitelist()
def get_previous_closing_dip(station, log_date, item_code):
    prev_log = frappe.get_all(
        "Daily Stock Log",
        filters={
            "station": station,
            "log_date": ("<", log_date),
            "docstatus": 1
        },
        fields=["name"],
        order_by="log_date desc",
        limit=1
    )
    if prev_log:
        closing_dip = frappe.db.get_value(
            "Daily Stock Item",
            {"parent": prev_log[0].name, "item_code": item_code},
            "closing_dip"
        )
        return flt(closing_dip)
    return 0.0

@frappe.whitelist()
def get_avg_daily_sales(station, log_date, item_code):
    """Calculate the average daily sales volume from the last 7 submitted stock logs."""
    from frappe.utils import add_days

    prev_logs = frappe.get_all(
        "Daily Stock Log",
        filters={
            "station": station,
            "log_date": ("<", log_date),
            "docstatus": 1
        },
        fields=["name"],
        order_by="log_date desc",
        limit=7
    )

    if not prev_logs:
        return {"avg_sales": 0, "days_counted": 0}

    parent_names = [log.name for log in prev_logs]
    items = frappe.get_all(
        "Daily Stock Item",
        filters={
            "parent": ("in", parent_names),
            "item_code": item_code
        },
        fields=["daily_sales"]
    )

    if not items:
        return {"avg_sales": 0, "days_counted": 0}

    total_sales = sum(flt(item.daily_sales) for item in items)
    days_counted = len(items)
    avg_sales = total_sales / days_counted if days_counted else 0

    return {"avg_sales": avg_sales, "days_counted": days_counted}
