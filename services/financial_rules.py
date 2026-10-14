"""Shared operating-versus-financing definitions; money remains Decimal."""

EXCLUDED_OPERATING_EXPENSE_CATEGORIES = frozenset({
    'Driver Advances', 'Driver Salaries', 'Loan Repayments', 'Owner Drawings',
})
OPERATING_PAYMENT_TYPES = frozenset({'EXPENSE', 'DRIVER_SALARY', 'TRANSFER_FEE', 'OTHER'})

# These aliases match the ordinary expense queries in performance and Bus Accounts.
OPERATING_EXPENSE_PREDICATE = """ec.name NOT IN ('Driver Advances', 'Driver Salaries', 'Loan Repayments', 'Owner Drawings')
    AND (e.payment_source = 'OWNER_PERSONAL' OR ft.transaction_type IN ('EXPENSE', 'TRANSFER_FEE', 'OTHER'))"""
