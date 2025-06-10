# This file will contain the client for interacting with the Materials Project API.

import os
# The new MPRester is part of mp_api.client
# pymatgen.ext.matproj is for the legacy API.
# For this implementation, we will use the new API via mp_api.client.MPRester
from mp_api.client import MPRester
from pymatgen.core import Composition # For type hinting if needed

# Comment regarding API versioning:
# The Materials Project has a legacy API and a new API.
# The `mp_api.client.MPRester` is designed to work with the new API.
# `pymatgen.ext.matproj.MPRester` is for the legacy API.
# This implementation uses the new API. Pymatgen handles much of the abstraction.

class MaterialsProjectMCPClient:
    def __init__(self, api_key: str = None):
        """
        Initializes the MaterialsProjectMCPClient.

        Args:
            api_key: The Materials Project API key. If None, it will try to
                     load from the MP_API_KEY environment variable.

        Raises:
            ValueError: If the API key is not provided and not found in environment variables.
            Exception: For errors during MPRester initialization.
        """
        if api_key is None:
            api_key = os.environ.get("MP_API_KEY")

        if not api_key:
            raise ValueError("API key must be provided or set as MP_API_KEY environment variable.")

        self.api_key = api_key
        try:
            # Initialize the MPRester with the API key.
            # The MPRester itself might not validate the key on init,
            # but errors can occur if the key format is severely malformed
            # or if there are connection issues.
            self.mpr = MPRester(self.api_key)
            # TODO: Add a method to check API key status/validity if MPRester provides one.
            # Currently, the best way to check is to make a simple, inexpensive query.
        except Exception as e:
            # Handle potential errors during MPRester initialization
            print(f"Error initializing MPRester: {e}")
            # Optionally, re-raise the exception or handle it as per application requirements
            raise

    def get_materials_data(self, criteria, properties: list[str]):
        """
        Fetches materials data from the Materials Project database.

        Args:
            criteria: Criteria for querying (e.g., chemical formula, material IDs, chemsys).
                      This can be a string (e.g., "Fe2O3"), a list of material IDs,
                      or a dictionary for more complex queries.
            properties: A list of properties to fetch for the materials.

        Returns:
            A list of dictionaries containing the fetched materials data,
            or None if an error occurs.

        Example criteria:
            - Formula: "Fe2O3"
            - Material ID: "mp-12345"
            - List of Material IDs: ["mp-12345", "mp-67890"]
            - Chemical system: "Fe-O" (elements in a material)
            - Using a dictionary for more complex queries:
              {"elements": ["Li", "Fe", "O"], "nelements": 3, "band_gap": (0.5, 2.0)}
        """
        if not self.mpr:
            print("MPRester not initialized. Cannot fetch data.")
            return None

        try:
            # Using MPRester.materials.search for flexibility with various criteria
            # For specific ID lookups: self.mpr.materials.get_data_by_id(material_id)
            # For formula lookups: self.mpr.materials.search(formula="Fe2O3", fields=properties)
            # For general search:
            if isinstance(criteria, str):
                # Could be a formula, material_id, or chemsys.
                # MPRester search can often infer this.
                # For more precise control, one might need separate methods or more complex criteria dict.
                data = self.mpr.materials.search(
                    formula=criteria if not criteria.startswith("mp-") and not "-" in criteria and not criteria.isdigit() else None,
                    material_ids=criteria if criteria.startswith("mp-") or criteria.isdigit() else None,
                    chemsys=criteria if "-" in criteria and not criteria.startswith("mp-") else None,
                    fields=properties
                )
            elif isinstance(criteria, list): # Assuming list of material_ids
                 data = self.mpr.materials.search(material_ids=criteria, fields=properties)
            elif isinstance(criteria, dict):
                data = self.mpr.materials.search(**criteria, fields=properties)
            else:
                print(f"Unsupported criteria type: {type(criteria)}")
                return None

            return [d.model_dump() for d in data] # Convert Pydantic models to dicts

        except Exception as e:
            # Handle API request errors (network issues, invalid queries, API key errors, etc.)
            print(f"Error querying Materials Project API: {e}")
            # TODO: Implement more specific error handling based on common MP API errors
            return None

    def check_api_key_status(self):
        """
        Placeholder for a method to check the API key status.
        Currently, the best way is to make a simple query.
        For example, try to retrieve data for a common material like "mp-149" (Silicon).
        """
        print("Checking API key status (simulated by fetching data for Si - mp-149)...")
        try:
            # A lightweight query to test API key and connectivity
            si_data = self.mpr.materials.search(material_ids="mp-149", fields=["material_id", "formula_pretty"])
            if si_data:
                print(f"API key seems valid. Successfully fetched: {si_data[0].formula_pretty}")
                return True
            else:
                # This case might not be hit if an exception occurs first for invalid keys
                print("API key might be invalid or network issue, no data returned for Si.")
                return False
        except Exception as e:
            print(f"API key status check failed: {e}")
            return False

