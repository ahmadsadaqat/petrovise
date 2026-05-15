# Petrovise

Petrovise is a comprehensive ERPNext application tailored for petroleum companies to manage their retail stations. It streamlines site operations, dealer ordering, fuel stock tracking, and compliance audits with robust automation and financial controls.

## Key Features & Workflows

### 1. Fuel Order Management

The central module for dealers to request fuel inventory, tightly integrated with station credit limits and finance approvals.

- **Credit Limit Enforcement:** A station's credit limit (set on the `Warehouse` master) is strictly enforced. Orders exceeding the available limit cannot be submitted.
- **Dynamic Pricing:** Automatically fetches the selling `Rate` from the standard Item Price list when an item is selected.
- **Multi-Stage Workflow:**
  - **Draft:** Dealer creates the order.
  - **Unpaid:** Upon submission without a payment slip, the order sits in an unpaid state.
  - **Pending Finance Approval:** Once the dealer attaches the payment slip to the submitted order, the system instantly deducts the order amount from the station's credit limit and routes the order to Finance.
- **Cancellation Refunds:** If a submitted order is cancelled, the deducted credit limit is automatically refunded to the station.

### 2. Daily Stock Log

Tracks the daily fuel inventory at the station level via dip readings.

- **Auto-Carryover:** The opening dip for any given item is automatically fetched from the previous day's closing dip in real-time.
- **Volume Calculation:** Calculates `Sales Volume` dynamically based on `(Opening Dip + Received Qty) - Closing Dip`.
- **Validation:** Prevents saving if the closing dip exceeds total available stock.

### 3. Site Visit Log

A mobile-friendly module for Area Sales Managers (ASMs) to conduct routine station audits.

- **Auto-Assignment:** Automatically assigns the logged-in ASM to the visit record.
- **Standardized Checklist:** Instantly populates a comprehensive, 9-point Safety, Signage, Equipment, and Cleanliness checklist to ensure compliance standards are met rapidly.

### 4. Site Complaint

Allows dealers to log operational, maintenance, or equipment issues.

- **Automated Time Tracking:** Records the exact time an issue is opened and resolved, calculating the total `Resolution Time (Hours)` automatically.
- **Instant Notifications:** Automatically dispatches an email notification to HQ (`hq@petroleum.com`) and the assigned ASM the moment a complaint is logged.

## Roles & Permissions

The app ships with two custom roles tailored to the operational hierarchy:

- **Petrovise ASM**
- **Petrovise Finance**

**Access Levels:** Both roles are pre-configured with **Create, Read, Write, and Submit** access to all four core doctypes (`Site Complaint`, `Fuel Order`, `Site Visit Log`, `Daily Stock Log`). _Delete access is strictly disabled for data integrity._

## Installation

To install the app on your Frappe Bench:

```bash
bench get-app petrovise https://github.com/your-repo/petrovise.git
bench --site [your-site-name] install-app petrovise
bench --site [your-site-name] migrate
```

_(The `migrate` command will automatically generate the required custom fields, roles, and permissions in your database)._

## License

MIT
