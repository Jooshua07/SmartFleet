import streamlit as st

from components.servicing_form import render_servicing_form
from services.maintenance_service import get_servicing_history
from utils.formatting import format_date, format_whole_kwacha


st.subheader('Record Servicing')
for key in st.session_state.pop('servicing_reset_keys', []):
    st.session_state.pop(key, None)
if st.session_state.pop('servicing_saved', False):
    st.success('Servicing saved and next due date updated.')
history = get_servicing_history(st.session_state.get('servicing_bus_id'))
edit_id = st.session_state.get('edit_servicing_id')
event = next((row for row in history if row['id']==edit_id), None)
render_servicing_form(event['bus_id'] if event else st.session_state.get('servicing_bus_id'), event)
if event and st.button('Cancel correction'):
    st.session_state.pop('edit_servicing_id',None)
    st.rerun()
st.subheader('Servicing history')
if not history:
    st.caption('No completed servicing recorded.')
for row in history:
    with st.expander(f"{row['registration_number']} | {format_date(row['completed_date'])}"):
        st.write(row['description'])
        st.write(f"Labour {format_whole_kwacha(row['labour_cost'])}, transport {format_whole_kwacha(row['transport_cost'])}, other {format_whole_kwacha(row['parts_cost'])}")
        st.write(f"Total: {format_whole_kwacha(row['total_cost'])}")
        st.caption(f"Paid: {format_date(row['payment_date'])}" if row['payment_date'] else 'No cash payment')
        if st.button('Correct servicing', icon=':material/edit:', key=f"correct_servicing_{row['id']}"):
            st.session_state.edit_servicing_id=row['id']
            st.rerun()
