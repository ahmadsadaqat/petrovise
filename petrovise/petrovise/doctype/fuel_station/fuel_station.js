// Copyright (c) 2026, Ahmad Sadaqat and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fuel Station", {
    customer: function(frm) {
        if (frm.doc.customer) {
            frappe.db.get_doc("Customer", frm.doc.customer).then(doc => {
                if (doc.credit_limits && doc.credit_limits.length > 0) {
                    let limit = doc.credit_limits[0].credit_limit;
                    frm.set_value("credit_limit", limit);
                    frappe.show_alert({message: `Credit Limit updated to ${limit} based on Customer profile.`, indicator: "blue"});
                } else {
                    frm.set_value("credit_limit", 0);
                    frappe.show_alert({message: `No credit limit found for this customer.`, indicator: "orange"});
                }
            });
        } else {
            frm.set_value("credit_limit", 0);
        }
    }
});
