import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_hours

class SiteComplaint(Document):
    def before_insert(self):
        # Ensure the opened time is exactly when the record hits the database
        self.opened_at = now_datetime()

    def before_save(self):
        # Track the exact time it gets resolved and calculate the lifecycle
        if self.status == "Resolved" and not self.resolved_at:
            self.resolved_at = now_datetime()

            # Calculate total time open in hours (rounded to 2 decimal places)
            if self.opened_at:
                self.resolution_time_hours = round(time_diff_in_hours(self.resolved_at, self.opened_at), 2)

        # If someone re-opens a resolved complaint, clear the resolution data
        elif self.status != "Resolved":
            self.resolved_at = None
            self.resolution_time_hours = 0

    def after_insert(self):
        # Send automated email notification upon creation
        recipients = ["hq@vitalpetroleum.com"] # Replace with actual HQ email

        if self.assigned_asm:
            recipients.append(self.assigned_asm)

        subject = f"New Site Complaint Logged: {self.station} - {self.issue_category}"
        message = f"""
        <p>A new issue has been logged by the dealer.</p>
        <ul>
            <li><b>Station:</b> {self.station}</li>
            <li><b>Category:</b> {self.issue_category}</li>
            <li><b>Description:</b> {self.description}</li>
            <li><b>Status:</b> {self.status}</li>
        </ul>
        <p>Please review this in the Petrovise dashboard.</p>
        """

        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            now=True # Sends immediately
        )