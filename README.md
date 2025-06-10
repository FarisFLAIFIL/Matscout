# MateriaScout: AI-Powered Materials Science Agent

MateriaScout is an AI-powered assistant designed for materials science research. It leverages the Materials Project API to fetch data and uses a Gradio-based web interface for user interaction. This project was developed for the "Agents-MCP-Hackathon 2025, Track 3: Agentic Demo Showcase".

## Features

*   **Natural Language Queries:** Ask for materials using everyday language (e.g., "Find materials with iron and oxygen").
*   **Materials Project API Integration:** Fetches comprehensive materials data directly from the Materials Project database.
*   **Gradio Web Interface:** User-friendly interface for querying and viewing results.
*   **API Key Management:** Securely input and use your Materials Project API key via the UI.
*   **Selectable Material Properties:** Choose which material properties you want to see in the results.
*   **Demo Mode:** Explore the application's functionality using built-in sample data, no API key required.
*   **Unit-Tested Core Components:** Key modules like `ElementExtractor`, `MaterialsProjectMCPClient`, and `MaterialsAgent` have associated unit tests.

## Technical Overview

MateriaScout consists of several core Python components:

*   `materiascout/app.py`: Implements the Gradio web interface and handles user interaction logic.
*   `materiascout/materials_agent.py`: The main agent that orchestrates the query process. It uses the `ElementExtractor` to understand the query and the `MaterialsProjectMCPClient` to fetch data.
*   `materiascout/mcp_client.py`: A client specifically for interacting with the new Materials Project API (using `mp_api.client.MPRester`).
*   `materiascout/element_extractor.py`: A utility to parse natural language queries and extract chemical element names, symbols, or formulas.
*   `materiascout/data/demo_materials.json`: Sample data used when the application is running in Demo Mode.

## Project Structure

```
materiascout/
├── __init__.py
├── app.py                # Gradio UI and application logic
├── materials_agent.py    # Core agent orchestrating queries
├── mcp_client.py         # Client for Materials Project API
├── element_extractor.py  # For NLP query processing
└── data/
    ├── __init__.py (optional)
    ├── .gitkeep (if directory is empty otherwise)
    └── demo_materials.json # Sample data for demo mode
tests/
├── __init__.py
├── test_materials_agent.py
├── test_mcp_client.py
└── test_element_extractor.py
README.md
requirements.txt
LICENSE
```

## Setup Instructions

### Prerequisites

*   Python 3.8 or newer.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/materiascout.git # Replace with actual URL
    cd materiascout
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Ensure your terminal is in the project's root directory where `materiascout/` is visible.**
2.  **Run the Gradio application:**
    ```bash
    python materiascout/app.py
    ```
3.  Open your web browser and go to the URL provided by Gradio (usually `http://127.0.0.1:7860` or `http://localhost:7860`).

## Configuration

### Materials Project API Key

For live data queries, MateriaScout requires an API key from the Materials Project.

1.  **Obtain an API Key:** If you don't have one, visit the [Materials Project Dashboard](https://materialsproject.org/dashboard) and generate an API key.
2.  **Using the API Key in MateriaScout:**
    *   Launch the MateriaScout application.
    *   In the "Configuration" section of the UI, paste your API key into the "Materials Project API Key" textbox.
    *   Click "Apply Configuration". The application will validate the key and display its status.

Alternatively, the underlying `mp-api` library (and `pymatgen`) can automatically detect an API key if it's set as the `MP_API_KEY` environment variable. However, using the UI input is recommended for this application.

### Demo Mode

If you don't have an API key or wish to explore the application with sample data:

*   Check the "Enable Demo Mode" checkbox in the "Configuration" section of the UI.
*   Click "Apply Configuration".
*   The application will then use a predefined set of materials from `materiascout/data/demo_materials.json` for all queries.

## Running Tests

To run the unit tests for the core components:

1.  **Ensure your terminal is in the project's root directory.**
2.  **Run all tests using unittest discovery:**
    ```bash
    python -m unittest discover tests
    ```
3.  **To run tests for a specific file:**
    ```bash
    python -m unittest tests.test_element_extractor
    python -m unittest tests.test_mcp_client
    python -m unittest tests.test_materials_agent
    ```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.