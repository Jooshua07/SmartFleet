"use strict";
const invoiceForm = document.querySelector('.complete-cashing');
if (invoiceForm) {
  const money = cents => 'K ' + (cents / 100).toLocaleString('en-ZM', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const amount = input => {
    const value = input?.value ?? '';
    const [mantissa, exponent = '0'] = value.toLowerCase().split('e');
    const precision = (mantissa.split('.')[1]?.length || 0) - Number(exponent);
    const number = Number(value);
    return value !== '' && Number.isFinite(number) && number >= 0 && number < 1000000000 && precision <= 2 ? Math.round(number * 100) : null;
  };
  const date = invoiceForm.querySelector('#collection_date');
  invoiceForm.querySelector('#load-invoice-date').addEventListener('click', () => {
    window.location.assign('/record-cashing?date=' + encodeURIComponent(date.value));
  });
  function updateInvoice() {
    const adjusted = invoiceForm.querySelector('[name="mode"]:checked')?.value === 'ADJUSTED';
    let total = 0, complete = true;
    invoiceForm.querySelectorAll('.cashing-choice').forEach(card => {
      const bid = card.dataset.id;
      const checkbox = card.querySelector('[name="adjust_ids"]');
      const selected = adjusted && checkbox.checked;
      card.querySelector('[data-adjust-toggle]').hidden = !adjusted;
      card.querySelector('[data-adjust-fields]').hidden = !selected;
      card.classList.toggle('is-adjusted', selected);
      let expected = Number(card.dataset.standard), actual = expected;
      if (selected) {
        const days = Number(card.querySelector('[name="days_' + bid + '"]').value);
        const sunday = card.querySelector('[data-add-sunday]')?.checked;
        expected = days * Number(card.dataset.normalRate) + (sunday ? Number(card.dataset.sundayRate) : 0);
        const normal = amount(card.querySelector('[name="amount_' + bid + '"]'));
        const sundayAmount = sunday ? amount(card.querySelector('[name="sunday_amount_' + bid + '"]')) : 0;
        actual = normal === null || sundayAmount === null ? null : normal + sundayAmount;
        const sundayInput = card.querySelector('[data-sunday-input]');
        if (sundayInput) sundayInput.hidden = !sunday;
        const differs = actual !== expected || days !== Number(card.dataset.days);
        card.querySelector('[data-difference-controls]').hidden = !differs;
        const classification = card.querySelector('[name="classification_' + bid + '"]');
        const responsibility = differs && classification.value === 'CONFIRMED_UNPAID_OBLIGATION';
        card.querySelector('[data-responsibility]').hidden = !responsibility;
        card.querySelector('[name="responsible_' + bid + '"]').required = responsibility;
        card.querySelector('[name="explanation_' + bid + '"]').required = differs;
      }
      card.querySelector('[data-expected]').textContent = money(expected);
      card.querySelector('[data-actual]').textContent = actual === null ? 'Enter amount' : money(actual);
      if (actual === null) complete = false;
      else total += actual;
      checkbox.disabled = !adjusted;
      card.querySelectorAll('[data-adjust-fields] input,[data-adjust-fields] select').forEach(input => {
        input.disabled = !!input.closest('[hidden]');
      });
    });
    const output = invoiceForm.querySelector('#invoice-total');
    if (output) output.textContent = complete ? money(total) : 'Enter adjusted amounts';
    const submit = invoiceForm.querySelector('[type="submit"]');
    if (submit) submit.disabled = date.value !== invoiceForm.dataset.loadedDate || !invoiceForm.querySelector('.cashing-choice');
  }
  invoiceForm.addEventListener('input', updateInvoice);
  invoiceForm.addEventListener('change', updateInvoice);
  updateInvoice();
}
