-- SmartFleet Schema V1: automated integrity regression tests for migration 022.
-- Run using: \i 'C:/.../migrations/smartfleet_integrity_tests.sql'
-- All inserts and updates are in one outer transaction that is ALWAYS rolled back.
-- Do not wrap this file in another transaction. Ensure psql prompt is smartfleet=#.
\set ON_ERROR_STOP on
\pset pager off
BEGIN;

CREATE TEMP TABLE sf_test_results (
    test_name TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('PASS','FAIL')),
    detail TEXT
) ON COMMIT DROP;

-- Fixtures are transaction-local and will be discarded.
INSERT INTO routes(name) VALUES ('SF022 Integrity Test Route');
INSERT INTO buses(registration_number, route_id)
SELECT v.registration_number, r.id FROM routes r CROSS JOIN
(VALUES ('SF022-TEST-A'), ('SF022-TEST-B')) v(registration_number)
WHERE r.name='SF022 Integrity Test Route';
INSERT INTO drivers(full_name) VALUES ('SF022 Test Driver One'), ('SF022 Test Driver Two');
INSERT INTO driver_employments(driver_id,start_date,monthly_salary)
SELECT id, CURRENT_DATE - 40, 2000 FROM drivers WHERE full_name LIKE 'SF022 Test Driver %';

-- Each DO block catches an expected error in its own PL/pgSQL subtransaction.
-- An unexpected success is intentionally rolled back by raising SQLSTATE ZX001.
-- An unexpected error in a valid scenario is recorded as FAIL.

