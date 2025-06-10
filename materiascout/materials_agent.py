# This file will contain the AI agent logic for MateriaScout.

import os
import json
from materiascout.element_extractor import ElementExtractor
from materiascout.mcp_client import MaterialsProjectMCPClient

class MaterialsAgent:
    def __init__(self, mcp_client: MaterialsProjectMCPClient, element_extractor: ElementExtractor, demo_mode: bool = False):
        """
        Initializes the MaterialsAgent.

        Args:
            mcp_client: An instance of MaterialsProjectMCPClient.
            element_extractor: An instance of ElementExtractor.
            demo_mode: Boolean flag to enable/disable demo mode.
        """
        self.mcp_client = mcp_client
        self.element_extractor = element_extractor
        self.demo_mode = demo_mode
        self.demo_data = []

        if self.demo_mode:
            self._load_demo_data()

    def _load_demo_data(self):
        """
        Loads demo data from a JSON file.
        Handles errors if the file is not found or JSON is invalid.
        """
        # Construct the path relative to this file's directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        demo_data_path = os.path.join(base_dir, "data", "demo_materials.json")

        try:
            with open(demo_data_path, 'r') as f:
                self.demo_data = json.load(f)
            print(f"Demo mode: Successfully loaded {len(self.demo_data)} materials from {demo_data_path}")
        except FileNotFoundError:
            print(f"Warning: Demo data file not found at {demo_data_path}. Demo mode will use an empty dataset.")
            self.demo_data = []
        except json.JSONDecodeError:
            print(f"Warning: Error decoding JSON from {demo_data_path}. Demo mode will use an empty dataset.")
            self.demo_data = []
        except Exception as e:
            print(f"Warning: An unexpected error occurred while loading demo data: {e}. Demo mode will use an empty dataset.")
            self.demo_data = []

    def perform_query(self, natural_language_query: str, properties_to_fetch: list[str]) -> dict:
        """
        Performs a query based on natural language input to find materials data.
        Uses demo data if demo_mode is enabled.
        """
        result_template = {
            "status": "error",
            "message": "",
            "extracted_elements": [],
            "data": []
        }

        extracted_elements = self.element_extractor.extract_elements(natural_language_query)
        result_template["extracted_elements"] = extracted_elements

        if not extracted_elements:
            result_template["status"] = "no_results"
            result_template["message"] = "No chemical elements or formulas found in the query."
            return result_template

        if self.demo_mode:
            result_template["message"] = "Demo mode: Querying loaded sample data."

            if not self.demo_data:
                result_template["status"] = "no_results"
                result_template["message"] = "Demo mode: No demo data loaded or available."
                return result_template

            matched_materials = []
            for material in self.demo_data:
                # Check if all extracted elements are present in the material's "elements" list
                # This handles cases like "iron and oxygen" (must have both Fe, O)
                # and single element queries like "iron" or formulas like "Fe2O3".
                # For formulas, the ElementExtractor should ideally return the constituent elements
                # or the formula itself if it's a direct match.
                # Current simple check: if an extracted item is a formula, it won't match "elements" list.
                # This could be enhanced if ElementExtractor distinguishes elements from formulas.

                material_elements_set = set(material.get("elements", []))
                extracted_elements_set = set(extracted_elements)

                # If any of the extracted items look like a formula (e.g. Fe2O3),
                # check against 'formula_pretty' as well for a direct match.
                is_formula_match = False
                for ext_el in extracted_elements:
                    if ext_el == material.get("formula_pretty"):
                        is_formula_match = True
                        break

                if extracted_elements_set.issubset(material_elements_set) or is_formula_match:
                    # If it's a match, select only the requested properties
                    selected_data = {"material_id": material.get("material_id")} # Always include material_id
                    for prop in properties_to_fetch:
                        selected_data[prop] = material.get(prop) # get() returns None if prop not found
                    matched_materials.append(selected_data)

            if matched_materials:
                result_template["status"] = "success"
                result_template["data"] = matched_materials
                result_template["message"] = f"Demo mode: Found {len(matched_materials)} matching materials."
            else:
                result_template["status"] = "no_results"
                result_template["message"] = f"Demo mode: No materials found containing all elements: {', '.join(extracted_elements)} or matching formulas."
            return result_template

        # --- Live API Query Logic (unchanged from previous version) ---
        try:
            # (The following code is from the previous version for live API calls)
            if len(extracted_elements) > 1:
                criteria_string = "-".join(sorted(list(set(extracted_elements))))
            elif len(extracted_elements) == 1:
                criteria_string = extracted_elements[0]
            else: # Should be caught by "if not extracted_elements"
                result_template["status"] = "error"
                result_template["message"] = "Element extraction resulted in an empty list unexpectedly."
                return result_template

            result_template["message"] = f"Querying Materials Project for criteria: '{criteria_string}' with properties: {properties_to_fetch}"
            print(f"Constructed criteria for MCPClient: {criteria_string}")

            materials_data = self.mcp_client.get_materials_data(criteria=criteria_string, properties=properties_to_fetch)

            if materials_data is None:
                result_template["status"] = "error"
                result_template["message"] = "Error occurred while fetching data from Materials Project."
                return result_template

            if not materials_data:
                result_template["status"] = "no_results"
                result_template["message"] = f"No materials found for criteria '{criteria_string}' with the specified properties."
                return result_template

            result_template["status"] = "success"
            result_template["data"] = materials_data
            result_template["message"] = f"Successfully retrieved {len(materials_data)} material(s)."
            return result_template

        except Exception as e:
            result_template["status"] = "error"
            result_template["message"] = f"An unexpected error occurred in MaterialsAgent (live mode): {e}"
            return result_template


