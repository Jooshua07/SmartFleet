from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from utils.help_content import GUIDES, CATEGORIES, filter_guides


class HelpGuideTests(unittest.TestCase):
    def test_search_and_categories(self):
        self.assertEqual(len({guide.id for guide in GUIDES}),len(GUIDES))
        self.assertGreaterEqual(len(GUIDES),27)
        self.assertTrue(filter_guides('AIH 2715'))
        self.assertTrue(filter_guides('SALARY advance','Drivers'))
        self.assertFalse(filter_guides('xyznoresult'))
        self.assertTrue(all(guide.category=='Buses and servicing' for guide in filter_guides(category='Buses and servicing')))

    def test_page_search_filter_empty_and_restore(self):
        page=Path(__file__).resolve().parents[1]/'app_pages/help_guide.py'
        app=AppTest.from_file(page).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.expander),len(GUIDES)+1)
        app.text_input(key='help_search').set_value('advance').run()
        self.assertLess(len(app.expander),len(GUIDES)+1)
        app.selectbox(key='help_category').set_value('Drivers').run()
        self.assertTrue(any('salary' in item.label.lower() for item in app.expander))
        app.text_input(key='help_search').set_value('xyznoresult').run()
        self.assertTrue(app.info)
        app.text_input(key='help_search').set_value('').run()
        app.selectbox(key='help_category').set_value('All').run()
        self.assertEqual(len(app.expander),len(GUIDES)+1)
        self.assertFalse(app.exception)