if __name__ == '__main__':
    print("Attempting to initialize MaterialsProjectMCPClient...")
    # This example requires the MP_API_KEY environment variable to be set.
    # If you don't have an API key, this will raise an error or fail.
    api_key_env = os.environ.get("MP_API_KEY")

    if not api_key_env:
        print("MP_API_KEY environment variable not set. Skipping live API tests.")
        print("To run live tests, please set your Materials Project API key as MP_API_KEY.")
    else:
        print(f"Using API key from MP_API_KEY environment variable: {api_key_env[:5]}...") # Print first 5 chars for confirmation
        try:
            client = MaterialsProjectMCPClient(api_key=api_key_env)
            print("MaterialsProjectMCPClient initialized successfully.")

            # 1. Check API key status
            print("\n--- Checking API Key Status ---")
            client.check_api_key_status()

            # 2. Example: Get data for a specific material ID
            print("\n--- Example 1: Get data for Fe2O3 (using formula) ---")
            fe2o3_props = ["material_id", "formula_pretty", "band_gap", "density"]
            # MPRester might return multiple entries for a formula, we'll take the first for simplicity
            fe2o3_data = client.get_materials_data(criteria="Fe2O3", properties=fe2o3_props)
            if fe2o3_data and len(fe2o3_data) > 0:
                print(f"Data for Fe2O3: {fe2o3_data[0]}")
            elif fe2o3_data is None:
                 print("Failed to retrieve data for Fe2O3 (API error or client issue).")
            else:
                print("No data found for Fe2O3 with the specified properties.")

            # 3. Example: Get data for a list of material IDs
            print("\n--- Example 2: Get data for Si (mp-149) and NaCl (mp-22862) by IDs ---")
            ids_props = ["material_id", "formula_pretty", "crystal_system", "volume"]
            material_ids = ["mp-149", "mp-22862"] # Silicon and Salt
            materials_by_ids = client.get_materials_data(criteria=material_ids, properties=ids_props)
            if materials_by_ids:
                for material in materials_by_ids:
                    print(f"Data: {material}")
            else:
                print(f"Failed to retrieve data for material IDs: {material_ids}")

            # 4. Example: Query using a dictionary (more complex query)
            print("\n--- Example 3: Complex query for materials containing Li, Mn, O with 3 elements ---")
            complex_criteria = {"elements": ["Li", "Mn", "O"], "nelements": 3, "band_gap": (0.1, 3.0)}
            complex_props = ["material_id", "formula_pretty", "band_gap", "formation_energy_per_atom"]
            complex_data = client.get_materials_data(criteria=complex_criteria, properties=complex_props)
            if complex_data:
                print(f"Found {len(complex_data)} materials matching complex criteria (showing up to 2):")
                for material in complex_data[:2]: # Print first 2 results
                    print(f"Data: {material}")
            else:
                print(f"Failed to retrieve data for complex criteria: {complex_criteria}")

            # 5. Example: Invalid query (e.g., non-existent property or malformed criteria)
            print("\n--- Example 4: Invalid property query ---")
            invalid_props = ["non_existent_property_abc123"]
            invalid_data = client.get_materials_data(criteria="mp-149", properties=invalid_props)
            if invalid_data: # API might return entry with the field as null or omit it
                print(f"Data with invalid property (might be empty or error message): {invalid_data}")
            else: # More likely an error logged by the client.get_materials_data method
                print("Query with invalid property likely resulted in an error (check console output).")

        except ValueError as ve:
            print(f"Initialization ValueError: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred during client usage: {e}")
            print("This could be due to an invalid API key, network issues, or changes in the MP API.")
            print("Ensure your MP_API_KEY is correct and you have internet access.")
