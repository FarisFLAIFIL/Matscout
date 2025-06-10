# This file will contain tests for the MaterialsProjectMCPClient class.

import os
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from materiascout.mcp_client import MaterialsProjectMCPClient
# Assuming MPRester is imported in mcp_client from mp_api.client
# We'll patch 'materiascout.mcp_client.MPRester'

# Mock Pydantic model if necessary for simulating MPRester responses
class MockMaterialDoc:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        # Add a 'formula_pretty' attribute if 'formula_alphabetical' is provided, common in MP docs
        if 'formula_alphabetical' in kwargs and 'formula_pretty' not in kwargs:
            self.formula_pretty = kwargs['formula_alphabetical']


    def model_dump(self): # Renamed from as_dict() to match pydantic v2
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class TestMaterialsProjectMCPClient(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True) # Start with a clean environment
    @patch('materiascout.mcp_client.MPRester')
    def test_init_with_api_key_arg(self, MockMPRester):
        """Test initialization with API key provided as argument."""
        mock_mpr_instance = MockMPRester.return_value
        client = MaterialsProjectMCPClient(api_key="test_key_arg")
        MockMPRester.assert_called_once_with("test_key_arg")
        self.assertEqual(client.api_key, "test_key_arg")
        self.assertIsNotNone(client.mpr)

    @patch.dict(os.environ, {"MP_API_KEY": "test_key_env"}, clear=True)
    @patch('materiascout.mcp_client.MPRester')
    def test_init_with_api_key_env(self, MockMPRester):
        """Test initialization with API key from environment variable."""
        mock_mpr_instance = MockMPRester.return_value
        client = MaterialsProjectMCPClient() # No API key arg
        MockMPRester.assert_called_once_with("test_key_env")
        self.assertEqual(client.api_key, "test_key_env")
        self.assertIsNotNone(client.mpr)

    @patch.dict(os.environ, {}, clear=True) # Ensure MP_API_KEY is not set
    @patch('materiascout.mcp_client.MPRester')
    def test_init_no_api_key(self, MockMPRester):
        """Test initialization fails if no API key is provided or in env."""
        with self.assertRaises(ValueError) as context:
            MaterialsProjectMCPClient()
        self.assertIn("API key must be provided", str(context.exception))
        MockMPRester.assert_not_called()

    @patch.dict(os.environ, {"MP_API_KEY": "bad_key"}, clear=True)
    @patch('materiascout.mcp_client.MPRester')
    def test_init_mprester_exception(self, MockMPRester):
        """Test handling of exception during MPRester initialization."""
        MockMPRester.side_effect = Exception("MPRester init failed")
        with self.assertRaises(Exception) as context:
            MaterialsProjectMCPClient()
        self.assertIn("MPRester init failed", str(context.exception))

    @patch('materiascout.mcp_client.MPRester')
    def setUp(self, MockMPRester): # Patched here to be available in all tests if needed
        """Common setup for tests: mock MPRester and initialize client."""
        self.mock_mpr_instance = MockMPRester.return_value
        # Mock the 'materials' attribute of MPRester instance, which is then used for 'search'
        self.mock_materials_search = MagicMock()
        self.mock_mpr_instance.materials.search = self.mock_materials_search

        # Initialize client with a dummy API key for most tests
        # Tests for __init__ specifically will handle their own client creation and MPRester mocking
        # For other tests, we assume client is successfully initialized.
        self.client = MaterialsProjectMCPClient(api_key="dummy_key_for_setup")
        # Reset call counts for MPRester that happened during setup's client init for method tests
        MockMPRester.reset_mock()
        self.mock_materials_search.reset_mock()


    def test_get_materials_data_string_criteria_formula(self):
        """Test get_materials_data with a string formula criterion."""
        mock_response = [
            MockMaterialDoc(material_id="mp-1", formula_pretty="Fe2O3", band_gap=2.0),
            MockMaterialDoc(material_id="mp-2", formula_pretty="Fe3O4", band_gap=0.1)
        ]
        self.mock_materials_search.return_value = mock_response

        criteria = "Fe2O3"
        properties = ["material_id", "formula_pretty", "band_gap"]
        result = self.client.get_materials_data(criteria, properties)

        self.mock_materials_search.assert_called_once_with(
            formula=criteria, material_ids=None, chemsys=None, fields=properties
        )
        expected_result = [doc.model_dump() for doc in mock_response]
        self.assertEqual(result, expected_result)

    def test_get_materials_data_string_criteria_material_id(self):
        """Test get_materials_data with a string material_id criterion."""
        mock_response = [MockMaterialDoc(material_id="mp-123", formula_pretty="Si", density=2.3)]
        self.mock_materials_search.return_value = mock_response

        criteria = "mp-123"
        properties = ["material_id", "formula_pretty", "density"]
        result = self.client.get_materials_data(criteria, properties)

        self.mock_materials_search.assert_called_once_with(
            formula=None, material_ids=criteria, chemsys=None, fields=properties
        )
        self.assertEqual(result, [doc.model_dump() for doc in mock_response])

    def test_get_materials_data_string_criteria_chemsys(self):
        """Test get_materials_data with a string chemsys criterion."""
        mock_response = [MockMaterialDoc(material_id="mp-1", elements=["Fe","O"], volume=100)]
        self.mock_materials_search.return_value = mock_response

        criteria = "Fe-O"
        properties = ["material_id", "elements", "volume"]
        result = self.client.get_materials_data(criteria, properties)

        self.mock_materials_search.assert_called_once_with(
            formula=None, material_ids=None, chemsys=criteria, fields=properties
        )
        self.assertEqual(result, [doc.model_dump() for doc in mock_response])


    def test_get_materials_data_list_criteria(self):
        """Test get_materials_data with a list of material_ids."""
        mock_response = [MockMaterialDoc(material_id="mp-1"), MockMaterialDoc(material_id="mp-2")]
        self.mock_materials_search.return_value = mock_response

        criteria = ["mp-1", "mp-2"]
        properties = ["material_id"]
        result = self.client.get_materials_data(criteria, properties)

        self.mock_materials_search.assert_called_once_with(material_ids=criteria, fields=properties)
        self.assertEqual(result, [doc.model_dump() for doc in mock_response])

    def test_get_materials_data_dict_criteria(self):
        """Test get_materials_data with dictionary criteria."""
        mock_response = [MockMaterialDoc(elements=["Li", "Fe", "O"], band_gap=1.0)]
        self.mock_materials_search.return_value = mock_response

        criteria = {"elements": ["Li", "Fe", "O"], "band_gap": (0.5, 1.5)}
        properties = ["elements", "band_gap"]
        result = self.client.get_materials_data(criteria, properties)

        self.mock_materials_search.assert_called_once_with(**criteria, fields=properties)
        self.assertEqual(result, [doc.model_dump() for doc in mock_response])

    def test_get_materials_data_api_error(self):
        """Test get_materials_data when MPRester raises an API error."""
        self.mock_materials_search.side_effect = Exception("API Error") # Simulate MPRester error

        result = self.client.get_materials_data("Fe2O3", ["material_id"])
        self.assertIsNone(result)

    def test_get_materials_data_no_results(self):
        """Test get_materials_data when API returns no results."""
        self.mock_materials_search.return_value = [] # Empty list from API

        result = self.client.get_materials_data("NonExistentFormula", ["material_id"])
        self.assertEqual(result, [])

    def test_get_materials_data_unsupported_criteria_type(self):
        """Test get_materials_data with an unsupported criteria type."""
        result = self.client.get_materials_data(12345, ["material_id"]) # Integer criteria
        self.assertIsNone(result)
        self.mock_materials_search.assert_not_called()

    def test_check_api_key_status_success(self):
        """Test check_api_key_status for a successful API call."""
        # Simulate a successful lightweight query for Si (mp-149)
        mock_si_data = [MockMaterialDoc(material_id="mp-149", formula_pretty="Si")]
        self.mock_materials_search.return_value = mock_si_data

        is_valid = self.client.check_api_key_status() # Now returns (bool, str)

        self.mock_materials_search.assert_called_once_with(
            material_ids="mp-149", fields=["material_id", "formula_pretty"]
        )
        self.assertTrue(is_valid) # Only checking the boolean part for this test method

    def test_check_api_key_status_failure_exception(self):
        """Test check_api_key_status when the API call fails (raises exception)."""
        self.mock_materials_search.side_effect = Exception("Simulated API error")

        is_valid = self.client.check_api_key_status()
        self.assertFalse(is_valid)

    def test_check_api_key_status_failure_no_data(self):
        """Test check_api_key_status when the API call returns no data (unexpected for mp-149)."""
        self.mock_materials_search.return_value = [] # Empty list for Si query

        is_valid = self.client.check_api_key_status()
        self.assertFalse(is_valid)

    def test_mpr_not_initialized_get_materials_data(self):
        """Test get_materials_data if mpr is not initialized."""
        # Temporarily break the client's mpr instance for this test
        original_mpr = self.client.mpr
        self.client.mpr = None

        result = self.client.get_materials_data("Fe2O3", ["material_id"])
        self.assertIsNone(result)

        self.client.mpr = original_mpr # Restore


if __name__ == "__main__":
    unittest.main()
