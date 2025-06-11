import gradio as gr
import pymatgen.core as mg
import requests
import json
import pandas as pd
import tempfile
import os
import subprocess
import sys
import time

# --- Mappings for user-friendly property names ---
API_TO_FRIENDLY_NAME = {
    "is_stable": "Stable?",
    "symmetry": "Space Group",
}
FRIENDLY_NAME_TO_API = {v: k for k, v in API_TO_FRIENDLY_NAME.items()}

DEFAULT_PROPERTIES_API = [
    "builder_meta", "nsites", "elements", "nelements", "composition", "composition_reduced",
    "formula_pretty", "formula_anonymous", "chemsys", "volume", "density", "density_atomic",
    "symmetry", "property_name", "material_id", "deprecated", "deprecation_reasons",
    "last_updated", "origins", "warnings", "structure", "task_ids", "uncorrected_energy_per_atom",
    "energy_per_atom", "formation_energy_per_atom", "energy_above_hull", "is_stable",
    "equilibrium_reaction_energy_per_atom", "decomposes_to", "xas", "grain_boundaries",
    "band_gap", "cbm", "vbm", "efermi", "is_gap_direct", "is_metal", "es_source_calc_id",
    "bandstructure", "dos", "orbital", "magnetic_ordering", "dos_energy_up", "dos_energy_down",
    "is_magnetic", "ordering", "total_magnetization", "total_magnetization_normalized_vol",
    "total_magnetization_normalized_formula_units", "num_magnetic_sites", "num_unique_magnetic_sites",
    "types_of_magnetic_species", "bulk_modulus", "shear_modulus", "universal_anisotropy",
    "homogeneous_poisson", "e_total", "e_ionic", "e_electronic", "n", "e_ij_max",
    "weighted_surface_energy_EV_PER_ANG2", "weighted_surface_energy", "weighted_work_function",
    "surface_anisotropy", "shape_factor", "has_reconstructed", "possible_species",
    "has_props", "theoretical", "database_IDs"
]

# --- 1. Core Components: Agent & MCP Client ---

