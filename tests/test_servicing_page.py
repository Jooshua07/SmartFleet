from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import components.servicing_form

PAGE=Path(__file__).resolve().parents[1]/'app_pages/record_servicing.py'


class ServicingPageTest(unittest.TestCase):
    def test_human_cost_entry_submit_and_clear(self):
        buses=[{'id':1,'registration_number':'ABC123'}]
        with patch('services.bus_service.get_all_buses',return_value=buses), \
             patch('services.maintenance_service.get_servicing_history',return_value=[]), \
             patch('components.servicing_form.record_servicing',return_value={'id':1}) as save:
            app=AppTest.from_file(PAGE).run()
            self.assertFalse(app.exception)
            app.number_input[0].set_value(100)
            app.number_input[1].set_value(50)
            app.run()
            self.assertEqual(app.metric[0].value,'K150')
            next(button for button in app.button if button.label=='Record servicing').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success)
            self.assertEqual(app.number_input[0].value,0)
            self.assertEqual(app.number_input[1].value,0)
            self.assertEqual(save.call_count,1)

    def test_invalid_save_displays_safe_error(self):
        with patch('services.bus_service.get_all_buses',return_value=[{'id':1,'registration_number':'ABC123'}]), \
             patch('services.maintenance_service.get_servicing_history',return_value=[]), \
             patch('components.servicing_form.record_servicing',side_effect=ValueError('Servicing is already recorded.')):
            app=AppTest.from_file(PAGE).run()
            next(button for button in app.button if button.label=='Record servicing').click().run()
            self.assertTrue(app.error)
            self.assertFalse(app.exception)
