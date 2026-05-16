// Copyright (c) 2026, Ahmad Sadaqat and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daily Stock Log", {
    onload: function(frm) {
        if (frm.doc.station) {
            fetch_station_details(frm);
        }
    },
    station: function(frm) {
        update_all_opening_dips(frm);
        fetch_station_details(frm);
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
        check_minimum_stock_and_dry_out(frm, cdt, cdn);
    }
});

function fetch_station_details(frm) {
    if (frm.doc.station) {
        frappe.db.get_value("Fuel Station", frm.doc.station, ["minimum_stock", "lead_time"], (r) => {
            if (r) {
                frm.station_minimum_stock = flt(r.minimum_stock);
                frm.station_lead_time = flt(r.lead_time);
            }
        });
    }
}

function calculate_sales_volume(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let opening = flt(row.opening_dip);
    let received = flt(row.received_qty);
    let closing = flt(row.closing_dip);
    let total_available = opening + received;

    // Available stock = what's currently in the tank
    if (closing > 0) {
        // Closing dip entered: that's the physical stock remaining
        frappe.model.set_value(cdt, cdn, "available_quantity", closing);
    } else {
        // No closing yet: total supply is what's available
        frappe.model.set_value(cdt, cdn, "available_quantity", total_available);
    }
}

function check_minimum_stock_and_dry_out(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let closing = flt(row.closing_dip);
    let min_stock = frm.station_minimum_stock || 0;
    let lead_time = frm.station_lead_time || 0;

    if (!row.item_code || closing <= 0) return;

    // Warning: below minimum stock
    if (min_stock > 0 && closing < min_stock) {
        frappe.show_alert({
            message: `⚠️ ${row.item_code} closing stock (${closing.toFixed(0)} L) is below minimum stock (${min_stock.toFixed(0)} L). Please place a fuel order!`,
            indicator: 'orange'
        }, 7);
    }

    // Fetch average daily sales from last 7 days for accurate prediction
    if (frm.doc.station && frm.doc.log_date) {
        frappe.call({
            method: "petrovise.petrovise.doctype.daily_stock_log.daily_stock_log.get_avg_daily_sales",
            args: {
                station: frm.doc.station,
                log_date: frm.doc.log_date,
                item_code: row.item_code
            },
            callback: function(r) {
                if (!r.message) return;

                let hist_avg = flt(r.message.avg_sales);
                let days_counted = r.message.days_counted;
                
                // Calculate today's sales locally since it's only saved on submit now
                let today_sales = (flt(row.opening_dip) + flt(row.received_qty)) - closing;

                // Blend today's sales into the historical average
                let avg_sales;
                let total_days;
                if (days_counted > 0 && hist_avg > 0) {
                    total_days = days_counted + 1;
                    avg_sales = ((hist_avg * days_counted) + today_sales) / total_days;
                } else if (today_sales > 0) {
                    // No history, use today only
                    avg_sales = today_sales;
                    total_days = 1;
                } else {
                    return; // No data at all
                }

                if (avg_sales <= 0) return;

                let days_remaining = closing / avg_sales;

                // Build the alert message
                let msg = `<b>Dry Out Analysis for ${row.item_code}</b><br><br>`;
                msg += `📊 Average daily sales (last ${total_days} days incl. today): <b>${avg_sales.toFixed(0)} Liters/day</b><br>`;
                msg += `📈 Today's sales: <b>${today_sales.toFixed(0)} Liters</b><br>`;
                msg += `⛽ Current closing stock: <b>${closing.toFixed(0)} Liters</b><br>`;
                msg += `⏳ Estimated stock life: <b>${days_remaining.toFixed(1)} days</b><br><br>`;

                if (lead_time > 0 && days_remaining < lead_time) {
                    // Critical: will dry out before delivery even if ordered today
                    msg += `🚨 <b style="color:red;">CRITICAL:</b> Your stock will run out in <b>${days_remaining.toFixed(1)} days</b>, `;
                    msg += `but delivery takes <b>${lead_time} days</b>. `;
                    msg += `Even if you order right now, you will dry out <b>${(lead_time - days_remaining).toFixed(1)} days before delivery arrives!</b>`;

                    frappe.msgprint({
                        title: '🚨 Critical Dry Out Alert',
                        indicator: 'red',
                        message: msg
                    });
                } else if (lead_time > 0 && days_remaining < (lead_time + 2)) {
                    // Warning: must order today to avoid dry out
                    msg += `⚠️ <b style="color:orange;">ORDER TODAY:</b> Your stock will last <b>${days_remaining.toFixed(1)} days</b> `;
                    msg += `and delivery takes <b>${lead_time} days</b>. `;
                    msg += `If you don't place an order today, you risk running dry!`;

                    frappe.msgprint({
                        title: '⚠️ Order Now to Avoid Dry Out',
                        indicator: 'orange',
                        message: msg
                    });
                } else if (lead_time > 0 && days_remaining < (lead_time + 5)) {
                    // Advisory: plan an order within the next few days
                    let days_left_to_order = (days_remaining - lead_time).toFixed(1);
                    msg += `📋 <b style="color:#318AD8;">PLAN AHEAD:</b> Your stock will last <b>${days_remaining.toFixed(1)} days</b> `;
                    msg += `and delivery takes <b>${lead_time} days</b>. `;
                    msg += `You have approximately <b>${days_left_to_order} days</b> to place an order before it becomes critical.`;

                    frappe.msgprint({
                        title: '📋 5-Day Order Reminder',
                        indicator: 'blue',
                        message: msg
                    });
                }
            }
        });
    }
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
