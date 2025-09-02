from unittest import result
import streamlit as st
import asyncio
import json
from pathlib import Path
import sys
import pandas as pd

# Add project                 
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from valiant.framework.api import ValiantAPI
from valiant.ui.logger import streamlit_logger


def main():
    st.set_page_config(
        page_title="Workflow Execution Monitor",
        page_icon="🔄",
        layout="wide"
    )
    
    # Custom CSS for better metadata and tags display
    st.markdown("""
        <style>
        .stDataFrame td {
            white-space: pre-wrap !important;
            vertical-align: top !important;
            padding: 8px !important;
        }
        div[data-testid="stDataFrame"] table {
            table-layout: auto !important;
            width: 100% !important;
        }
        div[data-testid="stDataFrame"] th {
            background-color: #f0f2f6 !important;
            padding: 10px !important;
            font-weight: bold !important;
        }
        div[data-testid="stDataFrame"] td {
            max-width: 250px !important;
            font-family: monospace !important;
            background-color: #fafafa !important;
            border-radius: 4px !important;
            overflow-wrap: break-word !important;
        }
        /* Status column */
        div[data-testid="stDataFrame"] td:nth-child(2) {
            text-align: center !important;
            font-size: 1.2em !important;
            width: 80px !important;
        }
        /* Time and Attempts columns */
        div[data-testid="stDataFrame"] td:nth-child(4),
        div[data-testid="stDataFrame"] td:nth-child(5) {
            width: 100px !important;
            text-align: center !important;
        }
        /* Metrics column */
        div[data-testid="stDataFrame"] td:nth-child(6) {
            background-color: #f0f8ff !important;
            white-space: pre-wrap !important;
            font-family: monospace !important;
            font-size: 0.9em !important;
            line-height: 1.4 !important;
            padding: 12px !important;
        }
        /* Tags column */
        div[data-testid="stDataFrame"] td:nth-child(7) {
            background-color: #f0fff0 !important;
            font-family: monospace !important;
            font-size: 0.9em !important;
            line-height: 1.4 !important;
            padding: 12px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.title("🚀 Valiant Workflow Runner")

    streamlit_logger.info("Streamlit app started")

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
                streamlit_logger.info(f"Running workflow: {selected_workflow}")
                result = asyncio.run(ValiantAPI.run_workflow(
                    selected_workflow,
                    context_overrides=user_inputs
                ))
                streamlit_logger.info(f"Workflow completed: {selected_workflow}")

            st.header("📊 Results")
            # Controls for filtering and display
            colf1, colf2, colf3 = st.columns([1,1,2])
            with colf1:
                only_failed = st.checkbox("Show only failed", value=False)
            with colf2:
                only_with_metrics = st.checkbox("Only steps with metrics", value=False)
            with colf3:
                tag_filter = st.text_input("Filter by tag (comma-separated)", value="").strip()
            if result.get('execution_summary', {}).get('successful_steps', 0) > 0:
                st.success(f"Workflow completed successfully with {result['execution_summary']['successful_steps']} successful steps")
            else:
                st.warning("Workflow execution completed but no steps were executed successfully")
            
            # Apply filters to results
            filtered_results = result['results']
            if only_failed:
                filtered_results = [s for s in filtered_results if not s.get('success') and s.get('executed')]
            if only_with_metrics:
                filtered_results = [s for s in filtered_results if s.get('derived_metrics')]
            if tag_filter:
                required_tags = {t.strip().lower() for t in tag_filter.split(',') if t.strip()}
                if required_tags:
                    def has_tags(s):
                        tags = {t.lower() for t in s.get('tags', [])}
                        return required_tags.issubset(tags)
                    filtered_results = [s for s in filtered_results if has_tags(s)]

            table_rows = []
            for step in filtered_results:
                # Format metrics as a bulleted list with improved formatting
                metrics = step.get('derived_metrics', {})
                if metrics:
                    metrics_list = []
                    # Sort keys for stable display
                    for k in sorted(metrics.keys()):
                        v = metrics[k]
                        # Format numeric values to 2 decimal places if they're floats
                        if isinstance(v, float):
                            value_str = f"{v:.2f}"
                        else:
                            value_str = str(v)
                        metrics_list.append(f"• {k}: {value_str}")
                    # Truncate long lists for table view
                    preview_limit = 6
                    if len(metrics_list) > preview_limit:
                        hidden_count = len(metrics_list) - preview_limit
                        metrics_str = "\n".join(metrics_list[:preview_limit] + [f"… +{hidden_count} more"])
                    else:
                        metrics_str = "\n".join(metrics_list)
                else:
                    metrics_str = ""  # Empty string for no metrics
                
                # Convert tags to string with a cleaner format
                tags = sorted(set(step.get('tags', [])))  # Remove duplicates, sort for stability
                if tags:
                    tags_str = ", ".join(tags)
                else:
                    tags_str = ""  # Empty string for no tags
                
                status_symbol = "✅" if step['success'] else "❌"
                if step.get('skipped', False):
                    status_symbol = "⏭️"
                
                table_rows.append({
                    "Step": step['name'],
                    "Status": status_symbol,
                    "Message": step['message'],
                    "Time (s)": step['time_taken'],
                    "Attempts": step['attempts'],
                    "Metrics": metrics_str,
                    "Tags": tags_str
                })

            # Create DataFrame with specific column widths
            df = pd.DataFrame(table_rows)
            
            # Configure column widths and display settings
            column_config = {
                "Step": st.column_config.TextColumn(
                    "Step",
                    width="medium"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    width="small"
                ),
                "Message": st.column_config.TextColumn(
                    "Message",
                    width="large"
                ),
                "Time (s)": st.column_config.NumberColumn(
                    "Time (s)",
                    format="%.2f",
                    width="small"
                ),
                "Attempts": st.column_config.NumberColumn(
                    "Attempts",
                    width="small"
                ),
                "Metrics": st.column_config.TextColumn(
                    "Metrics",
                    width="large",
                    help="Derived metrics from the step execution"
                ),
                "Tags": st.column_config.TextColumn(
                    "Tags",
                    width="medium",
                    help="Tags associated with the step"
                )
            }
            
            # Display the DataFrame with custom configuration
            st.dataframe(
                df,
                column_config=column_config,
                use_container_width=True,
                hide_index=True
            )

            # Show full data and metrics/tags in expanders below the table
            for idx, step in enumerate(filtered_results):
                if step.get('data') not in (None, '', [], {}):
                    with st.expander(f"Full data for {step['name']}"):
                        st.json(step['data'])
                # Full metrics
                if step.get('derived_metrics'):
                    with st.expander(f"Metrics for {step['name']}"):
                        st.json(step['derived_metrics'])
                # Full tags
                if step.get('tags'):
                    with st.expander(f"Tags for {step['name']}"):
                        st.write(", ".join(sorted(set(step.get('tags', [])))))

            # Download full raw results
            st.download_button(
                label="Download results (JSON)",
                data=json.dumps(result, indent=2),
                file_name=f"workflow_results_{selected_workflow}.json",
                mime="application/json"
            )


    except Exception as e:
        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
