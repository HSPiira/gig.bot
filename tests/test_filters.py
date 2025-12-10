import unittest
import unittest.mock # Import unittest.mock
from core.filters import keyword_score_and_filter, extract_budget_info, looks_like_gig
from core.config import config # To access test keywords

class TestFilters(unittest.TestCase):

    def setUp(self):
        # Set up some test config values for keywords
        config._data["weighted_keywords"] = {
            "freelance": 5, "project": 3, "hiring": 2, "developer": 3,
            "urgent": 1, "budget": 2, "pay": 2
        }
        config._data["negative_keywords"] = [
            "recruitment agency", "full-time", "permanent position", "internship"
        ]

    def test_keyword_score_and_filter_negative_keywords(self):
        text = "Looking for a full-time developer at a recruitment agency."
        score, is_gig = keyword_score_and_filter(text)
        self.assertFalse(is_gig)
        self.assertEqual(score, 0.0)

        text = "Internship opportunity available."
        score, is_gig = keyword_score_and_filter(text)
        self.assertFalse(is_gig)
        self.assertEqual(score, 0.0)

    def test_keyword_score_and_filter_positive_keywords(self):
        text = "Freelance developer needed for a project."
        score, is_gig = keyword_score_and_filter(text)
        self.assertTrue(is_gig)
        self.assertGreater(score, 0.0)
        self.assertEqual(score, 5 + 3 + 3) # freelance + project + developer

        text = "Urgent hiring for a software project."
        score, is_gig = keyword_score_and_filter(text)
        self.assertTrue(is_gig)
        self.assertGreater(score, 0.0)
        self.assertEqual(score, 1 + 2 + 3) # urgent + hiring + project

    def test_keyword_score_and_filter_no_keywords(self):
        text = "This is a random sentence about nothing important."
        score, is_gig = keyword_score_and_filter(text)
        self.assertFalse(is_gig)
        self.assertEqual(score, 0.0)

    def test_extract_budget_info_single_amount(self):
        # Test single amount with currency symbol
        info = extract_budget_info("Budget: $500")
        self.assertEqual(info, {"amount": 500.0, "currency": "USD", "type": "fixed_price"})

        info = extract_budget_info("Pay is 1000 UGX")
        self.assertEqual(info, {"amount": 1000.0, "currency": "UGX", "type": "fixed_price"})

        info = extract_budget_info("Fee of €250")
        self.assertEqual(info, {"amount": 250.0, "currency": "EUR", "type": "fixed_price"})
        
        info = extract_budget_info("Budget: 5k")
        self.assertEqual(info, {"amount": 5000.0, "currency": None, "type": "fixed_price"}) # Updated expectation for 'k' currency
        
        info = extract_budget_info("Pay is 1m")
        self.assertEqual(info, {"amount": 1000000.0, "currency": None, "type": "fixed_price"}) # 'm' without explicit currency

        info = extract_budget_info("Job pays 50000")
        self.assertEqual(info, {"amount": 50000.0, "currency": None, "type": "fixed_price"})

    def test_extract_budget_info_range(self):
        # Test range with currency symbol
        info = extract_budget_info("Budget: $100-200")
        self.assertEqual(info, {"amount_min": 100.0, "amount_max": 200.0, "currency": "USD", "type": "range"})

        info = extract_budget_info("50 to 150 EUR")
        self.assertEqual(info, {"amount_min": 50.0, "amount_max": 150.0, "currency": "EUR", "type": "range"})

        info = extract_budget_info("Pay is 1k - 2k USD")
        self.assertEqual(info, {"amount_min": 1000.0, "amount_max": 2000.0, "currency": "USD", "type": "range"})

        info = extract_budget_info("Budget between 10,000 and 20,000 UGX")
        self.assertEqual(info, {"amount_min": 10000.0, "amount_max": 20000.0, "currency": "UGX", "type": "range"})
        
        info = extract_budget_info("1.5m - 2.5m")
        self.assertEqual(info, {"amount_min": 1500000.0, "amount_max": 2500000.0, "currency": None, "type": "range"})

    def test_extract_budget_info_no_budget(self):
        info = extract_budget_info("Just a plain text message.")
        self.assertEqual(info, {})

    @unittest.mock.patch('core.filters.pipeline') # Patch the pipeline function
    def test_looks_like_gig_nlp_positive(self, mock_pipeline):
        # Configure the mock pipeline to return a mock classifier
        mock_classifier_instance = unittest.mock.MagicMock(return_value={"labels": ["freelance gig", "discussion"], "scores": [0.8, 0.2]})
        mock_pipeline.return_value = mock_classifier_instance
        
        # This text should pass keyword filter and then NLP
        text = "Looking for a freelance graphic designer."
        self.assertTrue(looks_like_gig(text))
        # Ensure classifier was called with the correct arguments
        mock_classifier_instance.assert_called_with(unittest.mock.ANY, ["freelance gig", "job offer", "advertisement", "discussion"])

    @unittest.mock.patch('core.filters.pipeline') # Patch the pipeline function
    def test_looks_like_gig_nlp_negative(self, mock_pipeline):
        # Configure the mock pipeline to return a mock classifier
        mock_classifier_instance = unittest.mock.MagicMock(return_value={"labels": ["discussion", "freelance gig"], "scores": [0.8, 0.2]})
        mock_pipeline.return_value = mock_classifier_instance
        
        # This text should pass keyword filter but fail NLP
        text = "Discussion about new project management tools."
        self.assertFalse(looks_like_gig(text))
        mock_classifier_instance.assert_called_with(unittest.mock.ANY, ["freelance gig", "job offer", "advertisement", "discussion"])

    @unittest.mock.patch('core.filters.pipeline') # Patch the pipeline function
    def test_looks_like_gig_keyword_negative_override_nlp(self, mock_pipeline):
        # This text should fail keyword filter due to negative keyword,
        # so NLP should not even be called effectively
        text = "Hiring a full-time developer for a project."
        self.assertFalse(looks_like_gig(text))
        # Assert that the NLP classifier was NOT called
        mock_pipeline.assert_not_called()

if __name__ == '__main__':
    unittest.main()