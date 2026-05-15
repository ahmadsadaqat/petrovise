// Copyright (c) 2026, Ahmad Sadaqat and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daily Stock Log", {
    station: function(frm) {
        update_all_opening_dips(frm);
    },
    log_date: function(frm) {
        update_all_opening_dips(frm);
    }
});

frappe.ui.form.on("Daily Stock Item", {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (frm.doc.station && frm.doc.log_date && row.item_code) {
            frappe.call({
                method: "petrovise.petrovise.doctype.daily_stock_log.daily_stock_log.get_previous_closing_dip",
                args: {
                    station: frm.doc.station,
                    log_date: frm.doc.log_date,
                    item_code: row.item_code
                },
                callback: function(r) {
                    if (r.message !== undefined) {
                        frappe.model.set_value(cdt, cdn, "opening_dip", r.message);
                    }
                }
            });
        }
    },
    opening_dip: function(frm, cdt, cdn) {
        calculate_sales_volume(frm, cdt, cdn);
    },
    received_qty: function(frm, cdt, cdn) {
        calculate_sales_volume(frm, cdt, cdn);
    },
    closing_dip: function(frm, cdt, cdn) {
        calculate_sales_volume(frm, cdt, cdn);
    }
});

function calculate_sales_volume(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let opening = flt(row.opening_dip);
    let received = flt(row.received_qty);
    let closing = flt(row.closing_dip);
    let total_available = opening + received;

    frappe.model.set_value(cdt, cdn, "sales_volume", total_available - closing);
}

function update_all_opening_dips(frm) {
    if (frm.doc.station && frm.doc.log_date && frm.doc.stock_details) {
        $.each(frm.doc.stock_details, function(i, row) {
            if (row.item_code) {
                frappe.call({
                    method: "petrovise.petrovise.doctype.daily_stock_log.daily_stock_log.get_previous_closing_dip",
                    args: {
                        station: frm.doc.station,
                        log_date: frm.doc.log_date,
                        item_code: row.item_code
                    },
                    callback: function(r) {
                        if (r.message !== undefined) {
                            frappe.model.set_value(row.doctype, row.name, "opening_dip", r.message);
                        }
                    }
                });
            }
        });
    }
}
