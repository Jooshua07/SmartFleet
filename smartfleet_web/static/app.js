"use strict";
if (window.lucide) window.lucide.createIcons();

function fitMetrics() {
  document.querySelectorAll('.metric-value').forEach(element => {
    let size = 22;
    element.style.fontSize = size + 'px';
    while (element.scrollWidth > element.clientWidth && size > 11) element.style.fontSize = (--size) + 'px';
  });
}
fitMetrics();
window.addEventListener('resize', fitMetrics);

const periodPicker = document.querySelector('.period-picker');
if (periodPicker) {
  function updatePeriod() {
    const custom = periodPicker.querySelector('[name="period"]:checked')?.value === 'custom';
    periodPicker.querySelector('[data-custom-period]').hidden = !custom;
    periodPicker.querySelector('[data-custom-dates]').hidden = !custom || periodPicker.querySelector('[name="custom"]').value !== 'dates';
  }
  periodPicker.addEventListener('change', updatePeriod);
  updatePeriod();
}

const cashingForm = document.querySelector('.cashing-entry');
if (cashingForm) {
  document.querySelector('#load-cashing-date').addEventListener('click', () => {
    const value = document.querySelector('#collection_date').value;
    window.location.assign(window.location.pathname + '?date=' + encodeURIComponent(value));
  });
  function updateCashing() {
    const adjusted = cashingForm.dataset.direct === 'true' || cashingForm.querySelector('[name="mode"]:checked')?.value === 'ADJUSTED';
    const selected = [...(cashingForm.querySelector('#bus_ids')?.selectedOptions || [])].map(o => o.value);
    const same = cashingForm.querySelector('#same_amount')?.checked;
    cashingForm.querySelectorAll('[data-bus]').forEach(row => { row.hidden = !selected.includes(row.dataset.bus); });
    cashingForm.querySelectorAll('[data-standard]').forEach(e => { e.hidden = adjusted; });
    cashingForm.querySelectorAll('[data-adjusted]').forEach(e => { e.hidden = !adjusted; });
    cashingForm.querySelectorAll('[data-common]').forEach(e => { e.hidden = !same; });
    cashingForm.querySelectorAll('[data-individual]').forEach(e => { e.hidden = !!same; });
    cashingForm.querySelectorAll('[data-sunday-amount]').forEach(e => { e.hidden = !e.parentElement.querySelector('[data-sunday]').checked; });
    cashingForm.querySelectorAll('input,select').forEach(e => { e.disabled = !!e.closest('[hidden]'); });
  }
  cashingForm.addEventListener('change', updateCashing);
  updateCashing();
}
