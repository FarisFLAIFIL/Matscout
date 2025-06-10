# This file will contain tests for the MaterialsAgent class.

import unittest
from unittest.mock import MagicMock, patch, mock_open
import os # For path manipulation in _load_demo_data tests

from materiascout.materials_agent import MaterialsAgent
from materiascout.element_extractor import ElementExtractor # For spec
from materiascout.mcp_client import MaterialsProjectMCPClient # For spec

class TestMaterialsAgent(unittest.TestCase):
    def setUp(self):
        """Instantiate MaterialsAgent with mock dependencies for each test."""
        self.mock_extractor = MagicMock(spec=ElementExtractor)
        self.mock_client = MagicMock(spec=MaterialsProjectMCPClient)

        # Default to demo_mode=False for most tests.
        # Tests for demo mode will re-initialize or modify the agent.
        self.agent = MaterialsAgent(
            mcp_client=self.mock_client,
            element_extractor=self.mock_extractor,
            demo_mode=False
        )

    # --- Test Live Mode (demo_mode=False) ---
    def test_perform_query_live_success(self):
        """Test successful query in live mode."""
        nl_query = "Find materials with iron and oxygen"
        properties = ["material_id", "formula_pretty"]
        extracted_els = ["Fe", "O"]
        client_response_data = [{"material_id": "mp-1", "formula_pretty": "Fe2O3"}]

        self.mock_extractor.extract_elements.return_value = extracted_els
        self.mock_client.get_materials_data.return_value = client_response_data

        result = self.agent.perform_query(nl_query, properties)

        self.mock_extractor.extract_elements.assert_called_once_with(nl_query)
        # Criteria string for "Fe", "O" is "Fe-O" (sorted)
        self.mock_client.get_materials_data.assert_called_once_with(
            criteria="Fe-O", properties=properties
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], client_response_data)
        self.assertEqual(result["extracted_elements"], extracted_els)
        self.assertIn("Successfully retrieved 1 material(s)", result["message"])

    def test_perform_query_live_single_element_criteria(self):
        """Test live query with a single extracted element forming the criteria."""
        nl_query = "Data for SiC"
        properties = ["band_gap"]
        extracted_els = ["SiC"] # Element extractor might return formula directly
        client_response_data = [{"material_id": "mp-SiC", "formula_pretty": "SiC", "band_gap": 3.0}]

        self.mock_extractor.extract_elements.return_value = extracted_els
        self.mock_client.get_materials_data.return_value = client_response_data

        result = self.agent.perform_query(nl_query, properties)
        self.mock_client.get_materials_data.assert_called_once_with(
            criteria="SiC", properties=properties
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], client_response_data)


    def test_perform_query_live_element_extraction_fails(self):
        """Test live query when element extraction returns no elements."""
        nl_query = "gibberish"
        properties = ["material_id"]
        self.mock_extractor.extract_elements.return_value = [] # No elements found

        result = self.agent.perform_query(nl_query, properties)

        self.mock_extractor.extract_elements.assert_called_once_with(nl_query)
        self.mock_client.get_materials_data.assert_not_called()
        self.assertEqual(result["status"], "no_results")
        self.assertIn("No chemical elements or formulas found", result["message"])
        self.assertEqual(result["data"], [])

    def test_perform_query_live_client_returns_no_data(self):
        """Test live query when client returns an empty list (no materials found)."""
        nl_query = "Unobtainium"
        properties = ["material_id"]
        extracted_els = ["Un"]

        self.mock_extractor.extract_elements.return_value = extracted_els
        self.mock_client.get_materials_data.return_value = [] # Client finds nothing

        result = self.agent.perform_query(nl_query, properties)

        self.assertEqual(result["status"], "no_results")
        self.assertIn("No materials found for criteria 'Un'", result["message"])
        self.assertEqual(result["data"], [])

    def test_perform_query_live_client_returns_error_none(self):
        """Test live query when client returns None (indicating an error)."""
        nl_query = "Iron"
        properties = ["material_id"]
        extracted_els = ["Fe"]

        self.mock_extractor.extract_elements.return_value = extracted_els
        self.mock_client.get_materials_data.return_value = None # Client error

        result = self.agent.perform_query(nl_query, properties)

        self.assertEqual(result["status"], "error")
        self.assertIn("Error occurred while fetching data", result["message"])
        self.assertEqual(result["data"], [])

    def test_perform_query_live_extractor_raises_exception(self):
        """Test live query when element extractor raises an exception."""
        nl_query = "Anything"
        properties = ["material_id"]
        self.mock_extractor.extract_elements.side_effect = Exception("Extractor boom!")

        result = self.agent.perform_query(nl_query, properties)

        self.assertEqual(result["status"], "error")
        self.assertIn("An unexpected error occurred", result["message"])
        self.assertIn("Extractor boom!", result["message"])
        self.mock_client.get_materials_data.assert_not_called()

    def test_perform_query_live_client_raises_exception(self):
        """Test live query when MCP client raises an exception."""
        nl_query = "Iron"
        properties = ["material_id"]
        extracted_els = ["Fe"]

        self.mock_extractor.extract_elements.return_value = extracted_els
        self.mock_client.get_materials_data.side_effect = Exception("Client boom!")

        result = self.agent.perform_query(nl_query, properties)

        self.assertEqual(result["status"], "error")
        self.assertIn("An unexpected error occurred", result["message"])
        self.assertIn("Client boom!", result["message"])


    # --- Test Demo Mode (demo_mode=True) ---
    def setup_demo_agent(self, demo_data):
        """Helper to create an agent in demo mode with specific demo_data."""
        # Patch _load_demo_data to prevent file access and control demo_data directly
        with patch.object(MaterialsAgent, '_load_demo_data', MagicMock()) as mock_load_method:
            agent_demo = MaterialsAgent(
                mcp_client=self.mock_client, # Still needs a client object, though not used
                element_extractor=self.mock_extractor,
                demo_mode=True
            )
            # Manually set demo_data after init because _load_demo_data is mocked
            agent_demo.demo_data = demo_data
            mock_load_method.assert_called_once() # Ensure __init__ tried to load
        return agent_demo

    def test_perform_query_demo_success_matching_data(self):
        """Test successful query in demo mode with matching data."""
        nl_query = "Iron and Oxygen"
        properties = ["material_id", "formula_pretty", "band_gap"]
        extracted_els = ["Fe", "O"] # Mock extractor output

        sample_demo_data = [
            {"material_id": "dm-1", "formula_pretty": "Fe2O3", "elements": ["Fe", "O"], "band_gap": 2.0, "density": 5.0},
            {"material_id": "dm-2", "formula_pretty": "SiO2", "elements": ["Si", "O"], "band_gap": 9.0},
            {"material_id": "dm-3", "formula_pretty": "FeO", "elements": ["Fe", "O"], "band_gap": 0.5, "volume": 20.0},
        ]
        agent_demo = self.setup_demo_agent(sample_demo_data)
        self.mock_extractor.extract_elements.return_value = extracted_els

        result = agent_demo.perform_query(nl_query, properties)

        self.mock_extractor.extract_elements.assert_called_once_with(nl_query)
        self.mock_client.get_materials_data.assert_not_called() # Client should not be called in demo

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        # Check if correct items are returned and properties are selected
        expected_data = [
            {"material_id": "dm-1", "formula_pretty": "Fe2O3", "band_gap": 2.0},
            {"material_id": "dm-3", "formula_pretty": "FeO", "band_gap": 0.5},
        ]
        self.assertCountEqual(result["data"], expected_data) # Use assertCountEqual for list of dicts
        self.assertIn("Demo mode: Found 2 matching materials", result["message"])

    def test_perform_query_demo_formula_match(self):
        """Test demo query matching a formula_pretty directly."""
        nl_query = "Fe2O3"
        properties = ["material_id", "density"]
        extracted_els = ["Fe2O3"] # Extractor might return the formula itself
        sample_demo_data = [
            {"material_id": "dm-1", "formula_pretty": "Fe2O3", "elements": ["Fe", "O"], "density": 5.0},
            {"material_id": "dm-2", "formula_pretty": "SiO2", "elements": ["Si", "O"], "density": 2.5},
        ]
        agent_demo = self.setup_demo_agent(sample_demo_data)
        self.mock_extractor.extract_elements.return_value = extracted_els

        result = agent_demo.perform_query(nl_query, properties)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0], {"material_id": "dm-1", "density": 5.0})


    def test_perform_query_demo_no_matching_data(self):
        """Test demo query with no matching materials in demo_data."""
        nl_query = "Gold"
        properties = ["material_id"]
        extracted_els = ["Au"]
        sample_demo_data = [{"material_id": "dm-1", "formula_pretty": "NaCl", "elements": ["Na", "Cl"]}]
        agent_demo = self.setup_demo_agent(sample_demo_data)
        self.mock_extractor.extract_elements.return_value = extracted_els

        result = agent_demo.perform_query(nl_query, properties)

        self.assertEqual(result["status"], "no_results")
        self.assertIn("No materials found containing all elements: Au", result["message"])
        self.assertEqual(result["data"], [])

    def test_perform_query_demo_property_selection(self):
        """Test that demo mode correctly selects only requested properties and adds material_id."""
        nl_query = "NaCl"
        properties_to_fetch = ["band_gap", "density", "non_existent_prop"]
        extracted_els = ["NaCl"]
        sample_demo_data = [
            {"material_id": "dm-NaCl", "formula_pretty": "NaCl", "elements": ["Na", "Cl"],
             "band_gap": 5.0, "density": 2.16, "volume": 40.0}
        ]
        agent_demo = self.setup_demo_agent(sample_demo_data)
        self.mock_extractor.extract_elements.return_value = extracted_els

        result = agent_demo.perform_query(nl_query, properties_to_fetch)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        expected_material_data = {
            "material_id": "dm-NaCl", # Always included
            "band_gap": 5.0,
            "density": 2.16,
            "non_existent_prop": None # .get() behavior
        }
        self.assertDictEqual(result["data"][0], expected_material_data)

    def test_perform_query_demo_no_demo_data_loaded(self):
        """Test demo mode when demo_data list is empty."""
        nl_query = "Anything"
        properties = ["material_id"]
        extracted_els = ["Any"]
        agent_demo = self.setup_demo_agent([]) # No demo data
        self.mock_extractor.extract_elements.return_value = extracted_els

        result = agent_demo.perform_query(nl_query, properties)
        self.assertEqual(result["status"], "no_results")
        self.assertIn("No demo data loaded or available", result["message"])


    # --- Test __init__ for Demo Mode Data Loading ---
    @patch('builtins.open', new_callable=mock_open, read_data='[{"material_id": "dm-test", "elements": ["Test"]}]')
    @patch('os.path.abspath') # Mock abspath to control the base path for demo data
    @patch('os.path.join') # Mock join to verify path construction
    def test_init_demo_mode_loads_data_success(self, mock_os_join, mock_os_abspath, mock_file_open):
        """Test that __init__ calls _load_demo_data and loads data in demo mode."""
        # Define what os.path.abspath and os.path.join should return to form the expected path
        mock_os_abspath.return_value = "/mock/base/dir/materiascout"
        expected_demo_file_path = "/mock/base/dir/materiascout/data/demo_materials.json"
        mock_os_join.return_value = expected_demo_file_path

        agent_demo = MaterialsAgent(MagicMock(), MagicMock(), demo_mode=True)

        mock_file_open.assert_called_once_with(expected_demo_file_path, 'r')
        self.assertEqual(len(agent_demo.demo_data), 1)
        self.assertEqual(agent_demo.demo_data[0]["material_id"], "dm-test")

    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('os.path.abspath')
    @patch('os.path.join')
    def test_init_demo_mode_load_data_file_not_found(self, mock_os_join, mock_os_abspath, mock_file_open):
        """Test _load_demo_data handling FileNotFoundError."""
        mock_os_abspath.return_value = "/mock/base/dir/materiascout"
        mock_os_join.return_value = "/mock/base/dir/materiascout/data/demo_materials.json"

        # Suppress print warning during test
        with patch('builtins.print') as mock_print:
            agent_demo = MaterialsAgent(MagicMock(), MagicMock(), demo_mode=True)

        self.assertEqual(agent_demo.demo_data, [])
        mock_print.assert_any_call(unittest.mock.ANY) # Check that a warning was printed

    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('os.path.abspath')
    @patch('os.path.join')
    def test_init_demo_mode_load_data_json_error(self, mock_os_join, mock_os_abspath, mock_file_open):
        """Test _load_demo_data handling JSONDecodeError."""
        mock_os_abspath.return_value = "/mock/base/dir/materiascout"
        mock_os_join.return_value = "/mock/base/dir/materiascout/data/demo_materials.json"

        with patch('builtins.print') as mock_print:
            agent_demo = MaterialsAgent(MagicMock(), MagicMock(), demo_mode=True)

        self.assertEqual(agent_demo.demo_data, [])
        mock_print.assert_any_call(unittest.mock.ANY) # Check that a warning was printed


if __name__ == "__main__":
    unittest.main()
