import streamlit as st
import asyncio
import json
from pathlib import Path
import sys
import pandas as pd

# Add project root to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from valiant.framework.api import ValiantAPI


def main():
    st.set_page_config(page_title="Valiant Workflow Runner", layout="wide")
    st.title("🚀 Valiant Workflow Runner")

    try:
        # Get available workflows
        workflows = ValiantAPI.list_workflows()

        if not workflows:
            st.error("No workflows found.")
            return

        # Workflow selection
        #selected_workflow = st.sidebar.selectbox("Choose Workflow", list(workflows.keys()))
        selected_workflow = st.selectbox("Choose Workflow", list(workflows.keys()))
        # Get input schema
        input_schema = ValiantAPI.get_workflow_input_schema(selected_workflow)

        # Render dynamic form
        user_inputs = {}
        if input_schema:
            st.header("🔧 Configuration")
            cols = st.columns(3)  # 3 columns per row
            for idx, field in enumerate(input_schema):
                col = cols[idx % 3]
                with col:
                    if field['type'] == 'text':
                        user_inputs[field['name']] = st.text_input(
                            field['label'], value=field.get('default', '')
                        )
                    elif field['type'] == 'password':
                        user_inputs[field['name']] = st.text_input(
                            field['label'], type="password", value=field.get('default', '')
                        )
                    elif field['type'] == 'number':
                        user_inputs[field['name']] = st.number_input(
                            field['label'],
                            min_value=field.get('min_value', 0),
                            max_value=field.get('max_value', 1000),
                            value=field.get('default', 0)
                        )
                    elif field['type'] == 'select':
                        user_inputs[field['name']] = st.selectbox(
                            field['label'],
                            field.get('options', []),
                            index=field.get('options', []).index(field.get('default', '')) if field.get('default', '') in field.get('options', []) else 0
                        )
                    elif field['type'] == 'date':
                        date_value = st.date_input(field['label'])
                        if date_value:
                            if isinstance(date_value, tuple):
                                user_inputs[field['name']] = date_value[0].isoformat() if date_value[0] else None
                            else:
                                user_inputs[field['name']] = date_value.isoformat()
                        else:
                            user_inputs[field['name']] = None
                    elif field['type'] == 'checkbox' or field['type'] == 'boolean':
                        user_inputs[field['name']] = st.checkbox(field['label'], value=field.get('default', False))

        # Run workflow
        if st.button("▶️ Run Workflow", type="primary"):
            with st.spinner("Running workflow..."):
                result = asyncio.run(ValiantAPI.run_workflow(
                    selected_workflow,
                    context_overrides=user_inputs
                ))

            st.header("📊 Results")
            table_rows = []
            view_buttons = []
            for idx, step in enumerate(result['results']):
                data_preview = ""
                if step.get('data') not in (None, '', [], {}):
                    data_str = json.dumps(step['data'])
                    data_preview = data_str if len(data_str) < 60 else data_str[:57] + "..."
                if step['success']:
                    status_symbol = "✅"
                elif step.get('skipped', False):
                    status_symbol = "⏭️"
                else:
                    status_symbol = "❌"

                table_rows.append({
                    "Step": step['name'],
                    "Status": status_symbol,
                    "Message": step['message'],
                    "Time (s)": step.get('time_taken', 0),
                    "Attempts": step.get('attempts', 1),
                    "Data": data_preview if data_preview else "",
                })
                # Add a button for viewing full data if present
                if step.get('data') not in (None, '', [], {}):
                    view_buttons.append((idx, step['name']))

            df = pd.DataFrame(table_rows)
            st.table(df)


    except Exception as e:
        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
