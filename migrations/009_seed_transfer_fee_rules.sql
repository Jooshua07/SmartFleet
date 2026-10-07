-- Airtel Money to another Airtel Money number

INSERT INTO transfer_fee_rules
    (transfer_type, minimum_amount, maximum_amount, fee_amount, notes)
VALUES
    ('AIRTEL_TO_AIRTEL', 1.00,    500.00,   4.00,  'Current Airtel transfer rule'),
    ('AIRTEL_TO_AIRTEL', 500.01,  1000.00,  6.00,  'Current Airtel transfer rule'),
    ('AIRTEL_TO_AIRTEL', 1000.01, 3000.00,  8.00,  'Current Airtel transfer rule'),
    ('AIRTEL_TO_AIRTEL', 3000.01, 5000.00,  12.00, 'Current Airtel transfer rule'),
    ('AIRTEL_TO_AIRTEL', 5000.01, 10000.00, 15.00, 'Current Airtel transfer rule');


-- Airtel Money to business bank account

INSERT INTO transfer_fee_rules
    (transfer_type, minimum_amount, maximum_amount, fee_amount, notes)
VALUES
    ('AIRTEL_TO_BANK', 0.01,     5000.00,  50.00,  'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 5000.01,  10000.00, 100.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 10000.01, 15000.00, 150.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 15000.01, 20000.00, 200.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 20000.01, 25000.00, 250.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 25000.01, 30000.00, 300.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 30000.01, 35000.00, 350.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 35000.01, 40000.00, 400.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 40000.01, 45000.00, 450.00, 'K50 per K5,000 band'),
    ('AIRTEL_TO_BANK', 45000.01, 50000.00, 500.00, 'K50 per K5,000 band');