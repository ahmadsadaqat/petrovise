frappe.ui.form.on("Site Visit Log", {
	refresh: function (frm) {
		// 1. Auto-set the ASM Name to the actual logged-in user
		if (frm.is_new() && !frm.doc.asm_name) {
			frm.set_value("asm_name", frappe.session.user);
		}

		// 2. Auto-populate the checklist
		if (frm.is_new() && (!frm.doc.audit_checklist || frm.doc.audit_checklist.length === 0)) {
			const standard_questions = [
				{
					category: "Safety",
					checkpoint: "Are fire extinguishers visible, charged, and unblocked?",
					status: "Pass",
				},
				{
					category: "Safety",
					checkpoint: "Is the emergency pump shut-off switch easily accessible?",
					status: "Pass",
				},
				{
					category: "Safety",
					checkpoint: "Are sand buckets filled and placed near dispensing units?",
					status: "Pass",
				},
				{
					category: "Signage",
					checkpoint: "Are all price boards accurate and fully illuminated?",
					status: "Pass",
				},
				{
					category: "Signage",
					checkpoint: 'Are "No Smoking" and safety warning signs clearly visible?',
					status: "Pass",
				},
				{
					category: "Equipment",
					checkpoint: "Are all dispensing nozzles and hoses free of leaks?",
					status: "Pass",
				},
				{
					category: "Equipment",
					checkpoint: "Are the underground tank dip caps properly secured?",
					status: "Pass",
				},
				{
					category: "Cleanliness",
					checkpoint: "Is the forecourt free of oil spills and debris?",
					status: "Pass",
				},
				{
					category: "Cleanliness",
					checkpoint: "Are the customer washrooms clean and fully stocked?",
					status: "Pass",
				},
			];

			standard_questions.forEach((q) => {
				let row = frm.add_child("audit_checklist");
				row.category = q.category;
				row.checkpoint = q.checkpoint;
				row.status = q.status; // Defaults everything to 'Pass' to save time!
			});

			frm.refresh_field("audit_checklist");
			frappe.show_alert({ message: "Standard safety checklist loaded.", indicator: "blue" });
		}
	},
});
