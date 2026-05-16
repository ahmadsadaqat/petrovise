import frappe
from frappe.model.document import Document
from frappe.utils import flt

class FuelOrder(Document):
    def validate(self):
        self.calculate_totals()
        
        station_limit = frappe.db.get_value("Fuel Station", self.station, "credit_limit")
        station_limit = flt(station_limit)
        if self.total_amount > station_limit and not self.finance_release:
            frappe.msgprint(f"Warning: This order ({self.total_amount:,.2f}) exceeds the station's available credit limit ({station_limit:,.2f}). You will not be able to submit it.", indicator="orange")
    def calculate_totals(self):
        total = 0
        if self.get("order_details"):
            for row in self.order_details:
                row.amount = flt(row.qty) * flt(row.rate)
                total += row.amount

        self.total_amount = total

    def before_submit(self):
        station_limit = frappe.db.get_value("Fuel Station", self.station, "credit_limit")
        station_limit = flt(station_limit)
        
        if self.total_amount > station_limit and not self.finance_release:
            frappe.throw(f"Cannot submit: This order ({self.total_amount:,.2f}) exceeds the station's available credit limit ({station_limit:,.2f}).")

    def on_submit(self):
        if not self.payment_slip:
            self.db_set("status", "Unpaid")
        else:
            self.process_payment_slip()

    def on_update_after_submit(self):
        # If status is Unpaid and slip is now uploaded
        if self.status == "Unpaid" and self.payment_slip:
            self.process_payment_slip()

    def process_payment_slip(self):
        station_limit = frappe.db.get_value("Fuel Station", self.station, "credit_limit")
        station_limit = flt(station_limit)

        # Deduct limit
        new_limit = station_limit - self.total_amount
        frappe.db.set_value("Fuel Station", self.station, "credit_limit", new_limit)

        # Update status
        self.db_set("status", "Pending Finance Approval")
        frappe.msgprint(f"Payment slip attached. Credit limit reduced by {self.total_amount:,.2f}. Status updated to Pending Finance Approval.", indicator="green")

    def on_cancel(self):
        # Refund limit if it was already processed
        if self.status not in ["Draft", "Unpaid"]:
            station_limit = frappe.db.get_value("Fuel Station", self.station, "credit_limit")
            station_limit = flt(station_limit)
            refunded_limit = station_limit + self.total_amount
            frappe.db.set_value("Fuel Station", self.station, "credit_limit", refunded_limit)
            frappe.msgprint(f"Order cancelled. Credit limit of {self.total_amount:,.2f} refunded to {self.station}.", indicator="orange")