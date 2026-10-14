from decimal import Decimal
import streamlit as st

from services.bus_service import get_all_buses
from services.maintenance_service import record_servicing
from utils.dates import today_lusaka
from utils.formatting import format_whole_kwacha


def render_servicing_form(bus_id=None, event=None):
    buses = get_all_buses()
    if not buses:
        st.info('Register a bus before recording servicing.')
        return
    key = f"servicing_{event['id'] if event else 'new'}_{bus_id or 'all'}"
    options = {bus['id']:bus['registration_number'] for bus in buses}
    selected = st.selectbox('Bus', list(options), format_func=options.get,
        index=list(options).index(bus_id) if bus_id in options else 0, disabled=bus_id is not None,
        key=key+'_bus')
    completed = st.date_input('Actual completion date', value=event['completed_date'] if event else today_lusaka(),
        max_value=today_lusaka(), format='DD/MM/YYYY', key=key+'_completion')
    st.write(f"**{options[selected]} - Servicing - {completed:%d %b %Y}**")
    costs = []
    for label, field in [('Mechanic labour','labour_cost'),('Mechanic transport','transport_cost'),('Other servicing costs','parts_cost')]:
        costs.append(st.number_input(label+' (K)', min_value=0.0, value=float(event[field]) if event else 0.0,
            step=10.0, key=key+'_'+field))
    total = sum((Decimal(str(value)) for value in costs), Decimal('0'))
    st.metric('Total servicing cost', format_whole_kwacha(total))
    payment = st.date_input('Actual payment date', value=(event['payment_date'] if event and event['payment_date'] else completed),
        max_value=today_lusaka(), format='DD/MM/YYYY', key=key+'_payment') if total else None
    if total:
        st.caption('Record paid servicing here. Keep the actual completion and payment dates.')
    notes = st.text_area('Notes', value=(event['notes'] or '') if event else '', key=key+'_notes')
    reason = st.text_input('Correction reason', key=key+'_reason') if event else None
    if st.button('Save correction' if event else 'Record servicing', icon=':material/save:', type='primary', key=key+'_save'):
        try:
            record_servicing(selected, completed, *costs, payment_date=payment, notes=notes,
                event_id=event['id'] if event else None, reason=reason)
            st.cache_data.clear()
            st.session_state.pop('edit_servicing_id', None)
            st.session_state.servicing_saved = True
            for widget in list(st.session_state):
                if widget.startswith(key) and widget != key+'_save':
                    # Reset on the next rerun, before widgets are instantiated.
                    st.session_state.setdefault('servicing_reset_keys', []).append(widget)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
