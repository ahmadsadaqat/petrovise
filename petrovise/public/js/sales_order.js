// Petrovise customizations for Sales Order
// Adds Station link, auto-fetch Customer, Payment Slip, and Release Payment workflow

frappe.ui.form.on("Sales Order", {
    refresh: function(frm) {
        // Show Release Payment button only for Petrovise Finance on submitted, unreleased orders
        if (frm.doc.docstatus === 1
            && !frm.doc.custom_released
            && frappe.user_roles.includes("Petrovise Finance")) {

            frm.add_custom_button(__("Release Payment"), function() {
                // Show dialog to pick Mode of Payment
                let d = new frappe.ui.Dialog({
                    title: __("Release Payment"),
                    fields: [
                        {
                            label: "Mode of Payment",
                            fieldname: "mode_of_payment",
                            fieldtype: "Link",
                            options: "Mode of Payment",
                            reqd: 1,
                            default: "Bank Transfer"
                        }
                    ],
                    primary_action_label: __("Create Payment Entry"),
                    primary_action(values) {
                        d.hide();
                        frappe.call({
                            method: "petrovise.api.release_payment",
                            args: {
                                sales_order_name: frm.doc.name,
                                mode_of_payment: values.mode_of_payment
                            },
                            freeze: true,
                            freeze_message: __("Creating Payment Entry..."),
                            callback: function(r) {
                                if (r.message) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                });
                d.show();
            }, __("Petrovise"));
        }
    },

    custom_station: function(frm) {
        if (frm.doc.custom_station) {
            frappe.db.get_value("Fuel Station", frm.doc.custom_station, ["customer"], (r) => {
                if (r && r.customer) {
                    frm.set_value("customer", r.customer);
                    frappe.show_alert({
                        message: __("Customer fetched from Station: {0}", [r.customer]),
                        indicator: "blue"
                    });
                }
            });
        }
    }
});