-- 01: Owner personally pays an expense: no business ledger entry, but matching owner debt.
DO $test$
DECLARE e_id INT; err TEXT;
BEGIN
  BEGIN
    INSERT INTO expenses(expense_date,category_id,amount,description,scope,payment_source)
    VALUES (CURRENT_DATE,(SELECT id FROM expense_categories WHERE name='Parts'),900,
      'SF022 personal parts', 'GENERAL','OWNER_PERSONAL') RETURNING id INTO e_id;
    INSERT INTO owner_loan_transactions(owner_loan_id,transaction_date,transaction_type,amount,description,expense_id)
    VALUES ((SELECT id FROM owner_loans WHERE name='Owner Loan Account'),CURRENT_DATE,
      'OWNER_FUNDED',900,'SF022 owner parts',e_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    INSERT INTO sf_test_results VALUES ('01 owner personal expense + loan','PASS','Matching personal expense and owner obligation accepted');
    SET CONSTRAINTS ALL DEFERRED;
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('01 owner personal expense + loan','FAIL',err);
  END;
END $test$;

-- 02: Owner repayment without an outgoing ledger transaction must be rejected.
DO $test$
DECLARE err TEXT;
BEGIN
  BEGIN
    INSERT INTO owner_loan_transactions(owner_loan_id,transaction_date,transaction_type,amount,description)
    VALUES ((SELECT id FROM owner_loans WHERE name='Owner Loan Account'),CURRENT_DATE,
      'REPAYMENT',100,'SF022 unbacked repayment');
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='INVALID owner repayment was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('02 unbacked owner repayment rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%needs ledger%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 03: Owner deposits money into tracked business account: matched IN ledger.
DO $test$
DECLARE f_id INT; err TEXT;
BEGIN
  BEGIN
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'OWNER_LOAN','IN',250)
    RETURNING id INTO f_id;
    INSERT INTO owner_loan_transactions(owner_loan_id,transaction_date,transaction_type,amount,description,financial_transaction_id)
    VALUES ((SELECT id FROM owner_loans WHERE name='Owner Loan Account'),CURRENT_DATE,
      'OWNER_FUNDED',250,'SF022 owner deposit',f_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    INSERT INTO sf_test_results VALUES ('03 matched owner deposit','PASS','Business account IN and owner debt accepted');
    SET CONSTRAINTS ALL DEFERRED;
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('03 matched owner deposit','FAIL',err);
  END;
END $test$;

-- 04: Business loan cannot be over-repaid (even if there is a correct ledger OUT).
DO $test$
DECLARE l_id INT; f_id INT; err TEXT;
BEGIN
  BEGIN
    INSERT INTO business_loans(loan_name,lender,original_amount,start_date,default_monthly_repayment)
    VALUES ('SF022 overpay test','SF022 Lender',500,CURRENT_DATE,100) RETURNING id INTO l_id;
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'LOAN_REPAYMENT','OUT',600)
    RETURNING id INTO f_id;
    INSERT INTO loan_repayments(loan_id,repayment_date,amount,payment_source,financial_transaction_id)
    VALUES (l_id,CURRENT_DATE,600,'BUSINESS_ACCOUNT',f_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='INVALID loan overpayment was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('04 overpaid business loan rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%over-repaid%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 05: Owner personally pays a business loan: increases owner obligation, no cash movement.
DO $test$
DECLARE l_id INT; o_id INT; err TEXT;
BEGIN
  BEGIN
    INSERT INTO business_loans(loan_name,lender,original_amount,start_date,default_monthly_repayment)
    VALUES ('SF022 owner loan payment','SF022 Lender',1000,CURRENT_DATE,100) RETURNING id INTO l_id;
    INSERT INTO owner_loan_transactions(owner_loan_id,transaction_date,transaction_type,amount,description)
    VALUES ((SELECT id FROM owner_loans WHERE name='Owner Loan Account'),CURRENT_DATE,
      'OWNER_FUNDED',300,'SF022 owner pays lender') RETURNING id INTO o_id;
    INSERT INTO loan_repayments(loan_id,repayment_date,amount,payment_source,owner_loan_transaction_id)
    VALUES (l_id,CURRENT_DATE,300,'OWNER_PERSONAL',o_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    INSERT INTO sf_test_results VALUES ('05 owner pays business lender','PASS','Debt shifted from lender to owner without bank movement');
    SET CONSTRAINTS ALL DEFERRED;
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('05 owner pays business lender','FAIL',err);
  END;
END $test$;

-- 06: A driver advance with a matching payment is valid.
DO $test$
DECLARE emp INT; f_id INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver One';
  BEGIN
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'DRIVER_ADVANCE','OUT',400)
    RETURNING id INTO f_id;
    INSERT INTO driver_advances(employment_id,advance_date,amount,financial_transaction_id)
    VALUES (emp,CURRENT_DATE,400,f_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    INSERT INTO sf_test_results VALUES ('06 matching driver advance','PASS','Advance and outgoing payment accepted');
    SET CONSTRAINTS ALL DEFERRED;
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('06 matching driver advance','FAIL',err);
  END;
END $test$;

-- 07: A driver advance cannot misstate the ledger amount.
DO $test$
DECLARE emp INT; f_id INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver Two';
  BEGIN
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'DRIVER_ADVANCE','OUT',250)
    RETURNING id INTO f_id;
    INSERT INTO driver_advances(employment_id,advance_date,amount,financial_transaction_id)
    VALUES (emp,CURRENT_DATE,300,f_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='INVALID advance amount was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('07 mismatched driver advance rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%must match its OUT ledger transaction%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 08: Salary cannot claim K100 recovered unless allocation rows total K100.
DO $test$
DECLARE emp INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver One';
  BEGIN
    INSERT INTO driver_salaries(employment_id,salary_year,salary_month,base_salary,
      prorated_salary,advance_recovery,other_deductions)
    VALUES (emp,2098,1,2000,2000,100,0);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='UNALLOCATED payroll recovery was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('08 missing salary recovery allocation rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%allocations do not reconcile%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 09: An advance from one employment cannot be allocated to another employment.
DO $test$
DECLARE emp INT; foreign_advance INT; salary INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver Two';
  SELECT a.id INTO foreign_advance FROM driver_advances a JOIN driver_employments e
    ON e.id=a.employment_id JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver One' ORDER BY a.id DESC LIMIT 1;
  BEGIN
    INSERT INTO driver_salaries(employment_id,salary_year,salary_month,base_salary,
      prorated_salary,advance_recovery)
    VALUES (emp,2098,2,2000,2000,100) RETURNING id INTO salary;
    INSERT INTO salary_advance_recoveries(salary_id,advance_id,amount)
    VALUES (salary,foreign_advance,100);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='CROSS-DRIVER recovery was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('09 cross-driver recovery rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND ((err LIKE '%different employment%' OR err LIKE '%another employment%')) THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 10: Payroll with matching advance recovery, deduction, and net payment is valid.
DO $test$
DECLARE emp INT; a_id INT; d_id INT; f_id INT; salary INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver One';
  SELECT a.id INTO a_id FROM driver_advances a WHERE a.employment_id=emp ORDER BY a.id DESC LIMIT 1;
  BEGIN
    INSERT INTO driver_deductions(employment_id,deduction_date,amount,deduction_type,reason)
    VALUES (emp,CURRENT_DATE,50,'PENALTY','SF022 sample deduction') RETURNING id INTO d_id;
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'DRIVER_SALARY','OUT',1850)
    RETURNING id INTO f_id;
    INSERT INTO driver_salaries(employment_id,salary_year,salary_month,base_salary,
      prorated_salary,advance_recovery,other_deductions,status,payment_date,financial_transaction_id)
    VALUES (emp,2098,3,2000,2000,100,50,'PAID',CURRENT_DATE,f_id) RETURNING id INTO salary;
    INSERT INTO salary_advance_recoveries(salary_id,advance_id,amount) VALUES (salary,a_id,100);
    INSERT INTO salary_deduction_allocations(salary_id,deduction_id,amount) VALUES (salary,d_id,50);
    -- The deduction is fully applied by this paid salary; keep its state consistent.
    UPDATE driver_deductions SET applied=TRUE WHERE id=d_id;
    SET CONSTRAINTS ALL IMMEDIATE;
    INSERT INTO sf_test_results VALUES ('10 matching paid payroll','PASS','Net salary 1850 and allocations 100+50 accepted');
    SET CONSTRAINTS ALL DEFERRED;
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('10 matching paid payroll','FAIL',err);
  END;
END $test$;

-- 11: Maintenance for bus B cannot link to a bus A expense.
DO $test$
DECLARE f_id INT; e_id INT; err TEXT;
BEGIN
  BEGIN
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'EXPENSE','OUT',100)
    RETURNING id INTO f_id;
    INSERT INTO expenses(expense_date,category_id,amount,description,scope,bus_id,
      payment_source,financial_account_id,financial_transaction_id)
    VALUES (CURRENT_DATE,(SELECT id FROM expense_categories WHERE name='Maintenance'),
      100,'SF022 Bus A part','BUS',
      (SELECT id FROM buses WHERE registration_number='SF022-TEST-A'),
      'BUSINESS_ACCOUNT',(SELECT id FROM financial_accounts WHERE name='Cash'),f_id)
    RETURNING id INTO e_id;
    INSERT INTO maintenance(bus_id,maintenance_type,description,reported_date,expense_id)
    VALUES ((SELECT id FROM buses WHERE registration_number='SF022-TEST-B'),
      'UNPLANNED','SF022 wrong bus expense',CURRENT_DATE,e_id);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='WRONG-BUS maintenance link was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('11 wrong-bus maintenance expense rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%another bus%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 12: Legitimate no-cost maintenance must be permitted without an expense.
