# This file will contain the main Gradio application logic for MateriaScout.

import os
import gradio as gr
from materiascout.element_extractor import ElementExtractor
from materiascout.mcp_client import MaterialsProjectMCPClient
from materiascout.materials_agent import MaterialsAgent
import pandas as pd

# --- Global Variables & Initializations ---
# Initialize components. API key will be set via UI.
element_extractor = ElementExtractor()
# These will be updated by API key input
mcp_client_instance = None
materials_agent_instance = None

# Available properties for the user to select
AVAILABLE_PROPERTIES = [
    "material_id",
    "formula_pretty", # Changed from pretty_formula to match MP new API
    "density",
    "band_gap",
    "formation_energy_per_atom",
    "volume",
    "crystal_system",
    "symmetry.number", # Example of nested property
    "nelements",
    "nsites"
]

DEFAULT_PROPERTIES = ["material_id", "formula_pretty", "band_gap", "density"]

# --- Helper Functions ---
def initialize_client_and_agent(api_key, demo_mode_active):
    """
    Initializes or updates the MCPClient and MaterialsAgent instances.
    """
    global mcp_client_instance, materials_agent_instance

    if demo_mode_active:
        # In demo mode, we might not need a real API key for the agent,
        # but MaterialsAgent expects an mcp_client. We can use a dummy or mock one.
        class DummyMCPClient:
            def get_materials_data(self, criteria, properties): return []
            def check_api_key_status(self): return True, "Demo mode: API key not used."

        mcp_client_instance = DummyMCPClient()
        materials_agent_instance = MaterialsAgent(
            mcp_client=mcp_client_instance,
            element_extractor=element_extractor,
            demo_mode=True
        )
        return "Demo mode active. Using mock data.", True

    if not api_key:
        mcp_client_instance = None
        materials_agent_instance = None
        return "API Key not configured. Please enter an API key or enable Demo Mode.", False

    try:
        mcp_client_instance = MaterialsProjectMCPClient(api_key=api_key)
        status_ok, message = mcp_client_instance.check_api_key_status() # Assuming this method returns (bool, str)
        if status_ok:
            materials_agent_instance = MaterialsAgent(
                mcp_client=mcp_client_instance,
                element_extractor=element_extractor,
                demo_mode=False # Explicitly false when API key is used
            )
            return f"API Key validated. Client and Agent are active. ({message})", True
        else:
            mcp_client_instance = None
            materials_agent_instance = None
            return f"API Key validation failed: {message}. Please check your key.", False
    except Exception as e:
        mcp_client_instance = None
        materials_agent_instance = None
        return f"Error initializing client/agent: {str(e)}", False

def format_results_to_markdown_table(data_list: list[dict], properties: list[str]) -> str:
    """
    Formats a list of material data dictionaries into a Markdown table.
    """
    if not data_list:
        return "No data to display."

    # Ensure all requested properties are columns, even if some materials don't have them
    df = pd.DataFrame(data_list, columns=properties)
    return df.to_markdown(index=False)

# --- Gradio Interface Functions ---
def update_api_key_status(api_key_input: str, demo_mode_active: bool):
    """
    Called when "Save API Key" is clicked or demo_mode is toggled.
    Initializes client/agent and updates the status message.
    """
    # Store the API key in an environment variable if it's valid and not in demo mode
    # This is just one way to persist it for the session; Gradio states or other methods could be used.
    if api_key_input and not demo_mode_active:
        os.environ["MP_API_KEY_GRADIOM"] = api_key_input # Use a custom env var name
    else:
        # Clear it if demo mode or no key
        os.environ.pop("MP_API_KEY_GRADIOM", None)

    message, _ = initialize_client_and_agent(api_key_input, demo_mode_active)
    return message

