import requests
from typing import Optional, Dict, List, Any

API_URL = "http://localhost:3003"

def get_jobs(limit: int = 10, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Fetch jobs from API with pagination and filters"""
    try:
        params = {
            'offset': offset,
            **(filters or {})
        }
        
        # Convert list filters to multiple query params
        query_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_params.append(f"{key}={item}")
            else:
                query_params.append(f"{key}={value}")
        
        url = f"{API_URL}/jobs/search?{'&'.join(query_params)}"
        print(url)
        response = requests.get(url)
        response.raise_for_status()
        
        jobs = response.json()
        return [{
            'description': job.get('description', ''),
            'title': job.get('title', '')
        } for job in jobs]
        
    except Exception as e:
        st.error(f"Failed to fetch jobs: {str(e)}")
        raise

def get_filter_options() -> Dict[str, List[str]]:
    """Fetch available filter options from API"""
    try:
        response = requests.get(f"{API_URL}/jobs/filter-options")
        response.raise_for_status()
        data = response.json()
        
        return {
            'categories': [option['key'] for option in data.get('categories', [])],
            'locations': [option['key'] for option in data.get('locations', [])],
            'projectTypes': [option['key'] for option in data.get('projectTypes', [])],
            'paymentTypes': [option['key'] for option in data.get('paymentTypes', [])],
            'skills': data.get('skills', [])
        }
    except Exception as e:
        st.error(f"Failed to fetch filter options: {str(e)}")
        raise