DO $test$
DECLARE err TEXT;
BEGIN
  BEGIN
    INSERT INTO maintenance(bus_id,maintenance_type,description,reported_date,
      status,completed_date)
    VALUES ((SELECT id FROM buses WHERE registration_number='SF022-TEST-A'),
      'PLANNED','SF022 complimentary check',CURRENT_DATE,'COMPLETED',CURRENT_DATE);
    SET CONSTRAINTS ALL IMMEDIATE;
    INSERT INTO sf_test_results VALUES ('12 no-cost completed maintenance','PASS','No expense needed for complimentary inspection');
    SET CONSTRAINTS ALL DEFERRED;
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('12 no-cost completed maintenance','FAIL',err);
  END;
END $test$;

-- 13: Changing a business record refreshes updated_at automatically.
DO $test$
DECLARE bus_id INT; changed TIMESTAMP; err TEXT;
BEGIN
  BEGIN
    SELECT id INTO bus_id FROM buses WHERE registration_number='SF022-TEST-A';
    UPDATE buses SET updated_at='2000-01-01 00:00:00' WHERE id=bus_id;
    SELECT updated_at INTO changed FROM buses WHERE id=bus_id;
    IF changed < '2020-01-01'::timestamp THEN
       RAISE EXCEPTION 'updated_at trigger did not update timestamp';
    END IF;
    INSERT INTO sf_test_results VALUES ('13 automatic updated_at','PASS','Trigger refreshed timestamp');
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('13 automatic updated_at','FAIL',err);
  END;
END $test$;

