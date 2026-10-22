from html import escape

import frappe
from frappe.utils import add_days, formatdate, getdate, nowdate
from frappe.utils.user import get_users_with_role

SETTINGS = "Batch Expiry Notification Setting"
LOG = "Batch Expiry Alert Log"


def send_batch_expiry_alerts(on_date=None, force=0):
    """Runs daily at 00:00. One email per configured offset, listing all
    batches that expire on (today + offset)."""
    settings = frappe.get_single(SETTINGS)
    if not settings.enabled:
        return

    today = getdate(on_date or nowdate())
    to_list, cc_list = get_recipients(settings)
    if not to_list:
        frappe.log_error("No 'To' recipients configured", "Batch Expiry Alert")
        return

    offsets = sorted({int(r.days_before) for r in settings.get("reminder_days")}, reverse=True)

    for days in offsets:
        expiry_date = add_days(today, days)
        batches = get_batches(expiry_date, settings.skip_zero_stock)

        if not force:
            batches = [
                b for b in batches
                if not frappe.db.exists(LOG, {"batch": b.name, "days_before": days})
            ]
        if not batches:
            continue

        send_mail(settings, to_list, cc_list, batches, days, expiry_date)

        if not force:
            for b in batches:
                frappe.get_doc({
                    "doctype": LOG,
                    "batch": b.name,
                    "days_before": days,
                    "sent_on": today,
                }).insert(ignore_permissions=True)

    frappe.db.commit()


def get_batches(expiry_date, skip_zero_stock):
    batches = frappe.get_all(
        "Batch",
        filters={"expiry_date": expiry_date, "disabled": 0},
        fields=["name", "item", "item_name", "expiry_date", "batch_qty", "stock_uom"],
        order_by="item asc",
    )
    if skip_zero_stock:
        batches = [b for b in batches if (b.batch_qty or 0) > 0]
    return batches


def get_recipients(settings):
    to, cc = set(), set()
    for r in settings.get("recepients"):
        if (r.recepient_type or "").lower() == "email":
            emails = [r.email]
        else:
            emails = get_users_with_role(r.role)
        target = to if (r.send_as or "").lower() == "to" else cc
        target.update(e for e in emails if e and e != "Administrator")
    cc -= to
    return sorted(to), sorted(cc)


def build_table(batches):
    rows = ""
    for i, b in enumerate(batches, 1):
        rows += (
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{escape(str(b.name))}</td>"
            f"<td>{escape(str(b.item or ''))}</td>"
            f"<td>{escape(str(b.item_name or ''))}</td>"
            f"<td>{formatdate(b.expiry_date)}</td>"
            f"<td align='right'>{b.batch_qty or 0}</td>"
            f"<td>{escape(str(b.stock_uom or ''))}</td>"
            "</tr>"
        )
    return (
        "<table border='1' cellpadding='6' cellspacing='0' "
        "style='border-collapse:collapse;font-size:13px;'>"
        "<thead style='background:#f0f0f0;'><tr>"
        "<th>#</th><th>Batch ID</th><th>Item Code</th><th>Item Name</th>"
        "<th>Expiry Date</th><th>Qty in Stock</th><th>UOM</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def send_mail(settings, to_list, cc_list, batches, days, expiry_date):
    if days == 0:
        subject = "Batch Expiry Alert: batches expiring TODAY"
        when = "<b>expire today</b>"
    else:
        subject = f"Batch Expiry Alert: batches expiring in {days} day(s)"
        when = f"will expire in <b>{days} day(s)</b>"

    message = (
        "<p>Hello,</p>"
        f"<p>The following batches {when} ({formatdate(expiry_date)}):</p>"
        f"{build_table(batches)}"
        "<p>Please take the necessary action.</p>"
    )

    frappe.sendmail(
        recipients=to_list,
        cc=cc_list,
        sender=settings.sender_email,
        subject=subject,
        message=message,
        reference_doctype=SETTINGS,
    )
