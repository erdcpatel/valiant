import streamlit as st
import asyncio
import json
from pathlib import Path
import sys
import pandas as pd

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from valiant.framework.api import ValiantAPI
from valiant.ui.logger import streamlit_logger


def render_metrics_for_table(metrics):
    """Render metrics in a simple format for DataFrame display"""
    if not metrics:
        return "—"  # Em dash for empty
    
    metrics_list = []
    for key, value in sorted(metrics.items()):
        if isinstance(value, float):
            value_str = f"{value:.3f}"
        else:
            value_str = str(value)
        metrics_list.append(f"• {key}: {value_str}")
    
    # Limit to first 3 items for table display
    if len(metrics_list) > 3:
        return "\n".join(metrics_list[:3] + [f"... +{len(metrics_list)-3} more"])
    return "\n".join(metrics_list)


def render_tags_for_table(tags):
    """Render tags in a simple format for DataFrame display"""
    if not tags:
        return "—"  # Em dash for empty
    return ", ".join(sorted(tags))


def main():
    st.set_page_config(
        page_title="Workflow Execution Monitor",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Initialize session state for workflow results
    if 'workflow_result' not in st.session_state:
        st.session_state.workflow_result = None
    if 'selected_workflow_name' not in st.session_state:
        st.session_state.selected_workflow_name = None
    
    # Enhanced CSS for professional look
    st.markdown("""
        <style>
        /* Global improvements */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }
        
        /* Custom section headers */
        .section-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 20px 0 15px 0;
            font-weight: 600;
            font-size: 1.1em;
            text-align: center;
        }
        
        /* Filter container */
        .filter-container {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0 25px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Results header styling */
        .results-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Status indicators */
        .status-success { color: #28a745; font-size: 1.4em; text-align: center; }
        .status-error { color: #dc3545; font-size: 1.4em; text-align: center; }
        .status-skipped { color: #6c757d; font-size: 1.4em; text-align: center; }
        
        /* Enhanced button styling */
        .stButton > button {
            border-radius: 8px;
            border: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        /* Improved form controls */
        .stSelectbox > div > div {
            border-radius: 8px;
        }
        
        .stMultiSelect > div > div {
            border-radius: 8px;
        }
        
        .stCheckbox > label {
            font-weight: 500;
        }
        
        /* Enhanced table styling */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        
        .stDataFrame table {
            border-collapse: separate !important;
            border-spacing: 0 !important;
        }
        
        .stDataFrame th {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 15px 10px !important;
            text-align: center !important;
            font-size: 0.95em !important;
        }
        
        .stDataFrame td {
            padding: 12px 8px !important;
            border-bottom: 1px solid #e9ecef !important;
            vertical-align: top !important;
            font-size: 0.9em !important;
        }
        
        /* Alternating row colors */
        .stDataFrame tbody tr:nth-child(even) {
            background-color: #f8f9fa !important;
        }
        
        .stDataFrame tbody tr:hover {
            background-color: #e8f4f8 !important;
        }
        
        /* Specific column styling */
        .stDataFrame td:nth-child(1) { font-weight: 600; max-width: 180px; }
        .stDataFrame td:nth-child(2) { text-align: center; width: 80px; }
        .stDataFrame td:nth-child(3) { max-width: 250px; }
        .stDataFrame td:nth-child(4), .stDataFrame td:nth-child(5) { 
            text-align: center; width: 90px; font-family: monospace; 
        }
        .stDataFrame td:nth-child(6) { max-width: 200px; }
        .stDataFrame td:nth-child(7) { max-width: 180px; }
        
        /* Success/Error styling */
        .alert-success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .alert-warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        /* Expander improvements */
        .streamlit-expanderHeader {
            background-color: #f1f3f4;
            border-radius: 8px;
            padding: 8px 15px;
        }
        
        /* Info boxes */
        .stInfo {
            border-radius: 8px;
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
        selected_workflow = st.selectbox("Choose Workflow", list(workflows.keys()))
        # Get input schema
        input_schema = ValiantAPI.get_workflow_input_schema(selected_workflow)

        # Render dynamic form
        user_inputs = {}
        if input_schema:
            # Create a more organized layout for form fields
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

        # Run workflow button
        st.markdown("")
        if st.button("▶️ Run Workflow", type="primary", use_container_width=True):
                with st.spinner("🔄 Running workflow..."):
                    streamlit_logger.info(f"Running workflow: {selected_workflow}")
                    result = asyncio.run(ValiantAPI.run_workflow(
                        selected_workflow,
                        context_overrides=user_inputs
                    ))
                    streamlit_logger.info(f"Workflow completed: {selected_workflow}")
                    
                    # Store results in session state
                    st.session_state.workflow_result = result
                    st.session_state.selected_workflow_name = selected_workflow
                    st.rerun()

        # Display results if available (either from current run or previous run)
        if st.session_state.workflow_result is not None:
            result = st.session_state.workflow_result
            workflow_name = st.session_state.selected_workflow_name
            
            # Compact results header in a single row
            st.markdown("---")
            summary = result.get('summary', {})
            header_cols = st.columns([5, 1, 1])
            
            with header_cols[0]:
                # Inline title and stats
                st.markdown(f"**📊 {workflow_name}** &nbsp;&nbsp;|&nbsp;&nbsp; "
                          f"Total: {summary.get('total_steps', 0)} &nbsp; "
                          f"✅ {summary.get('successful_steps', 0)} &nbsp; "
                          f"❌ {summary.get('total_steps', 0) - summary.get('successful_steps', 0) - summary.get('skipped_steps', 0)} &nbsp; "
                          f"⏭️ {summary.get('skipped_steps', 0)}")
            
            with header_cols[1]:
                st.download_button(
                    label="� Download JSON",
                    data=json.dumps(result, indent=2),
                    file_name=f"workflow_{workflow_name}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with header_cols[2]:
                if st.button("🗑️ Clear", type="secondary", use_container_width=True):
                    st.session_state.workflow_result = None
                    st.session_state.selected_workflow_name = None
                    if 'selected_step_detail' in st.session_state:
                        del st.session_state.selected_step_detail
                    st.rerun()
            
            # Extract all unique tags from the workflow results
            all_tags = set()
            tag_counts = {}
            for step in result['results']:
                step_tags = step.get('tags', [])
                all_tags.update(step_tags)
                for tag in step_tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Sort tags for consistent display
            available_tags = sorted(list(all_tags))
            
            # Compact filter layout in a single row
            filter_row = st.columns([1, 1, 2])
            
            with filter_row[0]:
                only_failed = st.checkbox("🚫 Show only failed", value=False, key="filter_failed")
            
            with filter_row[1]:
                only_with_metrics = st.checkbox("📊 Only steps with metrics", value=False, key="filter_metrics")
            
            with filter_row[2]:
                if available_tags:
                    # Create options with tag counts for better UX
                    tag_options = [f"{tag} ({tag_counts[tag]})" for tag in available_tags]
                    selected_tag_options = st.multiselect(
                        "🏷️ Filter by tags", 
                        options=tag_options,
                        default=[],
                        key="filter_tags",
                        help=f"Select from {len(available_tags)} available tags. Shows steps with ANY of the selected tags.",
                        label_visibility="visible"
                    )
                    # Extract just the tag names from the selected options
                    selected_tags = [option.split(' (')[0] for option in selected_tag_options]
                else:
                    selected_tags = []
                    st.caption("No tags available")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Workflow execution summary - Fixed to use correct API response structure
            if result.get('summary', {}).get('successful_steps', 0) > 0:
                st.markdown(f"""
                <div class="alert-success">
                    <strong>✅ Success!</strong> Workflow '{workflow_name}' completed successfully with 
                    {result['summary']['successful_steps']} successful steps
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-warning">
                    <strong>⚠️ Warning!</strong> Workflow '{workflow_name}' completed but no steps executed successfully
                </div>
                """, unsafe_allow_html=True)
            
            # Apply filters to results
            filtered_results = result['results']
            total_steps = len(filtered_results)
            
            if only_failed:
                filtered_results = [s for s in filtered_results if not s.get('success') and s.get('executed')]
            if only_with_metrics:
                filtered_results = [s for s in filtered_results if s.get('derived_metrics')]
            if selected_tags:
                # Filter steps that have ANY of the selected tags (OR condition)
                def has_any_selected_tags(step):
                    step_tags = {tag.lower() for tag in step.get('tags', [])}
                    required_tags = {tag.lower() for tag in selected_tags}
                    return bool(required_tags.intersection(step_tags))  # ANY tag matches
                filtered_results = [s for s in filtered_results if has_any_selected_tags(s)]

            # Show filter results
            filtered_count = len(filtered_results)
            if filtered_count != total_steps:
                filter_info = []
                if only_failed:
                    filter_info.append("failed steps only")
                if only_with_metrics:
                    filter_info.append("steps with metrics only")
                if selected_tags:
                    if len(selected_tags) == 1:
                        filter_info.append(f"steps with tag: {selected_tags[0]}")
                    else:
                        filter_info.append(f"steps with any of these tags: {', '.join(selected_tags)}")
                
                filter_text = " | ".join(filter_info) if filter_info else "filters applied"
                st.info(f"Showing {filtered_count} of {total_steps} steps ({filter_text})")

            if not filtered_results:
                st.warning("No steps match the current filters")
                return

            table_rows = []
            for step in filtered_results:
                # Format metrics using plain text for table display
                metrics_text = render_metrics_for_table(step.get('derived_metrics', {}))
                
                # Format tags using plain text for table display  
                tags_text = render_tags_for_table(step.get('tags', []))
                
                status_symbol = "✅" if step['success'] else "❌"
                if step.get('skipped', False):
                    status_symbol = "⏭️"
                
                # Truncate long messages for better table display
                message = step['message']
                if len(message) > 60:
                    message = message[:60] + "..."
                
                table_rows.append({
                    "Step": step['name'],
                    "Status": status_symbol,
                    "Message": message,
                    "Time (s)": step['time_taken'],
                    "Attempts": step['attempts'],
                    "Metrics": metrics_text,
                    "Tags": tags_text
                })

            # Create DataFrame with specific column widths
            df = pd.DataFrame(table_rows)
            
            # Table header with download options
            table_header_cols = st.columns([4, 1])
            with table_header_cols[0]:
                st.markdown("##### 📋 Workflow Steps")
            with table_header_cols[1]:
                # CSV download button
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name=f"workflow_steps_{workflow_name}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Configure column widths and display settings
            column_config = {
                "Step": st.column_config.TextColumn("Step", width="medium"),
                "Status": st.column_config.TextColumn("", width="small"),
                "Message": st.column_config.TextColumn("Message", width="large"),
                "Time (s)": st.column_config.NumberColumn("Time", format="%.3f", width="small"),
                "Attempts": st.column_config.NumberColumn("#", width="small"),
                "Metrics": st.column_config.TextColumn("Metrics", width="medium"),
                "Tags": st.column_config.TextColumn("Tags", width="medium")
            }
            
            # Calculate dynamic height based on number of rows (35px per row + 45px header)
            row_height = 35
            header_height = 45
            max_height = 600
            min_height = 150
            calculated_height = min(max(len(filtered_results) * row_height + header_height, min_height), max_height)
            
            # Display the DataFrame with custom configuration (full screen)
            st.dataframe(
                df,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                height=calculated_height
            )
            
            # Add action buttons for detailed view
            st.markdown("#### � Step Details")
            st.markdown("Click on any step below to view detailed information:")
            
            # Create a simple list of buttons for each step
            cols = st.columns(min(3, len(filtered_results)))  # Max 3 columns
            for idx, step in enumerate(filtered_results):
                col = cols[idx % len(cols)]
                with col:
                    button_key = f"detail_btn_{idx}"
                    if st.button(f"📋 {step['name']}", key=button_key, use_container_width=True):
                        # Store the selected step in session state
                        st.session_state.selected_step_detail = step
            
            # Display selected step details
            if 'selected_step_detail' in st.session_state and st.session_state.selected_step_detail:
                selected_step = st.session_state.selected_step_detail
                
                st.markdown("---")
                st.markdown(f"### 📊 Details for: {selected_step['name']}")
                
                # Create tabs for different types of information
                tab1, tab2, tab3 = st.tabs(["📋 Overview", "📊 Metrics", "📦 Raw Data"])
                
                with tab1:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Step Information:**")
                        st.markdown(f"- **Status:** {'✅ Success' if selected_step['success'] else '❌ Failed' if not selected_step.get('skipped') else '⏭️ Skipped'}")
                        st.markdown(f"- **Time Taken:** {selected_step['time_taken']:.3f} seconds")
                        st.markdown(f"- **Attempts:** {selected_step['attempts']}")
                        st.markdown(f"- **Executed:** {'Yes' if selected_step.get('executed', True) else 'No'}")
                    with col2:
                        st.markdown("**Message:**")
                        st.info(selected_step['message'])
                
                with tab2:
                    if selected_step.get('derived_metrics'):
                        st.markdown("**Derived Metrics:**")
                        metrics_df = pd.DataFrame([
                            {"Metric": k, "Value": v, "Type": type(v).__name__}
                            for k, v in selected_step['derived_metrics'].items()
                        ])
                        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
                        
                        # Download metrics as JSON
                        st.download_button(
                            "📥 Download Metrics (JSON)",
                            data=json.dumps(selected_step['derived_metrics'], indent=2),
                            file_name=f"metrics_{selected_step['name'].replace(' ', '_')}.json",
                            mime="application/json"
                        )
                    else:
                        st.info("No metrics available for this step.")
                
                with tab3:
                    if selected_step.get('data') not in (None, '', [], {}):
                        st.markdown("**Raw Step Data:**")
                        st.json(selected_step['data'])
                        
                        # Download raw data as JSON
                        st.download_button(
                            "📥 Download Step Data (JSON)",
                            data=json.dumps(selected_step['data'], indent=2),
                            file_name=f"stepdata_{selected_step['name'].replace(' ', '_')}.json",
                            mime="application/json"
                        )
                    else:
                        st.info("No additional data available for this step.")
                
                # Clear selection button
                st.markdown("---")
                if st.button("❌ Close Details", use_container_width=True):
                    if 'selected_step_detail' in st.session_state:
                        del st.session_state.selected_step_detail
                    st.rerun()


    except Exception as e:
        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