-- 14: An active fee band cannot overlap another active band of same transfer type.
DO $test$
DECLARE err TEXT;
BEGIN
  BEGIN
    INSERT INTO transfer_fee_rules(transfer_type,minimum_amount,maximum_amount,fee_amount)
    VALUES ('AIRTEL_TO_BANK',100,200,7);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='OVERLAPPING fee band accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('14 overlapping fee rule rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%overlaps another active%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 15: No overlapping historical date windows for a given cashing rate type.
DO $test$
DECLARE err TEXT;
BEGIN
  BEGIN
    INSERT INTO cashing_rates(rate_type,amount,active,effective_from,effective_to)
    VALUES ('NORMAL_DAY',700,FALSE,CURRENT_DATE-1,CURRENT_DATE+1);
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='OVERLAPPING cashing rates accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('15 overlapping cashing rate rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%overlaps another effective%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 16: Automatic fee function matches the configured tier.
DO $test$
DECLARE err TEXT;
BEGIN
  BEGIN
    IF sf_suggest_transfer_fee('AIRTEL_TO_BANK',5000) <> 50 OR
       sf_suggest_transfer_fee('AIRTEL_TO_BANK',5000.01) <> 100 OR
       sf_suggest_transfer_fee('AIRTEL_TO_AIRTEL',750) <> 6 OR
       sf_suggest_transfer_fee('AIRTEL_TO_AIRTEL',10001) IS NOT NULL THEN
         RAISE EXCEPTION 'Transfer fee suggestion did not match config';
    END IF;
    INSERT INTO sf_test_results VALUES ('16 fee suggestion calculations','PASS','Boundary amounts and manual-fee range correct');
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('16 fee suggestion calculations','FAIL',err);
  END;
END $test$;

-- 17: An inactive employment must not retain an ACTIVE bus assignment.
DO $test$
DECLARE emp INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver Two';
  BEGIN
    INSERT INTO driver_assignments(employment_id,bus_id,assignment_type,start_date,status)
    VALUES (emp,(SELECT id FROM buses WHERE registration_number='SF022-TEST-B'),
      'PERMANENT',CURRENT_DATE,'ACTIVE');
    UPDATE driver_employments SET status='TERMINATED',end_date=CURRENT_DATE
      WHERE id=emp;
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='TERMINATED driver kept active assignment';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('17 terminated assignment rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%conflicts with its bus assignment%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

-- 18: Advance recoveries paid via multiple salary records may not exceed the advance.
DO $test$
DECLARE emp INT; a_id INT; f_id INT; sal_id INT; err TEXT;
BEGIN
  SELECT e.id INTO emp FROM driver_employments e JOIN drivers d ON d.id=e.driver_id
    WHERE d.full_name='SF022 Test Driver One';
  SELECT id INTO a_id FROM driver_advances WHERE employment_id=emp ORDER BY id DESC LIMIT 1;
  BEGIN
    INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount)
    VALUES ((SELECT id FROM financial_accounts WHERE name='Cash'),CURRENT_DATE,'DRIVER_SALARY','OUT',1599)
    RETURNING id INTO f_id;
    INSERT INTO driver_salaries(employment_id,salary_year,salary_month,base_salary,prorated_salary,
      advance_recovery,status,payment_date,financial_transaction_id)
    VALUES (emp,2098,4,2000,2000,401,'PAID',CURRENT_DATE,f_id) RETURNING id INTO sal_id;
    INSERT INTO salary_advance_recoveries(salary_id,advance_id,amount) VALUES (sal_id,a_id,401);
    -- K401 alone exceeds the K400 advance, independently of earlier test outcomes.
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION USING ERRCODE='ZX001', MESSAGE='OVER-RECOVERY was accepted';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS err = MESSAGE_TEXT;
    INSERT INTO sf_test_results VALUES ('18 advance over-recovery rejected',
       CASE WHEN SQLSTATE <> 'ZX001' AND (err LIKE '%over-recovered%') THEN 'PASS' ELSE 'FAIL' END,err);
  END;
END $test$;

\echo
\echo ========== SMARTFLEET SCHEMA V1 TEST RESULTS ==========
SELECT test_name, result, detail FROM sf_test_results ORDER BY test_name;
SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE result='PASS') AS passed,
       COUNT(*) FILTER (WHERE result='FAIL') AS failed FROM sf_test_results;
\echo =====================================================
\echo ALL TEMPORARY DATA WILL BE DISCARDED NOW
ROLLBACK;
\echo Returned to original database state. Do not COMMIT test data.