def search_materials_interface(natural_language_query: str, properties_to_fetch: list[str],
                               api_key_input: str, demo_mode_active: bool):
    """
    Main function for the "Search Materials" button.
    """
    global materials_agent_instance, mcp_client_instance

    # Ensure agent is initialized, possibly again if API key or demo mode changed without saving explicitly
    # This makes the search button self-contained to some extent.
    if materials_agent_instance is None or \
       (materials_agent_instance.demo_mode != demo_mode_active) or \
       (not demo_mode_active and (mcp_client_instance is None or mcp_client_instance.api_key != api_key_input)):

        status_message, success = initialize_client_and_agent(api_key_input, demo_mode_active)
        if not success and not demo_mode_active: # If not demo mode and init failed
             return "Agent not initialized. Please check API key or enable Demo Mode.", f"Status: {status_message}", "[]"


    if not natural_language_query:
        return "Please enter a query.", "Status: No query provided.", "[]"
    if not properties_to_fetch:
        return "Please select properties to fetch.", "Status: No properties selected.", "[]"

    if materials_agent_instance is None and not demo_mode_active: # Should be caught by above, but as a safeguard
        return "Error: Agent not available and not in demo mode. Check API Key.", "Status: Agent unavailable.", "[]"

    # If in demo mode, ensure agent is set to demo mode.
    if demo_mode_active and (materials_agent_instance is None or not materials_agent_instance.demo_mode):
        # This re-initializes in demo mode if it wasn't already.
        initialize_client_and_agent(None, True)


    agent_result = materials_agent_instance.perform_query(
        natural_language_query=natural_language_query,
        properties_to_fetch=properties_to_fetch
    )

    status_text = f"Status: {agent_result['status']}. Message: {agent_result.get('message', 'N/A')}"
    raw_output_json = agent_result # Display the whole dict for debugging/info

    if agent_result["status"] == "success":
        if agent_result["data"]:
            markdown_table = format_results_to_markdown_table(agent_result["data"], properties_to_fetch)
            return markdown_table, status_text, raw_output_json
        else:
            return "No materials found matching your criteria.", status_text, raw_output_json
    elif agent_result["status"] == "no_results":
        return agent_result.get('message', "No materials found."), status_text, raw_output_json
    else: # Error
        return "An error occurred.", status_text, raw_output_json


# --- Gradio UI Definition ---
def create_gradio_app():
    """
    Constructs and returns the Gradio interface.
    """
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# MateriaScout: Materials Discovery Engine")

        # State to store API key for the session (alternative to env var for some use cases)
        # api_key_state = gr.State(None)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Configuration")
                api_key_textbox = gr.Textbox(
                    label="Materials Project API Key",
                    type="password",
                    placeholder="Enter your MP API key here",
                    elem_id="api_key_input"
                )
                demo_mode_checkbox = gr.Checkbox(label="Enable Demo Mode", value=False)

                # Initialize API status based on demo mode by default
                initial_api_status_message, _ = initialize_client_and_agent(None, demo_mode_checkbox.value)
                api_status_label = gr.Markdown(initial_api_status_message)

                save_api_key_button = gr.Button("Apply Configuration")

                # Connect button and demo_mode_checkbox to update_api_key_status
                # Use .then() for sequencing after a change or click
                # The `inputs` to `update_api_key_status` will be taken from these components.
                # The `outputs` will update `api_status_label`.
                save_api_key_button.click(
                    fn=update_api_key_status,
                    inputs=[api_key_textbox, demo_mode_checkbox],
                    outputs=[api_status_label]
                )
                demo_mode_checkbox.change(
                    fn=update_api_key_status,
                    inputs=[api_key_textbox, demo_mode_checkbox],
                    outputs=[api_status_label]
                )

                gr.Markdown("---")
                gr.Markdown("## Query Materials")
                query_textbox = gr.Textbox(
                    label="Natural Language Query",
                    placeholder="e.g., 'Find materials with silicon and oxygen, high band gap'",
                    lines=3
                )
                properties_checkbox_group = gr.CheckboxGroup(
                    label="Select Properties to Display",
                    choices=AVAILABLE_PROPERTIES,
                    value=DEFAULT_PROPERTIES
                )
                search_button = gr.Button("Search Materials", variant="primary")

            with gr.Column(scale=2):
                gr.Markdown("## Results")
                results_markdown_table = gr.Markdown("Search results will appear here as a table.")
                gr.Markdown("---")
                gr.Markdown("### Status & Raw Output")
                status_display_textbox = gr.Textbox(label="Query Status", lines=2, interactive=False)
                raw_output_json_display = gr.JSON(label="Agent Raw Output")

        # Connect search button to the search_materials_interface function
        search_button.click(
            fn=search_materials_interface,
            inputs=[query_textbox, properties_checkbox_group, api_key_textbox, demo_mode_checkbox],
            outputs=[results_markdown_table, status_display_textbox, raw_output_json_display]
        )

        gr.Markdown(
            """
            **Note:**
            - An API key from [Materials Project](https://materialsproject.org/api) is required for live queries.
            - If Demo Mode is enabled, the application will use mock data and will not query the live API.
            - The `MaterialsProjectMCPClient` and `MaterialsAgent` are initialized/updated when 'Apply Configuration' is clicked or Demo Mode is toggled.
            - The search button also attempts to re-initialize if the configuration seems out of sync.
            """
        )
    return demo

if __name__ == "__main__":
    # Initialize based on current demo_mode_checkbox default (False)
    # This sets up the initial state of client/agent before UI interaction
    # The API key is None initially, so it will show "API Key not configured"
    # unless demo mode is True by default (which it is not here)
    initial_api_key = os.environ.get("MP_API_KEY_GRADIOM") # Check if persisted from a previous save for convenience
    initialize_client_and_agent(initial_api_key, False) # Assuming demo mode is initially False

    app = create_gradio_app()
    app.launch()
