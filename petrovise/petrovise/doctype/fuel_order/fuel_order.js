// Copyright (c) 2026, Ahmad Sadaqat and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fuel Order", {
    order_details_remove: function(frm) {
        calculate_total(frm);
    }
});

frappe.ui.form.on("Fuel Order Item", {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Item Price",
                    filters: { item_code: row.item_code },
                    fields: ["price_list_rate"],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frappe.model.set_value(cdt, cdn, "rate", r.message[0].price_list_rate);
                    }
                }
            });
        }
    },
    qty: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
    }
});

function calculate_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, "amount", amount);
    
    calculate_total(frm);
}

function calculate_total(frm) {
    let total = 0;
    $.each(frm.doc.order_details || [], function(i, d) {
        total += flt(d.amount);
    });
    frm.set_value("total_amount", total);
}
