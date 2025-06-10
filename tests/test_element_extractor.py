# This file will contain tests for the ElementExtractor class.

import unittest
from materiascout.element_extractor import ElementExtractor

class TestElementExtractor(unittest.TestCase):
    def setUp(self):
        """Instantiate ElementExtractor for use in test methods."""
        self.extractor = ElementExtractor()
        # Expected element dictionary from ElementExtractor
        # self.element_dict = {
        #     "iron": "Fe", "silicon": "Si", "oxygen": "O", "carbon": "C",
        #     "sodium": "Na", "chlorine": "Cl"
        # }
        # The tests will rely on this dictionary being present in ElementExtractor

    def test_empty_input(self):
        """Test with an empty string input."""
        self.assertEqual(self.extractor.extract_elements(""), [])

    def test_none_input(self):
        """Test with None as input."""
        self.assertEqual(self.extractor.extract_elements(None), []) # type: ignore

    def test_basic_element_names_lowercase(self):
        """Test extraction of single, common element names in lowercase."""
        self.assertListEqual(self.extractor.extract_elements("iron"), ["Fe"])
        self.assertListEqual(self.extractor.extract_elements("silicon"), ["Si"])
        self.assertListEqual(self.extractor.extract_elements("oxygen"), ["O"])

    def test_basic_element_names_mixed_case(self):
        """Test extraction of single, common element names in mixed case (should be case-insensitive)."""
        self.assertListEqual(self.extractor.extract_elements("Iron"), ["Fe"])
        self.assertListEqual(self.extractor.extract_elements("Silicon"), ["Si"])
        self.assertListEqual(self.extractor.extract_elements("Oxygen"), ["O"])
        self.assertListEqual(self.extractor.extract_elements("CARBON"), ["C"])


    def test_chemical_symbols_direct(self):
        """Test direct usage of chemical symbols."""
        self.assertListEqual(self.extractor.extract_elements("Fe"), ["Fe"])
        self.assertListEqual(self.extractor.extract_elements("Si"), ["Si"])
        # Test for a symbol not in the name dict but valid symbol format
        self.assertListEqual(self.extractor.extract_elements("Au"), ["Au"])
        self.assertListEqual(self.extractor.extract_elements("H"), ["H"])


    def test_multiple_elements_names_and_symbols(self):
        """Test queries with multiple element names or symbols."""
        self.assertListEqual(self.extractor.extract_elements("iron and oxygen"), ["Fe", "O"])
        self.assertListEqual(self.extractor.extract_elements("Si, C"), ["Si", "C"])
        self.assertListEqual(self.extractor.extract_elements("sodium, chlorine"), ["Na", "Cl"])
        self.assertListEqual(self.extractor.extract_elements("Fe, Si, O"), ["Fe", "Si", "O"])

    def test_formulas_simple(self):
        """Test extraction of simple chemical formulas."""
        self.assertListEqual(self.extractor.extract_elements("H2O"), ["H2O"])
        self.assertListEqual(self.extractor.extract_elements("NaCl"), ["NaCl"])
        self.assertListEqual(self.extractor.extract_elements("Fe2O3"), ["Fe2O3"])

    def test_mixed_content_names_symbols_formulas(self):
        """Test queries containing mixed element names, symbols, and formulas."""
        self.assertListEqual(self.extractor.extract_elements("iron, NaCl and O"), ["Fe", "NaCl", "O"])
        self.assertListEqual(self.extractor.extract_elements("Data for Si, carbon, and Fe2O3"), ["Si", "C", "Fe2O3"])

    def test_no_elements_in_query(self):
        """Test queries that do not contain any recognizable element names or formulas."""
        self.assertListEqual(self.extractor.extract_elements("A string with no known elements."), [])
        self.assertListEqual(self.extractor.extract_elements("12345 numbers only"), [])
        self.assertListEqual(self.extractor.extract_elements("just some words"), [])

    def test_duplicates_handling(self):
        """Test that duplicates are handled (unique, ordered list)."""
        self.assertListEqual(self.extractor.extract_elements("iron and Fe"), ["Fe"])
        self.assertListEqual(self.extractor.extract_elements("silicon, Si, silicon"), ["Si"])
        self.assertListEqual(self.extractor.extract_elements("H2O, water, H2O"), ["H2O"]) # Assuming 'water' is not in dict
        self.assertListEqual(self.extractor.extract_elements("oxygen oxygen O O"), ["O"])


    def test_specific_iron_fe_mapping(self):
        """Explicitly test the 'iron' to 'Fe' mapping."""
        self.assertListEqual(self.extractor.extract_elements("Contains iron."), ["Fe"])

    def test_complex_sentences_and_extraneous_words(self):
        """Test with more complex sentence structures or extraneous words."""
        self.assertListEqual(self.extractor.extract_elements("Show me data for carbon and silicon elements."), ["C", "Si"])
        self.assertListEqual(self.extractor.extract_elements("What about Au? Is it present?"), ["Au"])
        self.assertListEqual(self.extractor.extract_elements("I need Fe2O3, please."), ["Fe2O3"])
        self.assertListEqual(self.extractor.extract_elements("Looking for (oxygen) or [chlorine]!"), ["O", "Cl"])

    def test_punctuation_handling(self):
        """Test handling of various punctuation marks."""
        self.assertListEqual(self.extractor.extract_elements("Fe.Si,O"), ["Fe", "Si", "O"])
        self.assertListEqual(self.extractor.extract_elements("carbon-oxygen compounds"), ["C", "O"]) # hyphenated
        self.assertListEqual(self.extractor.extract_elements("NaCl; Fe2O3"), ["NaCl", "Fe2O3"]) # Semicolon, current regex splits on it

    def test_order_of_extraction(self):
        """Test that the order of first appearance is preserved."""
        self.assertListEqual(self.extractor.extract_elements("oxygen and iron"), ["O", "Fe"])
        self.assertListEqual(self.extractor.extract_elements("Si, Fe, O, C"), ["Si", "Fe", "O", "C"])
        self.assertListEqual(self.extractor.extract_elements("NaCl, Fe, carbon, H2O, Si"), ["NaCl", "Fe", "C", "H2O", "Si"])

    def test_elements_not_in_dict_but_valid_symbol_format(self):
        """Test elements not in the predefined name-to-symbol dictionary but are valid symbols."""
        self.assertListEqual(self.extractor.extract_elements("Au and Pt"), ["Au", "Pt"])
        self.assertListEqual(self.extractor.extract_elements("Lithium (Li) and Helium (He)"), ["Li", "He"]) # Assuming Lithium, Helium not in dict

    def test_multi_letter_symbols(self):
        """Test multi-letter symbols like Cl, Na are handled correctly (both name and symbol)."""
        self.assertListEqual(self.extractor.extract_elements("chlorine"), ["Cl"])
        self.assertListEqual(self.extractor.extract_elements("Cl"), ["Cl"])
        self.assertListEqual(self.extractor.extract_elements("sodium and Cl"), ["Na", "Cl"])

    def test_numbers_attached_to_names_or_symbols(self):
        """Test if numbers attached to names or symbols are handled (they generally shouldn't match names)."""
        self.assertListEqual(self.extractor.extract_elements("iron2"), []) # "iron2" is not "iron"
        self.assertListEqual(self.extractor.extract_elements("Fe2"), ["Fe2"]) # "Fe2" is a valid formula-like token
        self.assertListEqual(self.extractor.extract_elements("Oxygen3"), []) # "Oxygen3" is not "Oxygen"

    def test_substrings(self):
        """Test that element names are matched as whole words (substrings should not match)."""
        # E.g., 'done' should not match 'O' if 'O' is oxygen.
        # Current regex `re.split(r'[ ,\.]+', text.lower())` tokenizes by spaces/commas/periods.
        # So, "done" would be a token. If "done" is not in element_dict, it won't match.
        # If an element like "on" was in the dict, "done" would not match "on".
        self.assertListEqual(self.extractor.extract_elements("done"), [])
        self.assertListEqual(self.extractor.extract_elements("sirius"), []) # Should not match "Si" from "silicon"
        self.assertListEqual(self.extractor.extract_elements("Feat"), []) # Should not match "Fe"
        # Test with a hypothetical short element name
        # self.extractor.element_dict["on"] = "On" # Temporarily add for test
        # self.assertListEqual(self.extractor.extract_elements("done contains on"), ["On"])
        # del self.extractor.element_dict["on"] # Clean up


if __name__ == "__main__":
    unittest.main()
