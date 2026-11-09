# Data dictionary

Each reporting period references an immutable organisation-owned template version. CSV headers begin with `company_identifier`, `reporting_year` (2000–2100), and `reporting_month` (1–12), followed by the template's metric keys in order. The supported metric keys are `revenue`, `expenses`, `cash_balance` (decimal) and `customer_count`, `new_customers`, `employee_count` (integer). Templates define requiredness, units, and optional numeric bounds. UTF-8 and UTF-8 BOM are supported. Each upload contains one company and one reporting period.

## Metric semantics

- `revenue`, `expenses`, and `new_customers` are reporting-period flows.
- `customer_count`, `employee_count`, and `cash_balance` are period-end snapshots.
- Only approved submissions contribute to analytics. Pending, rejected, validation-failed, and superseded submissions are excluded.
- Company overview revenue/expenses/profit and new-customer counts are sums over approved periods. Snapshot values are taken from the chronologically latest approved period.
- Portfolio overview selects each company's latest approved report. It sums that report's values per metric; the selected reporting periods may differ between companies. The response includes period coverage and explicitly identifies this basis. These totals must not be interpreted as same-period comparable values when coverage differs.
- Missing optional metrics remain `null`; calculations do not treat missing values as zero.

## Reporting period dates and submission history

Reporting-period start/end dates use actual calendar month boundaries, including leap years. Failed uploads are preserved with retrievable row/file errors. Corrected submissions link to their prior submission; original submissions and transition events are retained.
