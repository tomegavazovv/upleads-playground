import streamlit as st
from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from google.cloud import firestore
from prompts.company_info_prompt import company_info_prompt
from utils.flatten_dict import flatten_dict
from db.db import get_jobs
from models.suitability_rating import SuitabilityRating
from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_openai import ChatOpenAI
from utils.get_model import get_model, available_models
import json
from streamlit_js import st_js
from db.db import get_filter_options, get_jobs


def create_streamlit_app():
    st.set_page_config(layout="wide")

    # Initialize session state variables
    if 'job_offset' not in st.session_state:
        st.session_state.job_offset = 0
    if 'loaded_jobs' not in st.session_state:
        st.session_state.loaded_jobs = []
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = 'gpt-4o'
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    if 'title_filter' not in st.session_state:
        st.session_state.title_filter = ''
    
    st.markdown("""
        <style>
        .st-key-jobs-container {
            height: 70vh;
            max-height: 70vh;
            min-height: 70vh;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #ddd;
        }

        #text_area_1, div[data-testid="stTextArea"] textarea {
            background-color: white !important;
            padding: 10px;
            border: 1px solid #ddd;
            min-height: 50vh;
            max-height: 50vh;
        }

        .st-key-load_more_jobs_container{
            width: 100%;
            display: flex !important;
            justify-content: center;
            align-items: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Load prompt from localStorage when app starts
    stored_prompt = st_js("""
        try {
            const stored = localStorage.getItem('companyPrompt');
            if (!stored) return null;
            return stored;
        } catch (e) {
            console.error('Error accessing stored prompt:', e);
            return null;
        }
    """)
    
    # If stored_prompt is [], the JavaScript hasn't finished executing yet
    if stored_prompt == []:
        st.stop()  # Stop execution and wait for next rerun
    
    # Initialize company_prompt in session state if not present
    if 'company_prompt' not in st.session_state:
        if stored_prompt:
            try:
                # Handle the case where stored_prompt is a list
                if isinstance(stored_prompt, list):
                    cleaned_prompt = ''.join(stored_prompt)
                else:
                    cleaned_prompt = stored_prompt
                
                # Remove outer quotes if present and unescape
                cleaned_prompt = cleaned_prompt.strip('"').encode().decode('unicode_escape')
                st.session_state.company_prompt = cleaned_prompt
            except Exception as e:
                st.session_state.company_prompt = company_info_prompt  # fallback to default prompt
        else:
            st.session_state.company_prompt = company_info_prompt  # fallback to default prompt
    
    # Replace single model selection with multiple model selection
    selected_models = st.multiselect(
        "Choose models",
        options=available_models,
        default=available_models
    )
    
    # Update session state to store multiple models
    if 'selected_models' not in st.session_state:
        st.session_state.selected_models = selected_models

    # Get filter options from API
    filter_options = get_filter_options()

    # Filter section
    with st.expander("Filter Jobs"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Title filter
            st.session_state.title_filter = st.text_input("Job Title", value=st.session_state.title_filter)
            
            # Category filter
            selected_categories = st.multiselect(
                "Categories",
                options=filter_options['categories'],
                default=st.session_state.filters.get('categories', [])
            )
            
            # Location filter
            selected_locations = st.multiselect(
                "Locations",
                options=filter_options['locations'],
                default=st.session_state.filters.get('locations', [])
            )
            
        with col2:
            # Project Type filter
            selected_project_types = st.multiselect(
                "Project Types",
                options=filter_options['projectTypes'],
                default=st.session_state.filters.get('projectTypes', [])
            )
            
            # Payment Type filter
            selected_payment_types = st.multiselect(
                "Payment Types",
                options=filter_options['paymentTypes'],
                default=st.session_state.filters.get('paymentTypes', [])
            )
            
            # Skills filter
            selected_skills = st.multiselect(
                "Skills",
                options=filter_options['skills'],
                default=st.session_state.filters.get('skills', [])
            )
        
        # Apply filters button
        if st.button("Apply Filters"):
            st.session_state.filters = {
                'categories': selected_categories,
                'locations': selected_locations,
                'projectTypes': selected_project_types,
                'paymentTypes': selected_payment_types,
                'skills': selected_skills
            }
            if st.session_state.title_filter:
                st.session_state.filters['title'] = st.session_state.title_filter
            st.session_state.job_offset = 0  # Reset offset when applying new filters
            st.session_state.loaded_jobs = get_jobs(offset=0, filters=st.session_state.filters)
            st.rerun()

    col1, col2 = st.columns([1, 1])
    
    
    # Left column - Display the prompt and model selection
    with col1:
        
        
        # Update the selected model in session state if changed
        if selected_models != st.session_state.selected_models:
            st.session_state.selected_models = selected_models
        
        # Replace the disabled text area with an editable one and store in session state
        edited_prompt = st.text_area(
            "Edit Prompt", 
            value=st.session_state.company_prompt, 
            height=400,
            key="prompt_textarea"
        )
        
        # Add update button
        if st.button("Update Prompt", type="primary"):
            st.session_state.company_prompt = edited_prompt
            # Store in localStorage using st_js
            st_js(f"""
                localStorage.setItem('companyPrompt', JSON.stringify({json.dumps(edited_prompt)}));
                console.log('Prompt updated:', {json.dumps(edited_prompt)});
            """)
            st.success("Prompt updated successfully!")
    
    # Right column - Display jobs
    with col2:
        with st.container(key='jobs-container'):
            
            # Fetch new jobs and append to existing ones
            new_jobs = get_jobs(offset=st.session_state.job_offset, filters=st.session_state.filters)
            if not st.session_state.loaded_jobs or st.session_state.job_offset == 0:
                st.session_state.loaded_jobs = new_jobs
            
            # Display all loaded jobs
            for job in st.session_state.loaded_jobs:
                with st.container():
                    st.markdown(f"### {job['title']}")
                    
                    
                    
                    # Create a collapsible section for the full description
                    st.write(job['description'])
                    
                    # Modify the analyze button section to handle multiple models
                    if st.button(f"Analyze Suitability", key=f"analyze_{job['title']}"):
                        with st.spinner("Analyzing job suitability..."):
                            import asyncio
                            import concurrent.futures
                            
                            def analyze_with_model(model_name):
                                model = get_model(model_name)
                                suitability_agent = model.with_structured_output(SuitabilityRating)
                                
                                # Get the prompt from session state, fallback to default if not set
                                current_prompt = st.session_state.get('company_prompt', company_info_prompt)
                                
                                messages = [
                                    {"role": "system", "content": current_prompt},
                                    {"role": "user", "content": f"Job Title: {job['title']}\n\nJob Description: {job['description']}"}
                                ]
                                
                                return model_name, suitability_agent.invoke(messages)
                            
                            # Use ThreadPoolExecutor for parallel execution
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                futures = [executor.submit(analyze_with_model, model) for model in selected_models]
                                results = [future.result() for future in concurrent.futures.as_completed(futures)]
                            
                            # Display results for each model
                            for model_name, result in results:
                                score = int(result.suitability_score)
                                color = "#ff6666" if score < 40 else "#ffaa66" if score < 70 else "#66bb66"
                                st.markdown(f"""
                                    <div style='padding: 10px; margin-bottom: 10px; background-color: {color}; border-radius: 5px;'>
                                        <h4 style='color: white;'>{model_name} - Suitability Score: {score}/100</h4>
                                        <p style='color: white;'>{result.reason}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                    st.markdown("---")
                      
            
            with st.container(key='load_more_jobs_container'):
              if st.button("Load More Jobs", type="primary", use_container_width=True):
                  st.session_state.job_offset += 10
                  new_jobs = get_jobs(offset=st.session_state.job_offset, filters=st.session_state.filters)
                  st.session_state.loaded_jobs.extend(new_jobs)
                  st.rerun()

if __name__ == "__main__":
    create_streamlit_app()