if __name__ == '__main__':
    print("--- MaterialsAgent Example Usage ---")

    # 1. Initialize components
    print("\nInitializing components...")
    element_extractor = ElementExtractor()

    # For the __main__ example, we'll primarily test demo mode.
    # So, we can pass a None or a dummy mcp_client for demo mode.
    class DummyMCPClient:
        def get_materials_data(self, criteria, properties): return None # Not called in demo
        def check_api_key_status(self): return (True, "Dummy client")

    dummy_mcp_client = DummyMCPClient()

    print("\n--- Running Agent in DEMO mode (with data from demo_materials.json) ---")
    agent_demo = MaterialsAgent(mcp_client=dummy_mcp_client, element_extractor=element_extractor, demo_mode=True)

    # Test case 1: Query for elements present in demo_materials.json
    query_demo_1 = "Show me materials with iron and oxygen"
    properties_demo_1 = ["material_id", "formula_pretty", "band_gap", "crystal_system"]
    print(f"\nPerforming Demo Query 1: '{query_demo_1}' for props: {properties_demo_1}")
    results_demo_1 = agent_demo.perform_query(query_demo_1, properties_demo_1)
    print("Demo Results 1:")
    for key, value in results_demo_1.items():
        if key == "data" and isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    {item}")
        else:
            print(f"  {key}: {value}")

    # Test case 2: Query for a single element
    query_demo_2 = "Find data for Silicon" # ElementExtractor should find 'Si'
    properties_demo_2 = ["material_id", "formula_pretty", "density", "elements"]
    print(f"\nPerforming Demo Query 2: '{query_demo_2}' for props: {properties_demo_2}")
    results_demo_2 = agent_demo.perform_query(query_demo_2, properties_demo_2)
    print("Demo Results 2:")
    for key, value in results_demo_2.items():
        if key == "data" and isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    {item}")
        else:
            print(f"  {key}: {value}")

    # Test case 3: Query for a formula present in demo data
    query_demo_3 = "What about NaCl?"
    properties_demo_3 = ["material_id", "formula_pretty", "volume"]
    print(f"\nPerforming Demo Query 3: '{query_demo_3}' for props: {properties_demo_3}")
    results_demo_3 = agent_demo.perform_query(query_demo_3, properties_demo_3)
    print("Demo Results 3:")
    for key, value in results_demo_3.items():
        if key == "data" and isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    {item}")
        else:
            print(f"  {key}: {value}")

    # Test case 4: Query for elements NOT in any combination in demo data
    query_demo_4 = "Materials with Gallium, Arsenic and Titanium" # GaAs is present, TiO2 is present, but not Ga-As-Ti
    properties_demo_4 = ["material_id", "formula_pretty"]
    print(f"\nPerforming Demo Query 4: '{query_demo_4}' for props: {properties_demo_4}")
    results_demo_4 = agent_demo.perform_query(query_demo_4, properties_demo_4)
    print("Demo Results 4:")
    for key, value in results_demo_4.items():
        if key == "data" and isinstance(value, list) and value: # only print data if not empty
            print(f"  {key}:")
            for item in value:
                print(f"    {item}")
        else:
            print(f"  {key}: {value}")


    # Test case 5: Query with a property not available in all demo materials
    query_demo_5 = "Carbon materials"
    properties_demo_5 = ["material_id", "formula_pretty", "band_gap", "nelements", "non_existent_property"]
    print(f"\nPerforming Demo Query 5: '{query_demo_5}' for props: {properties_demo_5}")
    results_demo_5 = agent_demo.perform_query(query_demo_5, properties_demo_5)
    print("Demo Results 5:")
    for key, value in results_demo_5.items():
        if key == "data" and isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    {item}")
        else:
            print(f"  {key}: {value}")

    # Test case 6: No elements in query
    query_demo_6 = "Tell me a story"
    properties_demo_6 = ["material_id"]
    print(f"\nPerforming Demo Query 6: '{query_demo_6}' for props: {properties_demo_6}")
    results_demo_6 = agent_demo.perform_query(query_demo_6, properties_demo_6)
    print("Demo Results 6:")
    print(f"  Status: {results_demo_6['status']}")
    print(f"  Message: {results_demo_6['message']}")
    print(f"  Extracted Elements: {results_demo_6['extracted_elements']}")


    # --- Live Mode example (requires MP_API_KEY to be set) ---
    api_key = os.environ.get("MP_API_KEY")
    if api_key:
        print("\n--- Attempting LIVE mode query (if MP_API_KEY is set) ---")
        try:
            live_mcp_client = MaterialsProjectMCPClient(api_key=api_key)
            if live_mcp_client.check_api_key_status()[0]: # Check if API key is valid
                agent_live = MaterialsAgent(mcp_client=live_mcp_client, element_extractor=element_extractor, demo_mode=False)
                query_live = "Iron oxide"
                properties_live = ["material_id", "formula_pretty", "band_gap"]
                print(f"\nPerforming Live Query: '{query_live}' for props: {properties_live}")
                results_live = agent_live.perform_query(query_live, properties_live)
                print("Live Results:")
                for key, value in results_live.items():
                    if key == "data" and isinstance(value, list):
                        print(f"  {key}: (showing up to 2 entries)")
                        for item in value[:2]:
                            print(f"    {item}")
                        if len(value) > 2: print(f"    ... and {len(value)-2} more.")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("Live mode skipped: API key status check failed.")
        except Exception as e:
            print(f"Live mode skipped due to error: {e}")
    else:
        print("\n--- Live mode skipped: MP_API_KEY not set. ---")

    print("\n--- MaterialsAgent Example Usage Finished ---")