class MaterialsProjectMCPClient:
    """
    MCP Client that connects to our local MCP Server.
    """
    def __init__(self, mcp_server_url="http://127.0.0.1:8001"):
        self.mcp_server_url = mcp_server_url
        self.api_key = None

    def from_api_key(self, api_key: str):
        """Stores the API key for future requests."""
        if not api_key:
            self.api_key = None
            return "API Key cleared."
        self.api_key = api_key
        return f"API Key set successfully: {'*' * 8}{api_key[-4:]}" if api_key else "API Key cleared."

    def get_available_properties(self):
        """Fetches the available properties from the MCP server."""
        if not self.api_key:
            raise gr.Error("Materials Project API Key is not set.")
        
        properties_url = f"{self.mcp_server_url}/properties"
        payload = {"api_key": self.api_key}
        
        try:
            response = requests.post(properties_url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("properties", [])
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except json.JSONDecodeError:
                detail = e.response.text
            raise gr.Error(f"Failed to fetch properties: {detail}")
        except requests.exceptions.RequestException:
            raise gr.Error(f"Could not connect to the MCP server at {self.mcp_server_url}. Is it running?")

    def search(self, criteria, properties, max_results):
        """Performs a search by calling the local MCP server."""
        if not self.api_key:
            raise gr.Error("Materials Project API Key is not set. Please provide a valid API key.")
        
        search_url = f"{self.mcp_server_url}/search"
        payload = {
            "elements": criteria.get("elements", []),
            "properties": properties,
            "api_key": self.api_key,
            "max_results": max_results
        }
        
        try:
            response = requests.post(search_url, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            return response_data.get("data", [])
            
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except json.JSONDecodeError:
                detail = e.response.text
            raise gr.Error(f"Failed to query MCP server: {detail}")
        except requests.exceptions.RequestException as e:
            raise gr.Error(f"Could not connect to the MCP server at {self.mcp_server_url}. Is it running?")

class MaterialsAgent:
    """
    The main AI agent that processes user queries and interacts with the
    Materials Project database via the MCP client.
    """
    def __init__(self, mcp_client: MaterialsProjectMCPClient):
        self.mcp_client = mcp_client
        self.element_map = {
            "iron": "Fe", "carbon": "C", "oxygen": "O", "silicon": "Si",
            "aluminum": "Al", "titanium": "Ti", "copper": "Cu", "zinc": "Zn",
            "gold": "Au", "silver": "Ag", "nickel": "Ni", "cobalt": "Co",
            "manganese": "Mn", "chromium": "Cr", "vanadium": "V",
        }

    def parse_query(self, query: str):
        words = query.lower().replace(",", "").split()
        elements = []
        for word in words:
            if word in self.element_map:
                elements.append(self.element_map[word])
            elif mg.Element.is_valid_symbol(word.capitalize()):
                elements.append(word.capitalize())
        
        if not elements:
            raise gr.Error("Could not identify any chemical elements in the query. Please state the full element name (e.g., 'iron') or its symbol (e.g., 'Fe').")
            
        return {"elements": elements}

# --- 2. Gradio Interface Creation ---

def create_gradio_interface(agent: MaterialsAgent):
    """Creates and returns the Gradio web interface."""

    # Fetch properties on startup
    try:
        if not agent.mcp_client.api_key:
            raise gr.Error("MP_API_KEY secret is not set in your Hugging Face Space.")
        properties = agent.mcp_client.get_available_properties()
        display_choices = sorted([API_TO_FRIENDLY_NAME.get(p, p) for p in properties])
        is_interactive = True
        startup_error = None
    except Exception as e:
        display_choices = []
        is_interactive = False
        startup_error = str(e)

    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔬 MateriaScout: AI-Powered Materials Science Agent")
        gr.Markdown("Query the [Materials Project](https://materialsproject.org/) database using natural language.")

        if startup_error:
            gr.Markdown(f"<h3 style='color:red;'>Initialization Error: {startup_error}</h3>")
            gr.Markdown("Please ensure you have set the `MP_API_KEY` in your Space's secrets and that the key is valid. You may need to restart the Space after setting the secret.")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Search Configuration")
                properties_checkboxes = gr.CheckboxGroup(
                    label="Properties to Display",
                    choices=display_choices,
                    value=[],
                    interactive=is_interactive
                )
                max_results_slider = gr.Slider(
                    minimum=1, 
                    maximum=200, 
                    value=10, 
                    step=1, 
                    label="Max Results"
                )

            with gr.Column(scale=2):
                query_input = gr.Textbox(label="Your Query", placeholder="e.g., 'Find me materials made of Iron and Oxygen with a high band gap'")
                with gr.Row():
                    search_button = gr.Button("🚀 Search", variant="primary")
                    export_button = gr.Button("📄 Export to CSV")
                results_output = gr.DataFrame(label="📊 Results", interactive=False)
                csv_download_file = gr.File(label="Download CSV", visible=False)

        def handle_search(query, properties, max_results):
            """Handles the search button click event."""
            if not query:
                raise gr.Error("Please enter a query.")
            
            if not properties:
                raise gr.Error("Please select at least one property to display.")

            try:
                criteria = agent.parse_query(query)
                
                api_properties = [FRIENDLY_NAME_TO_API.get(p, p) for p in properties]

                if "material_id" not in api_properties:
                    api_properties.append("material_id")
                if "formula_pretty" not in api_properties:
                    api_properties.append("formula_pretty")

                data = agent.mcp_client.search(criteria, list(set(api_properties)), max_results)
                
                if not data:
                    return pd.DataFrame(), gr.update(visible=False)
                
                df = pd.DataFrame(data)

                if 'symmetry' in df.columns:
                    df['Space Group'] = df['symmetry'].apply(lambda x: x.get('symbol') if isinstance(x, dict) else None)
                if 'is_stable' in df.columns:
                    df['Stable?'] = df['is_stable']
                
                display_columns = ['material_id', 'formula_pretty'] + properties
                
                final_columns = [p for p in display_columns if p in df.columns]
                
                return df[final_columns], gr.update(visible=False)
            except gr.Error as e:
                raise e

        def handle_export(df):
            if df is None or len(df) == 0:
                return gr.update(visible=False)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', encoding='utf-8') as f:
                df.to_csv(f, name)
                filepath = f.name
            
            return gr.update(value=filepath, visible=True)

        search_button.click(
            fn=handle_search, 
            inputs=[query_input, properties_checkboxes, max_results_slider], 
            outputs=[results_output, csv_download_file]
        )
        
        export_button.click(
            fn=handle_export,
            inputs=[results_output],
            outputs=[csv_download_file]
        )

    return demo

# --- 3. Main Execution ---

if __name__ == "__main__":
    print("Starting MCP backend server...")
    server_command = [
        sys.executable, "-m", "uvicorn", "mcp_server:app",
        "--host", "0.0.0.0", "--port", "8001"
    ]
    # Use stdout=subprocess.PIPE and stderr=subprocess.PIPE to capture logs if needed for debugging
    server_process = subprocess.Popen(server_command)
    print("MCP backend server started. Waiting for it to be ready...")

    # Wait for the server to become available
    health_check_url = "http://127.0.0.1:8001/health"
    max_retries = 15
    retry_delay_seconds = 2

    for i in range(max_retries):
        try:
            response = requests.get(health_check_url)
            if response.status_code == 200:
                print("MCP backend server is ready.")
                break
        except requests.exceptions.ConnectionError:
            print(f"Waiting for server... Attempt {i + 1}/{max_retries}")
            time.sleep(retry_delay_seconds)
    else:
        print("Error: MCP backend server did not become ready in time.")
        server_process.terminate() # Stop the server process
        sys.exit("Could not connect to backend server. Exiting.")

    # Initialize client and agent
    api_key = os.environ.get("MP_API_KEY")
    
    mcp_client = MaterialsProjectMCPClient()
    mcp_client.from_api_key(api_key) 
    
    agent = MaterialsAgent(mcp_client)

    demo = create_gradio_interface(agent)
    demo.launch(show_error=True) 