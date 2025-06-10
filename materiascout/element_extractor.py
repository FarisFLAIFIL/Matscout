# This file will contain the logic for extracting elements from materials data.

import re

class ElementExtractor:
    def __init__(self):
        """
        Initializes the ElementExtractor with a predefined dictionary of element names to symbols.
        """
        self.element_dict = {
            "iron": "Fe",
            "silicon": "Si",
            "oxygen": "O",
            "carbon": "C",
            "sodium": "Na",
            "chlorine": "Cl",
            # TODO: Expand this dictionary with more elements
        }
        # TODO: Consider loading this dictionary from an external file (e.g., CSV, JSON)

    def extract_elements(self, text: str) -> list[str]:
        """
        Extracts chemical symbols/formulas from a natural language string.

        Args:
            text: The input natural language string.

        Returns:
            A list of extracted chemical symbols/formulas.
        """
        if not isinstance(text, str):
            # TODO: Add more robust error handling or logging
            return []

        extracted_symbols = []
        # Simple tokenization by splitting the text by spaces, commas, and periods.
        # TODO: Implement more sophisticated NLP techniques for tokenization.
        # TODO: Handle multi-word element names (e.g., "sodium chloride").
        # TODO: Handle more complex queries (e.g., "materials containing iron and oxygen").
        tokens = re.split(r'[ ,\.]+', text.lower())

        for token in tokens:
            if token in self.element_dict:
                extracted_symbols.append(self.element_dict[token])
            elif token.capitalize() in self.element_dict.values(): # Check if token is already a symbol
                extracted_symbols.append(token.capitalize())
            elif token.isalnum() and token[0].isupper() and all(c.islower() or c.isdigit() for c in token[1:]):
                # Basic check for chemical formulas like Fe2O3 or NaCl
                # This is a simplistic check and might need refinement
                extracted_symbols.append(token)


        # Remove duplicates while preserving order
        seen = set()
        unique_extracted_symbols = []
        for symbol in extracted_symbols:
            if symbol not in seen:
                seen.add(symbol)
                unique_extracted_symbols.append(symbol)

        return unique_extracted_symbols

if __name__ == '__main__':
    # Example Usage
    extractor = ElementExtractor()
    test_string_1 = "I am looking for materials with iron and silicon."
    print(f"'{test_string_1}' -> {extractor.extract_elements(test_string_1)}")

    test_string_2 = "Show me compounds of oxygen, carbon, and Fe"
    print(f"'{test_string_2}' -> {extractor.extract_elements(test_string_2)}")

    test_string_3 = "Find data on NaCl and H2O."
    print(f"'{test_string_3}' -> {extractor.extract_elements(test_string_3)}")

    test_string_4 = "Material with sodium chloride" # Not handled by current simple logic
    print(f"'{test_string_4}' -> {extractor.extract_elements(test_string_4)}")

    test_string_5 = "iron oxide" # Not handled by current simple logic
    print(f"'{test_string_5}' -> {extractor.extract_elements(test_string_5)}")

    test_string_6 = "Fe2O3"
    print(f"'{test_string_6}' -> {extractor.extract_elements(test_string_6)}")
