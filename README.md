# Batch Expiry Alert (Frappe v16 + ERPNext)

Emails an HTML table of expiring batches every day at 12:00 AM IST, for 6, 2 and 0 days before expiry. One email is sent per reminder day. A log prevents duplicate emails.

## Requirements
- Frappe v16 and ERPNext v16
- A working outgoing Email Account (Gmail needs an App Password)

## Install
    cd $PATH_TO_YOUR_BENCH
    bench get-app https://github.com/Vrunda-Dholariya/batch_expiry_alert --branch main
    bench --site <your-site> install-app batch_expiry_alert
    bench --site <your-site> migrate

## Setup
1. Set up an outgoing Email Account.
2. Open **Batch Expiry Notification Setting**: tick Enabled, set Sender Email, add reminder days (6, 2, 0), add recipients as To or CC.
3. Optional: tick Skip Zero Stock.

## Limitations
- A batch added with fewer than 6 days left misses the 6-day reminder.
- Send time is fixed at midnight server time.
- Every reminder day goes to the same recipients.
- Use a dedicated sender address in production.
