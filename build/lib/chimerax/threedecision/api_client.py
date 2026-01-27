"""
3decision API Client for ChimeraX

Handles all communication with the 3decision API endpoints.
Based on the PyMOL plugin API client with ChimeraX adaptations.
"""

import json
import requests
from typing import Optional, Dict, List, Any
import os
import configparser
import urllib3

# Disable SSL warnings when ignoring certificate verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ThreeDecisionAPIClient:
    """
    Client for interacting with 3decision API
    
    Note: SSL certificate verification is disabled for all requests
    to support local development servers and internal APIs.
    """
    
    def __init__(self, session):
        self.session = session  # ChimeraX session
        self.base_url = None
        self.api_key = None
        self.token = None
        self.http_session = requests.Session()
        # Disable SSL certificate verification for all requests
        self.http_session.verify = False
        self.config_file = os.path.expanduser("~/.3decision_chimerax_config")
        self.load_config()
        
    def log_info(self, message):
        """Log info message"""
        if hasattr(self.session, 'logger'):
            self.session.logger.info(f"threedecision: {message}")
        else:
            print(f"INFO: {message}")
    
    def log_error(self, message):
        """Log error message"""  
        if hasattr(self.session, 'logger'):
            self.session.logger.error(f"threedecision: {message}")
        else:
            print(f"ERROR: {message}")
            
    def log_warning(self, message):
        """Log warning message"""  
        if hasattr(self.session, 'logger'):
            self.session.logger.warning(f"threedecision: {message}")
        else:
            print(f"WARNING: {message}")
            
    def _make_authenticated_request(self, method, url, **kwargs):
        """Make an authenticated request with automatic token refresh"""
        if not self.is_authenticated():
            self.log_error("Not authenticated")
            return None
            
        # Add authorization header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        kwargs['headers'] = headers
        
        # Make initial request
        response = getattr(self.http_session, method.lower())(url, **kwargs)
        
        # If we get 401/403, try to refresh token once
        if response.status_code in [401, 403]:
            self.log_warning("Token expired, attempting to refresh")
            if self.login():
                # Update authorization header with new token
                headers['Authorization'] = f"Bearer {self.token}"
                # Retry request
                response = getattr(self.http_session, method.lower())(url, **kwargs)
            else:
                self.log_error("Token refresh failed")
                
        return response
            

        
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                config = configparser.ConfigParser()
                config.read(self.config_file)
                
                if 'API' in config:
                    self.base_url = config['API'].get('base_url')
                    self.api_key = config['API'].get('api_key')
                    self.token = config['API'].get('token')
                    
                    if self.token:
                        self.http_session.headers.update({
                            'Authorization': f'Bearer {self.token}',
                            'X-API-Version': '1'
                        })
                        
            except Exception as e:
                self.log_error(f"Error loading config: {e}")
                
    def save_config(self):
        """Save configuration to file"""
        try:
            config = configparser.ConfigParser()
            config['API'] = {
                'base_url': self.base_url or '',
                'api_key': self.api_key or '',
                'token': self.token or ''
            }
            
            with open(self.config_file, 'w') as f:
                config.write(f)
                
        except Exception as e:
            self.log_error(f"Error saving config: {e}")
            
    def configure(self, base_url: str, api_key: str):
        """Configure API settings"""
        # Ensure the URL includes the scheme
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'http://' + base_url
        
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.token = None
        
        # Update session headers
        self.http_session.headers.update({
            'Dng-Api-Key': self.api_key,
            'X-API-Version': '1',
            'User-Agent': 'ChimeraX-3decision-Plugin/1.1.3'
        })
        
        # Remove Authorization header if present
        if 'Authorization' in self.http_session.headers:
            del self.http_session.headers['Authorization']
            
    def is_configured(self) -> bool:
        """Check if API is configured"""
        return bool(self.base_url and self.api_key)
        
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (configured and connection works)"""
        return self.is_configured() and self.test_connection()
        
    def login(self) -> bool:
        """Login and get authentication token"""
        if not self.is_configured():
            return False
            
        try:
            url = f"{self.base_url}/auth/api/login"
            
            # Ensure we have the API key header for login
            headers = {
                'Dng-Api-Key': self.api_key,
                'X-API-Version': '1',
                'User-Agent': 'ChimeraX-3decision-Plugin/1.1.3'
            }
            
            response = self.http_session.get(url, headers=headers)
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                self.token = data.get('access_token')
                
                if self.token:
                    # Update session with token
                    self.http_session.headers.update({
                        'Authorization': f'Bearer {self.token}',
                        'X-API-Version': '1',
                        'User-Agent': 'ChimeraX-3decision-Plugin/1.1.3'
                    })
                    # Remove API key header as we now have token
                    if 'Dng-Api-Key' in self.http_session.headers:
                        del self.http_session.headers['Dng-Api-Key']
                    
                    self.save_config()
                    return True
                    
            self.log_error(f"Login failed: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            self.log_error(f"Login error: {e}")
            return False
            
    def test_connection(self) -> bool:
        """Test API connection"""
        if not self.is_configured():
            return False
            
        # If we have a token, assume it's valid and don't test
        # This avoids unnecessary login calls when we're already authenticated
        if self.token and 'Authorization' in self.http_session.headers:
            return True
            
        # Try to login if no token
        return self.login()
            
    def submit_search(self, query: str) -> Optional[Dict[str, Any]]:
        """Submit a search query and return job info"""
        if not self.test_connection():
            return None
            
        try:
            # Step 1: Submit search to get job ID
            url = f"{self.base_url}/search/{query}"
            
            response = self.http_session.get(url)
            
            # If we get 401/403, token might be expired - try to re-login once
            if response.status_code in [401, 403]:
                if self.login():
                    response = self.http_session.get(url)
                else:
                    self.log_error("Re-login failed")
                    return None
            
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    
                    # Extract job ID from response
                    job_id = data.get('id')
                    if job_id:
                        
                        # Step 2: Poll the queue endpoint to get results
                        queue_url = f"{self.base_url}/queues/basicSearch/jobs/{job_id}"
                        
                        queue_response = self.http_session.get(queue_url)
                        
                        if queue_response.status_code in [200, 201]:
                            queue_data = queue_response.json()
                            # Check progress - only proceed when it's 100
                            progress = queue_data.get("progress")
                            if progress is None:
                                progress = 0
                            if progress == 100:
                                
                                # Extract structure IDs from returnvalue.STRUCTURE_ID
                                structure_ids = []
                                if 'returnvalue' in queue_data and 'STRUCTURE_ID' in queue_data['returnvalue']:
                                    structure_ids = queue_data['returnvalue']['STRUCTURE_ID']
                                
                                # If we have structure IDs, fetch detailed info via GraphQL
                                if structure_ids:
                                    structures_info = self.get_structures_info(structure_ids)
                                    
                                    # Return the complete job data with structure details
                                    queue_data['structures_info'] = structures_info
                                    return queue_data
                                else:
                                    # Set empty structures_info to indicate job is complete with no results
                                    queue_data['structures_info'] = []
                                    return queue_data
                            else:
                                # Return job data without structure info to indicate polling needed
                                return {
                                    'id': job_id,
                                    'queue': 'basicSearch',
                                    'status': 'running',
                                    'progress': progress,
                                    'polling_needed': True
                                }
                        else:
                            self.log_error(f"Queue polling failed: {queue_response.status_code} - {queue_response.text}")
                            return None
                    else:
                        # If no ID, treat the response as direct results
                        return {
                            'id': 'direct',
                            'queue': 'direct',
                            'status': 'completed',
                            'result': data
                        }
                        
                except json.JSONDecodeError:
                    self.log_error(f"Non-JSON response from search: {response.text}")
                    return None
                    
            else:
                self.log_error(f"Search submission failed: {response.status_code}")
                self.log_error(f"Response text: {response.text}")
                return None
                
        except Exception as e:
            self.log_error(f"Search submission error: {e}")
            import traceback
            self.log_error(f"Full traceback: {traceback.format_exc()}")
            return None
            
    def get_job_status(self, queue_name: str, job_id: int) -> Optional[Dict[str, Any]]:
        """Get status of a job"""
        if not self.test_connection():
            return None
            
        try:
            url = f"{self.base_url}/queues/{queue_name}/jobs/{job_id}"
            
            response = self.http_session.get(url)
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data
            else:
                self.log_error(f"Job status check failed: {response.status_code}")
                self.log_error(f"Response text: {response.text}")
                return None
                
        except Exception as e:
            self.log_error(f"Job status error: {e}")
            import traceback
            self.log_error(f"Full traceback: {traceback.format_exc()}")
            return None
            
    def get_structures_info(self, structure_ids: List[int]) -> List[Dict[str, Any]]:
        """Get detailed information for structures using GraphQL"""
        if not self.test_connection():
            return []
            
        try:
            # If we have more than 500 structures, split into batches
            batch_size = 500
            all_structures = []
            
            if len(structure_ids) > batch_size:
                
                # Process in batches
                for i in range(0, len(structure_ids), batch_size):
                    batch_ids = structure_ids[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(structure_ids) + batch_size - 1) // batch_size
                    
                    
                    batch_structures = self._fetch_structures_batch(batch_ids)
                    if batch_structures:
                        all_structures.extend(batch_structures)
                
                return all_structures
            else:
                # For smaller datasets, use single request
                return self._fetch_structures_batch(structure_ids)
                
        except Exception as e:
            self.log_error(f"Structures info error: {e}")
            return []
            
    def _fetch_structures_batch(self, structure_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch a batch of structures using GraphQL"""
        try:
            # GraphQL query to get structure information
            query = """
            query GetStructuresInfo($ids: [Int!]!) {
                getStructuresInfo(ids: $ids) {
                    structure_id
                    general {
                        structure_id
                        external_code
                        title
                        method
                        resolution
                        created_date
                        imported_date
                        created_by
                        imported_by
                        source
                    }
                }
            }
            """
            
            variables = {"ids": structure_ids}
            
            url = f"{self.base_url}/graphql"
            payload = {
                "query": query,
                "variables": variables
            }
            
            
            response = self.http_session.post(url, json=payload)
            
            if response.status_code in [200, 201]:
                data = response.json()
                    
                if 'data' in data and 'getStructuresInfo' in data['data']:
                    batch_results = data['data']['getStructuresInfo']
                    
                    # Remove duplicates based on structure_id (NMR structures with multiple states)
                    seen_ids = set()
                    unique_structures = []
                    for structure in batch_results:
                        structure_id = structure.get('structure_id')
                        if structure_id and structure_id not in seen_ids:
                            seen_ids.add(structure_id)
                            unique_structures.append(structure)
                    
                    return unique_structures
                else:
                    self.log_error(f"Unexpected GraphQL response structure")
                    return []
            else:
                self.log_error(f"GraphQL batch query failed: {response.status_code}")
                self.log_error(f"Response text: {response.text}")
                return []
                
        except Exception as e:
            self.log_error(f"Batch fetch error: {e}")
            return []
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of available projects"""
        try:
            url = f"{self.base_url}/projects"
            headers = {"Accept": "application/json"}
            
            response = self._make_authenticated_request('GET', url, headers=headers)
            if not response:
                raise Exception("Failed to authenticate for projects request")
            
            if response.status_code == 200:
                projects_data = response.json()
                
                # Handle different response formats
                if isinstance(projects_data, list):
                    return projects_data
                elif isinstance(projects_data, dict):
                    # Check for 'projects' key first (as seen in actual response)
                    if 'projects' in projects_data:
                        return projects_data['projects']
                    # Check for 'results' key (alternative format)
                    elif 'results' in projects_data:
                        return projects_data['results']
                    else:
                        self.log_error(f"Unexpected projects response format: {projects_data}")
                        return []
                else:
                    self.log_error(f"Unexpected projects response format: {projects_data}")
                    return []
                    
            else:
                self.log_error(f"Projects request failed: {response.status_code}")
                self.log_error(f"Projects response text: {response.text}")
                raise Exception(f"Projects request failed: {response.status_code}")
                
        except Exception as e:
            self.log_error(f"Projects request error: {e}")
            import traceback
            self.log_error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def get_project_structures(self, project_id: str) -> List[Dict[str, Any]]:
        """Get structures from a specific project with transformation matrices"""
        if not self.is_authenticated():
            raise Exception("Not authenticated")
            
        try:
            url = f"{self.base_url}/projects/{project_id}/structures/matrix"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json"
            }
            
            response = self.http_session.get(url, headers=headers)
            
            if response.status_code == 200:
                structures_data = response.json()
                
                # Handle both list format and object format with results key
                if isinstance(structures_data, list):
                    return structures_data
                elif isinstance(structures_data, dict) and 'results' in structures_data:
                    return structures_data['results']
                else:
                    self.log_error(f"Unexpected project structures response format: {structures_data}")
                    return []
                    
            else:
                self.log_error(f"Project structures request failed: {response.status_code}")
                self.log_error(f"Project structures response text: {response.text}")
                raise Exception(f"Project structures request failed: {response.status_code}")
                
        except Exception as e:
            self.log_error(f"Project structures request error: {e}")
            import traceback
            self.log_error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def download_structures_zip(self, structure_ids: List[int], matrices: List[Dict] = None) -> Optional[bytes]:
        """Download structures as a ZIP file from the /exports/structure endpoint"""
        if not self.is_authenticated():
            raise Exception("Not authenticated")
            
        try:
            # Step 1: Submit export request to get domain event ID
            url = f"{self.base_url}/exports/structure"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Build the payload
            payload = {
                "structures_id": structure_ids
            }
            
            # Add matrices if provided
            if matrices:
                payload["matrix"] = matrices
            
            # Add output format parameter for ZIP file
            params = {
                "output_format": "structures-pdb-zip"
            }
            
            
            response = self.http_session.post(url, headers=headers, json=payload, params=params)
            
            if response.status_code in [200, 201]:
                # The export endpoint returns a domain event ID as plain text
                domain_event_id = response.text.strip()
                
                if domain_event_id:
                    # Step 2: Poll the domain events endpoint to check export status
                    domain_events_url = f"{self.base_url}/domain-events/{domain_event_id}"
                    
                    max_attempts = 30  # 30 attempts with 2-second intervals = 1 minute max
                    attempt = 0
                    
                    while attempt < max_attempts:
                        
                        domain_response = self.http_session.get(domain_events_url)
                        
                        if domain_response.status_code in [200, 201]:
                            try:
                                domain_data = domain_response.json()
                                
                                state = domain_data.get('state')
                                
                                if state == 'success':
                                    # Check if there are any export errors
                                    content = domain_data.get('content', {})
                                    errors = content.get('errors', {})
                                    not_exported = errors.get('not_exported', [])
                                    
                                    if not_exported:
                                        self.log_error(f"Export completed with errors: {not_exported}")
                                        return None
                                    else:
                                        
                                        # Extract filename from the response
                                        file_names = content.get('file_names', [])
                                        
                                        if file_names and len(file_names) > 0:
                                            first_file = file_names[0]
                                            
                                            if isinstance(first_file, dict):
                                                filename = first_file.get("file_name")
                                            else:
                                                self.log_error(f"Unexpected file_names structure: {type(first_file)} - {first_file}")
                                                return None
                                                
                                            if not filename:
                                                self.log_error("No filename found in file_names entry")
                                                return None
                                            
                                            # Remove extension from filename for URL parameter
                                            filename_without_ext = filename
                                            if '.' in filename:
                                                filename_without_ext = filename.rsplit('.', 1)[0]
                                            
                                            # Step 3: Download the actual ZIP file
                                            download_url = f"{self.base_url}/exports/structure/{domain_event_id}?filename={filename_without_ext}&download=true"
                                            
                                            
                                            download_response = self.http_session.get(download_url)
                                            
                                            if download_response.status_code in [200, 201]:
                                                zip_content = download_response.content
                                                
                                                # Verify it's actually a ZIP file
                                                if len(zip_content) > 4 and zip_content[:2] == b'PK':
                                                    return zip_content
                                                else:
                                                    return zip_content
                                            else:
                                                self.log_error(f"Download failed: {download_response.status_code}")
                                                return None
                                        else:
                                            self.log_error("No filename found in export response")
                                            return None
                                        
                                elif state == 'failed':
                                    self.log_error("Export failed")
                                    return None
                                else:
                                    # Still processing, wait and try again
                                    import time
                                    time.sleep(2)
                                    attempt += 1
                                    continue
                                    
                            except json.JSONDecodeError as e:
                                self.log_error(f"Failed to parse domain events response: {e}")
                                return None
                        else:
                            self.log_error(f"Domain events request failed: {domain_response.status_code}")
                            return None
                    
                    self.log_error("Export polling timed out")
                    return None
                else:
                    self.log_error("No domain event ID received")
                    return None
            else:
                self.log_error(f"Export request failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_error(f"ZIP download error: {e}")
            import traceback
            self.log_error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def export_structures_with_transforms(self, structures_with_transforms: List[Dict]) -> Optional[str]:
        """
        Export multiple structures with transformation matrices using batch export
        
        Args:
            structures_with_transforms: List of dicts with structure_id, external_code, and transform matrix
            
        Returns:
            PDB content as string (combined multi-MODEL for multiple structures), or None if failed
        """
        if not self.test_connection():
            return None
            
        try:
            # For multiple structures, we need to use ZIP format
            if len(structures_with_transforms) > 1:
                self.log_info(f"Exporting {len(structures_with_transforms)} structures with transformations as ZIP")
                
                # Build the matrix payload
                matrix_payload = [
                    {
                        "external_code": item["external_code"],
                        "structure_id": item["structure_id"],
                        "transform": item["transform"]
                    }
                    for item in structures_with_transforms
                ]
                
                # Get structure IDs for the download_structures_zip call
                structure_ids = [item["structure_id"] for item in structures_with_transforms]
                
                # Download as ZIP
                zip_content = self.download_structures_zip(structure_ids, matrix_payload)
                
                if not zip_content:
                    self.log_error("Failed to download structures as ZIP")
                    return None
                
                # Extract PDB files from ZIP and combine them into multi-MODEL format
                import zipfile
                import io
                
                combined_pdb = ""
                model_num = 1
                
                try:
                    with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                        # List all files in the ZIP
                        file_list = zip_ref.namelist()
                        self.log_info(f"ZIP contains {len(file_list)} files")
                        
                        # Process all PDB files in the ZIP
                        pdb_files = [f for f in file_list if f.endswith('.pdb')]
                        self.log_info(f"Found {len(pdb_files)} PDB files in ZIP")
                        
                        for pdb_filename in pdb_files:
                            pdb_content = zip_ref.read(pdb_filename).decode('utf-8')
                            
                            # Add MODEL/ENDMDL headers for multi-model format
                            combined_pdb += f"MODEL     {model_num}\n"
                            combined_pdb += pdb_content
                            if not pdb_content.endswith('\n'):
                                combined_pdb += '\n'
                            combined_pdb += "ENDMDL\n"
                            model_num += 1
                        
                        if combined_pdb:
                            self.log_info(f"Successfully combined {model_num - 1} structures into multi-MODEL PDB")
                            return combined_pdb
                        else:
                            self.log_error("No PDB files were extracted from ZIP")
                            return None
                            
                except zipfile.BadZipFile as e:
                    self.log_error(f"Invalid ZIP file: {e}")
                    return None
                except Exception as e:
                    self.log_error(f"Error extracting PDB files from ZIP: {e}")
                    import traceback
                    self.log_error(f"Full traceback: {traceback.format_exc()}")
                    return None
            
            else:
                # Single structure - use the text format
                url = f"{self.base_url}/exports/structure"
                
                # Build the payload with external_codes and matrix array
                matrix_payload = {
                    "external_codes": [item["external_code"] for item in structures_with_transforms],
                    "matrix": [
                        {
                            "external_code": item["external_code"],
                            "structure_id": item["structure_id"],
                            "transform": item["transform"]
                        }
                        for item in structures_with_transforms
                    ]
                }
                
                # Add format parameter for PDB text output
                params = {
                    "output_format": "structures-pdb-txt"
                }
                
                response = self.http_session.post(url, json=matrix_payload, params=params)
                
                if response.status_code in [200, 201]:
                    # The export endpoint returns a domain event ID as plain text
                    domain_event_id = response.text.strip()
                    
                    if domain_event_id:
                        # Poll the domain events endpoint to check export status
                        domain_events_url = f"{self.base_url}/domain-events/{domain_event_id}"
                        
                        max_attempts = 30
                        attempt = 0
                        
                        while attempt < max_attempts:
                            
                            domain_response = self.http_session.get(domain_events_url)
                            
                            if domain_response.status_code in [200, 201]:
                                try:
                                    domain_data = domain_response.json()
                                    state = domain_data.get('state')
                                    
                                    if state == 'success':
                                        # Check if there are any export errors
                                        content = domain_data.get('content', {})
                                        errors = content.get('errors', {})
                                        not_exported = errors.get('not_exported', [])
                                        
                                        if not_exported:
                                            self.log_error(f"Batch export completed with errors: {not_exported}")
                                            return None
                                        
                                        # Extract filename from the response
                                        file_names = content.get('file_names', [])
                                        if file_names and len(file_names) > 0:
                                            first_file = file_names[0]
                                            if isinstance(first_file, dict):
                                                filename = first_file.get("file_name")
                                            else:
                                                self.log_error(f"Unexpected file_names structure: {first_file}")
                                                return None
                                            
                                            if not filename:
                                                self.log_error("No filename found in file_names entry")
                                                return None
                                            
                                            # Remove extension from filename for URL parameter
                                            filename_without_ext = filename
                                            if '.' in filename:
                                                filename_without_ext = filename.rsplit('.', 1)[0]
                                            
                                            # Download the actual PDB file
                                            download_url = f"{self.base_url}/exports/structure/{domain_event_id}?filename={filename_without_ext}&download=true"
                                            
                                            download_response = self.http_session.get(download_url)
                                            
                                            if download_response.status_code == 200:
                                                pdb_content = download_response.text
                                                return pdb_content
                                            else:
                                                self.log_error(f"Failed to download PDB: {download_response.status_code}")
                                                return None
                                        else:
                                            self.log_error("No file_names found in export response")
                                            return None
                                            
                                    elif state == 'failed':
                                        self.log_error("Batch export failed")
                                        return None
                                        
                                except Exception as e:
                                    self.log_error(f"Error parsing domain event response: {e}")
                            
                            attempt += 1
                            if attempt < max_attempts:
                                import time
                                time.sleep(2)
                        
                        self.log_error("Batch export polling timed out")
                        return None
                    else:
                        self.log_error("No domain event ID received")
                        return None
                else:
                    self.log_error(f"Batch export request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            self.log_error(f"Batch export error: {e}")
            import traceback
            self.log_error(f"Full traceback: {traceback.format_exc()}")
            return None
            
    def get_associated_files(self, external_code: str) -> List[Dict[str, Any]]:
        """Get associated files for a structure by external code"""        
        try:
            url = f"{self.base_url}/structures/{external_code}/associated-files"
            headers = {"Accept": "application/json"}
            
            response = self._make_authenticated_request('GET', url, headers=headers)
            if not response:
                return []
            
            if response.status_code == 200:
                files_data = response.json()
                
                # Handle different response formats
                if isinstance(files_data, list):
                    return files_data
                elif isinstance(files_data, dict):
                    if 'files' in files_data:
                        return files_data['files']
                    elif 'results' in files_data:
                        return files_data['results']
                    else:
                        self.log_error(f"Unexpected associated files response format: {files_data}")
                        return []
                else:
                    self.log_error(f"Unexpected associated files response format: {files_data}")
                    return []
                    
            elif response.status_code == 404:
                # No associated files found - this is normal, not an error
                return []
            else:
                self.log_error(f"Associated files request failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.log_error(f"Associated files request error: {e}")
            return []
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific file"""
        if not self.is_authenticated():
            self.log_error("Not authenticated")
            return None
            
        try:
            url = f"{self.base_url}/structures/file/{file_id}"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json"
            }
            
            response = self.http_session.get(url, headers=headers)
            
            if response.status_code == 200:
                file_info = response.json()
                return file_info
            else:
                self.log_error(f"File info request failed: {response.status_code}")
                self.log_error(f"Response text: {response.text}")
                return None
                
        except Exception as e:
            self.log_error(f"File info request error: {e}")
            return None
    
    def download_file_by_id(self, file_id: str) -> Optional[bytes]:
        """Download file content by ID"""           
        try:
            url = f"{self.base_url}/structures/file/{file_id}/download"
            
            response = self._make_authenticated_request('GET', url)
            if not response:
                return None
            
            if response.status_code == 200:
                return response.content
            else:
                self.log_error(f"File download failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log_error(f"File download error: {e}")
            return None
            
    def download_file(self, file_info: Dict[str, Any]) -> Optional[bytes]:
        """Download file using file info dictionary"""
        # Extract file ID from different possible fields
        file_id = file_info.get('id') or file_info.get('file_id') or file_info.get('FILE_ID')
        
        if not file_id:
            # Try to get download URL directly
            download_url = file_info.get('download_url') or file_info.get('url')
            if download_url:
                return self._download_from_url(download_url)
            else:
                self.log_error("No file ID or download URL found in file info")
                return None
                
        return self.download_file_by_id(str(file_id))
        
    def _download_from_url(self, url: str) -> Optional[bytes]:
        """Download file from direct URL"""
        if not self.is_authenticated():
            self.log_error("Not authenticated")
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.token}"
            }
            
            response = self.http_session.get(url, headers=headers)
            
            if response.status_code == 200:
                content = response.content
                return content
            else:
                self.log_error(f"Direct URL download failed: {response.status_code}")
                self.log_error(f"Response text: {response.text}")
                return None
                
        except Exception as e:
            self.log_error(f"Direct URL download error: {e}")
            return None
