import streamlit as st

from utils.help_content import CATEGORIES, SECTIONS, filter_guides


st.subheader('Welcome to SmartFleet')
st.write('Keep your buses, cashing, costs, servicing and business money records together. Record what actually happened and check the dates before saving.')

with st.expander('Getting Started'):
    st.markdown('1. **Home:** see the business summary, financial graph and reminders.\n'
                '2. **Buses:** manage registrations, routes, drivers and active history.\n'
                '3. **Finance:** see collections, costs, payments and the current business balance.\n'
                '4. **More:** record transactions, servicing, driver/loan/owner money, reports and backups.')

query = st.text_input('Search guides', placeholder='Try servicing, salary, October or balance', key='help_search')
category = st.selectbox('Category', ('All', *CATEGORIES), key='help_category')
guides = filter_guides(query, category)
if not guides:
    st.info('No matching guides. Try another word or choose All categories.')
for section in SECTIONS:
    matching = [guide for guide in guides if guide.section == section]
    if matching:
        st.subheader(section)
        for guide in matching:
            with st.expander(guide.question):
                st.markdown('\n'.join(f'{index}. {step}' for index, step in enumerate(guide.steps, 1)))
                if guide.example:
                    st.write(guide.example)
                if guide.note:
                    st.caption(guide.note)
