"""
3decision GUI for ChimeraX

Main tool interface for the 3decision plugin.
Provides search, project browsing, and associated files functionality.
"""

from chimerax.core.tools import ToolInstance
from chimerax.ui import MainToolWindow
from chimerax.ui.widgets import ItemTable

# Import Qt through ChimeraX's path
try:
    from Qt.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
        QLabel, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
        QHeaderView, QProgressBar, QCheckBox, QAbstractItemView, 
        QSplitter, QTextEdit, QGroupBox, QFormLayout
    )
    from Qt.QtCore import Qt, QThread, QTimer
    from Qt.QtGui import QIcon, QPixmap
    
    # Try different ways to import the signal
    try:
        from Qt.QtCore import pyqtSignal
    except ImportError:
        try:
            from Qt.QtCore import Signal as pyqtSignal
        except ImportError:
            try:
                from PyQt6.QtCore import pyqtSignal
            except ImportError:
                try:
                    from PyQt5.QtCore import pyqtSignal
                except ImportError:
                    from PySide6.QtCore import Signal as pyqtSignal
    
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from .api_client import ThreeDecisionAPIClient
from .settings import SettingsDialog


def get_object_name(external_code: str, label: str = None, source: str = None) -> str:
    """
    Determine the best object name for a structure in ChimeraX.
    
    Naming logic:
    - For public domain structures (RCSB PDB, PDB, AlphaFold, etc.): use external_code (e.g., '1abo')
    - For private/internal structures with a label: use the label
    - Fallback: use external_code
    
    The name is sanitized to be valid for ChimeraX (no spaces, special chars replaced).
    """
    # Define public/known sources where external_code is meaningful
    public_sources = [
        'rcsb', 'pdb', 'alphafold', 'uniprot', 'chembl', 'drugbank',
        'pubchem', 'zinc', 'emdb', 'wwpdb'
    ]
    
    # Check if it's a public domain structure
    is_public = False
    if source:
        source_lower = source.lower()
        is_public = any(ps in source_lower for ps in public_sources)
    
    # Determine the name to use
    if is_public:
        # Use external_code for public structures (it's the PDB code, etc.)
        name = external_code
    elif label and label.strip() and label.lower() not in ['n/a', 'null', 'none', '']:
        # Use label for private structures if available
        name = label.strip()
    else:
        # Fallback to external_code
        name = external_code
    
    # Strip '3dec_' prefix if present (from API file naming)
    if name.lower().startswith('3dec_'):
        name = name[5:]
    
    # Sanitize name for ChimeraX (replace invalid characters)
    # ChimeraX model names should be alphanumeric with underscores
    sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    
    # Ensure we have a valid name
    if not sanitized:
        sanitized = external_code if external_code else 'structure'
    
    return sanitized


class NumericTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that sorts numerically instead of alphabetically"""
    def __init__(self, text, numeric_value):
        super().__init__(text)
        self.numeric_value = numeric_value
    
    def __lt__(self, other):
        """Override less-than comparison for sorting"""
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class SearchThread(QThread):
    """Thread for handling search operations"""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self, api_client, search_query):
        super().__init__()
        self.api_client = api_client
        self.search_query = search_query
        
    def run(self):
        try:
            self.status_update.emit("Submitting search...")
            job_response = self.api_client.submit_search(self.search_query)
            
            if not job_response:
                self.error_occurred.emit("Failed to submit search")
                return
            
            # Check if we have structure info already included
            if 'structures_info' in job_response:
                structures = job_response['structures_info']
                self.status_update.emit(f"Search completed. Found {len(structures)} structures.")
                self.results_ready.emit(structures)
                return
            
            # Check if we need to poll for progress
            if job_response.get('polling_needed'):
                job_id = job_response.get('id')
                queue_name = job_response.get('queue', 'basicSearch')
                
                if not job_id:
                    self.error_occurred.emit("No job ID received from search")
                    return
                
                self.status_update.emit(f"Job submitted (ID: {job_id}). Waiting for completion...")
                
                max_attempts = 60
                attempt = 0
                
                while attempt < max_attempts:
                    try:
                        result = self.api_client.get_job_status(queue_name, job_id)
                        
                        if result:
                            progress = result.get('progress', 0)
                            finished_on = result.get('finishedOn')
                            return_value = result.get('returnvalue')
                            
                            self.status_update.emit(f"Search progress: {progress}%")
                            
                            # Check if job is completed (either by finishedOn timestamp or progress 100% with return value)
                            is_finished = (finished_on is not None) or (progress == 100 and return_value is not None)
                            
                            if is_finished:
                                structure_ids = []
                                if (return_value is not None and 
                                    isinstance(return_value, dict) and 
                                    'STRUCTURE_ID' in return_value):
                                    structure_ids = return_value['STRUCTURE_ID']
                                
                                if structure_ids:
                                    self.status_update.emit("Fetching structure details...")
                                    structures = self.api_client.get_structures_info(structure_ids)
                                    self.results_ready.emit(structures)
                                else:
                                    self.status_update.emit("Search completed with no results.")
                                    self.results_ready.emit([])
                                return
                            elif result.get('status') == 'failed':
                                self.error_occurred.emit("Search job failed")
                                return
                        
                        self.msleep(2000)  # 2 seconds
                        attempt += 1
                        
                    except Exception as e:
                        self.api_client.log_error(f"Polling error: {e}")
                        attempt += 1
                        self.msleep(2000)
                
                self.error_occurred.emit("Search timed out waiting for completion")
                return
                
        except Exception as e:
            self.error_occurred.emit(f"Search error: {str(e)}")

class LoadStructuresThread(QThread):
    """Thread for loading structures with optional transformation matrices"""
    pdb_content_ready = pyqtSignal(str, list)  # pdb_content, structure_info_list
    all_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self, api_client, structures):
        super().__init__()
        self.api_client = api_client
        self.structures = structures
        
    def run(self):
        try:
            # Check if any structures have transformation matrices
            has_matrices = any(s.get('matrix') is not None for s in self.structures)
            
            if has_matrices:
                # Use batch export with transformation matrices
                self.api_client.log_info("Loading structures with transformation matrices using batch export")
                self.status_update.emit("Loading structures with transformations...")
                
                # Prepare structures for batch export
                structures_with_transforms = []
                for structure_info in self.structures:
                    structure_id = int(structure_info['structure_id'])
                    external_code = structure_info['external_code']
                    matrix = structure_info.get('matrix')
                    
                    # Identity matrix as default (no transformation)
                    identity_matrix = [
                        1.0, 0.0, 0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        0.0, 0.0, 0.0, 1.0
                    ]
                    
                    if matrix:
                        # Matrix should be a 4x4 nested list, flatten it to 16 values
                        if isinstance(matrix, list) and len(matrix) == 4:
                            flat_matrix = []
                            for row in matrix:
                                if isinstance(row, list) and len(row) == 4:
                                    flat_matrix.extend(row)
                                else:
                                    self.api_client.log_error(f"Invalid matrix row format for structure {structure_id}: {row}")
                                    flat_matrix = None
                                    break
                            
                            if flat_matrix and len(flat_matrix) == 16:
                                structures_with_transforms.append({
                                    "structure_id": structure_id,
                                    "external_code": external_code,
                                    "transform": flat_matrix
                                })
                            else:
                                self.api_client.log_error(f"Invalid matrix format for structure {structure_id}, using identity matrix")
                                structures_with_transforms.append({
                                    "structure_id": structure_id,
                                    "external_code": external_code,
                                    "transform": identity_matrix
                                })
                        else:
                            self.api_client.log_error(f"Invalid matrix structure for {structure_id}, using identity matrix")
                            structures_with_transforms.append({
                                "structure_id": structure_id,
                                "external_code": external_code,
                                "transform": identity_matrix
                            })
                    else:
                        # No matrix provided, use identity matrix (no transformation)
                        structures_with_transforms.append({
                            "structure_id": structure_id,
                            "external_code": external_code,
                            "transform": identity_matrix
                        })
                
                # Get batch PDB with transformations applied
                pdb_content = self.api_client.export_structures_with_transforms(structures_with_transforms)
                
                if pdb_content:
                    self.status_update.emit(f"Loaded {len(self.structures)} structures with transformations")
                    # Emit the PDB content with structure info
                    self.pdb_content_ready.emit(pdb_content, self.structures)
                else:
                    self.error_occurred.emit("Failed to load structures with transformations")
                    
            else:
                # Load structures individually without transformations (search results)
                self.api_client.log_info("Loading structures individually without transformations")
                self.status_update.emit("Loading structures...")
                
                # For structures without matrices, load them individually from 3decision
                combined_pdb = ""
                model_num = 1
                
                for structure_info in self.structures:
                    structure_id = int(structure_info['structure_id'])
                    external_code = structure_info['external_code']
                    
                    try:
                        # Load structure directly from 3decision using single structure export
                        single_structure = [{
                            "structure_id": structure_id,
                            "external_code": external_code,
                            "transform": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]  # Identity matrix
                        }]
                        
                        pdb_content = self.api_client.export_structures_with_transforms(single_structure)
                        
                        if pdb_content:
                            # Add MODEL/ENDMDL headers for multi-model format
                            combined_pdb += f"MODEL     {model_num}\n"
                            combined_pdb += pdb_content
                            if not pdb_content.endswith('\n'):
                                combined_pdb += '\n'
                            combined_pdb += "ENDMDL\n"
                            model_num += 1
                            
                            self.api_client.log_info(f"Downloaded {external_code} from 3decision")
                        else:
                            self.api_client.log_error(f"Failed to download structure {external_code} from 3decision")
                            
                    except Exception as e:
                        self.api_client.log_error(f"Error downloading structure {external_code}: {e}")
                
                if combined_pdb:
                    # Emit the combined PDB content with structure info
                    self.pdb_content_ready.emit(combined_pdb, self.structures)
                else:
                    self.error_occurred.emit("Failed to download any structures from 3decision")
            
            self.all_completed.emit()
                    
        except Exception as e:
            self.error_occurred.emit(f"Loading error: {str(e)}")

class ThreeDecisionTool(ToolInstance):
    """Main 3decision tool for ChimeraX"""

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        self.display_name = "Discngine 3decision"
        self.api_client = ThreeDecisionAPIClient(session)
        
        # Initialize threads
        self.search_thread = None
        self.load_thread = None
        
        # Create tool window
        self.tool_window = MainToolWindow(self)
        
        if QT_AVAILABLE:
            self._build_gui()
        else:
            self._build_simple_interface()
        
        # Show the tool window
        self.tool_window.manage(placement="side")

    def _build_gui(self):
        """Build the GUI interface"""
        # Main widget
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Discngine 3decision")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0066cc; margin: 5px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Help button
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(30, 30)
        self.help_button.clicked.connect(self.open_help)
        self.help_button.setToolTip("Help Documentation")
        header_layout.addWidget(self.help_button)
        
        # Settings button
        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(30, 30)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setToolTip("Settings")
        header_layout.addWidget(self.settings_button)
        
        main_layout.addLayout(header_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Search tab
        self.search_widget = self._create_search_tab()
        self.tab_widget.addTab(self.search_widget, "Search")
        
        # Projects tab
        self.projects_widget = self._create_projects_tab()
        self.tab_widget.addTab(self.projects_widget, "Projects")
        
        # Associated Files tab
        self.files_widget = self._create_files_tab()
        self.tab_widget.addTab(self.files_widget, "Associated Files")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("Ready - Configure API settings to begin")
        self.status_label.setStyleSheet("color: gray; padding: 5px;")
        main_layout.addWidget(self.status_label)
        
        main_widget.setLayout(main_layout)
        
        # Add the widget to the tool window properly
        ui_area_layout = QVBoxLayout()
        ui_area_layout.addWidget(main_widget)
        self.tool_window.ui_area.setLayout(ui_area_layout)
        
        # Check login status
        self.check_login_status()
        
        # Track if projects have been loaded
        self.projects_loaded = False
        
        # Initialize storage for filtering
        self.all_search_results = []
        self.all_projects = []
        self.all_project_structures = []

    def _create_search_tab(self):
        """Create the search tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Search input
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term (e.g., ABL1, kinase)")
        self.search_input.returnPressed.connect(self.submit_search)
        search_layout.addWidget(self.search_input)
        
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_search)
        search_layout.addWidget(self.submit_button)
        
        layout.addLayout(search_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Column filters section
        filters_label = QLabel("Filter Results:")
        filters_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(filters_label)
        
        filters_layout = QHBoxLayout()
        
        # Filter inputs for each column (skip checkbox column)
        self.filter_external_code = QLineEdit()
        self.filter_external_code.setPlaceholderText("External Code")
        self.filter_external_code.textChanged.connect(self.apply_search_filters)
        filters_layout.addWidget(self.filter_external_code)
        
        self.filter_label = QLineEdit()
        self.filter_label.setPlaceholderText("Label")
        self.filter_label.textChanged.connect(self.apply_search_filters)
        filters_layout.addWidget(self.filter_label)
        
        self.filter_title = QLineEdit()
        self.filter_title.setPlaceholderText("Title")
        self.filter_title.textChanged.connect(self.apply_search_filters)
        filters_layout.addWidget(self.filter_title)
        
        self.filter_method = QLineEdit()
        self.filter_method.setPlaceholderText("Method")
        self.filter_method.textChanged.connect(self.apply_search_filters)
        filters_layout.addWidget(self.filter_method)
        
        # Resolution filter with range support (min-max)
        self.filter_resolution = QLineEdit()
        self.filter_resolution.setPlaceholderText("Resolution (e.g., <2.0)")
        self.filter_resolution.textChanged.connect(self.apply_search_filters)
        filters_layout.addWidget(self.filter_resolution)
        
        self.filter_source = QLineEdit()
        self.filter_source.setPlaceholderText("Source")
        self.filter_source.textChanged.connect(self.apply_search_filters)
        filters_layout.addWidget(self.filter_source)
        
        # Clear filters button
        clear_filters_btn = QPushButton("Clear")
        clear_filters_btn.clicked.connect(self.clear_search_filters)
        filters_layout.addWidget(clear_filters_btn)
        
        layout.addLayout(filters_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "External Code", "Label", "Title", "Method", "Resolution", "Source"
        ])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow multiple row selection
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable editing
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        
        # Enable sorting by clicking column headers
        self.results_table.setSortingEnabled(True)
        
        layout.addWidget(self.results_table)
        
        # Load button
        load_layout = QHBoxLayout()
        load_layout.addStretch()
        
        self.load_button = QPushButton("Load Selected Structures")
        self.load_button.clicked.connect(self.load_selected_structures)
        self.load_button.setEnabled(False)
        load_layout.addWidget(self.load_button)
        
        layout.addLayout(load_layout)
        widget.setLayout(layout)
        return widget

    def _create_projects_tab(self):
        """Create the projects tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        layout.addWidget(QLabel("Browse and load structures from your 3decision projects"))
        
        # Projects list on top
        layout.addWidget(QLabel("Projects:"))
        
        # Projects filters
        projects_filters_layout = QHBoxLayout()
        
        self.projects_filter_name = QLineEdit()
        self.projects_filter_name.setPlaceholderText("Project Name")
        self.projects_filter_name.textChanged.connect(self.apply_projects_filters)
        projects_filters_layout.addWidget(self.projects_filter_name)
        
        self.projects_filter_structures = QLineEdit()
        self.projects_filter_structures.setPlaceholderText("Structures (e.g., >10)")
        self.projects_filter_structures.textChanged.connect(self.apply_projects_filters)
        projects_filters_layout.addWidget(self.projects_filter_structures)
        
        self.projects_filter_owner = QLineEdit()
        self.projects_filter_owner.setPlaceholderText("Owner")
        self.projects_filter_owner.textChanged.connect(self.apply_projects_filters)
        projects_filters_layout.addWidget(self.projects_filter_owner)
        
        # Clear projects filters button
        clear_projects_filters_btn = QPushButton("Clear")
        clear_projects_filters_btn.clicked.connect(self.clear_projects_filters)
        projects_filters_layout.addWidget(clear_projects_filters_btn)
        
        layout.addLayout(projects_filters_layout)
        
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(3)
        self.projects_table.setHorizontalHeaderLabels(["Project Name", "Structures", "Owner"])
        self.projects_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.projects_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable editing
        self.projects_table.setAlternatingRowColors(True)
        self.projects_table.setSortingEnabled(True)  # Enable sorting
        self.projects_table.itemSelectionChanged.connect(self.on_project_selection_changed)
        layout.addWidget(self.projects_table)
        
        # Projects buttons
        projects_buttons = QHBoxLayout()
        refresh_button = QPushButton("Refresh Projects")
        refresh_button.clicked.connect(self.load_projects)
        projects_buttons.addWidget(refresh_button)
        projects_buttons.addStretch()
        layout.addLayout(projects_buttons)
        
        # Project structures list below
        layout.addWidget(QLabel("Project Structures:"))
        
        # Project structures filters
        project_filters_layout = QHBoxLayout()
        
        self.project_filter_structure_id = QLineEdit()
        self.project_filter_structure_id.setPlaceholderText("Structure ID")
        self.project_filter_structure_id.textChanged.connect(self.apply_project_structures_filters)
        project_filters_layout.addWidget(self.project_filter_structure_id)
        
        self.project_filter_external_code = QLineEdit()
        self.project_filter_external_code.setPlaceholderText("External Code")
        self.project_filter_external_code.textChanged.connect(self.apply_project_structures_filters)
        project_filters_layout.addWidget(self.project_filter_external_code)
        
        self.project_filter_description = QLineEdit()
        self.project_filter_description.setPlaceholderText("Description")
        self.project_filter_description.textChanged.connect(self.apply_project_structures_filters)
        project_filters_layout.addWidget(self.project_filter_description)
        
        # Clear project structures filters button
        clear_project_filters_btn = QPushButton("Clear")
        clear_project_filters_btn.clicked.connect(self.clear_project_structures_filters)
        project_filters_layout.addWidget(clear_project_filters_btn)
        
        layout.addLayout(project_filters_layout)
        
        self.project_structures_table = QTableWidget()
        self.project_structures_table.setColumnCount(4)
        self.project_structures_table.setHorizontalHeaderLabels(["Structure ID", "External Code", "Description", "Files"])
        self.project_structures_table.setColumnWidth(3, 80)  # Files button column
        self.project_structures_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.project_structures_table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow multiple row selection
        self.project_structures_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable editing
        self.project_structures_table.setAlternatingRowColors(True)
        self.project_structures_table.setSortingEnabled(True)  # Enable sorting
        layout.addWidget(self.project_structures_table)
        
        # Structure selection buttons
        structure_buttons = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_project_structures)
        structure_buttons.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_none_project_structures)
        structure_buttons.addWidget(select_none_btn)
        
        structure_buttons.addStretch()
        
        self.load_project_structures_button = QPushButton("Load Selected Structures")
        self.load_project_structures_button.clicked.connect(self.load_selected_project_structures)
        self.load_project_structures_button.setEnabled(False)
        structure_buttons.addWidget(self.load_project_structures_button)
        
        layout.addLayout(structure_buttons)
        widget.setLayout(layout)
        return widget

    def _create_files_tab(self):
        """Create the associated files tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header with current structure info
        self.files_header_label = QLabel("Associated Files - Select a structure from the Projects tab to view its files")
        layout.addWidget(self.files_header_label)
        
        # Checkbox to apply transformation matrix
        transform_layout = QHBoxLayout()
        self.apply_transform_checkbox = QCheckBox("Apply transformation matrix to associated files (if available)")
        self.apply_transform_checkbox.setToolTip("When enabled, associated files (maps, etc.) will be transformed using the structure's reference transformation matrix")
        self.apply_transform_checkbox.setChecked(True)  # Default to enabled
        transform_layout.addWidget(self.apply_transform_checkbox)
        transform_layout.addStretch()
        layout.addLayout(transform_layout)
        
        # Files table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["File Name", "Type", "Size", "Format", "Description"])
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.files_table.setAlternatingRowColors(True)
        layout.addWidget(self.files_table)
        
        # Buttons for file operations
        files_buttons = QHBoxLayout()
        
        self.refresh_files_button = QPushButton("Refresh Files")
        self.refresh_files_button.clicked.connect(self.refresh_associated_files)
        self.refresh_files_button.setEnabled(False)
        files_buttons.addWidget(self.refresh_files_button)
        
        files_buttons.addStretch()
        
        self.open_file_button = QPushButton("Open in ChimeraX")
        self.open_file_button.clicked.connect(self.open_selected_file)
        self.open_file_button.setEnabled(False)
        files_buttons.addWidget(self.open_file_button)
        
        self.open_system_button = QPushButton("Download && Open with System")
        self.open_system_button.setToolTip("Download the file and open it with the system's default application (useful for PDFs, images, etc.)")
        self.open_system_button.clicked.connect(self.download_and_open_with_system)
        self.open_system_button.setEnabled(False)
        files_buttons.addWidget(self.open_system_button)
        
        layout.addLayout(files_buttons)
        
        # Status label for file operations
        self.files_status_label = QLabel("")
        layout.addWidget(self.files_status_label)
        
        widget.setLayout(layout)
        return widget

    # Associated Files functionality
    def view_structure_files(self, structure):
        """View associated files for a structure"""
        if not QT_AVAILABLE or not structure:
            return
            
        structure_id = str(structure.get('STRUCTURE_ID', structure.get('structure_id', '')))
        external_code = structure.get('EXTERNAL_CODE', structure.get('external_code', structure_id))
        
        # Store current structure for file operations
        self.current_structure = structure
        self.current_structure_id = structure_id
        self.current_external_code = external_code
        
        # Extract and store transformation matrix if available
        self.current_transform_matrix = None
        matrix = structure.get('TRANSFORM_MATRIX')
        if not matrix:
            ref_transforms = structure.get('ReferenceTransforms')
            if ref_transforms and isinstance(ref_transforms, dict):
                transform = ref_transforms.get('transform')
                if transform and isinstance(transform, list) and len(transform) == 16:
                    # Store as 4x4 nested array
                    matrix = [
                        transform[0:4],
                        transform[4:8],
                        transform[8:12],
                        transform[12:16]
                    ]
        self.current_transform_matrix = matrix
        
        # Update header and switch to files tab
        matrix_status = " (with transformation matrix)" if matrix else ""
        self.files_header_label.setText(f"Associated Files for {external_code} (ID: {structure_id}){matrix_status}")
        self.tab_widget.setCurrentIndex(2)  # Switch to Associated Files tab
        
        # Enable refresh button
        self.refresh_files_button.setEnabled(True)
        
        # Load files using external_code, not structure_id
        self.load_associated_files(external_code)
        
    def load_associated_files(self, external_code):
        """Load associated files for a structure using external code"""
        try:
            self.files_status_label.setText("Loading associated files...")
            
            # Get associated files from API using external_code
            files = self.api_client.get_associated_files(external_code)
            
            if files:
                self.populate_files_table(files)
                self.files_status_label.setText(f"Loaded {len(files)} associated files")
            else:
                self.files_table.setRowCount(0)
                self.files_status_label.setText("No associated files found")
                
        except Exception as e:
            self.files_status_label.setText(f"Error loading files: {str(e)}")
            self.files_table.setRowCount(0)
            
    def populate_files_table(self, files):
        """Populate the files table with file data"""
        self.files_table.setRowCount(len(files))
        
        for row, file_info in enumerate(files):
            # Extract file information using correct API response field names
            filename = file_info.get('file_name', 'Unknown')
            file_type = file_info.get('file_type_label', 'Unknown')
            file_size = "N/A"  # Size not provided in API response
            file_extension = file_info.get('file_type_extension', '')
            file_format = self._get_file_format_from_extension(file_extension, filename)
            description = file_info.get('file_desc', '') or ''
            
            # Create table items
            self.files_table.setItem(row, 0, QTableWidgetItem(filename))
            self.files_table.setItem(row, 1, QTableWidgetItem(str(file_type)))
            self.files_table.setItem(row, 2, QTableWidgetItem(str(file_size)))
            self.files_table.setItem(row, 3, QTableWidgetItem(file_format))
            self.files_table.setItem(row, 4, QTableWidgetItem(description))
            
            # Store full file data for later use
            self.files_table.item(row, 0).setData(Qt.UserRole, file_info)
            
        # Enable file operation buttons
        self.files_table.itemSelectionChanged.connect(self._on_file_selection_changed)
        
    def _get_file_format_from_extension(self, extension, filename=""):
        """Determine file format from extension and filename"""
        if not extension:
            # Fallback to extracting from filename
            if filename and '.' in filename:
                extension = filename.lower().split('.')[-1]
            else:
                return "Unknown"
                
        extension = extension.lower()
        
        format_map = {
            'pdb': 'PDB Structure',
            'cif': 'mmCIF Structure', 
            'dsn6': 'DSN6 Map',
            'xplor': 'XPLOR Map',
            'cns': 'CNS Map',
            'mtz': 'MTZ Reflection',
            'mrc': 'MRC Map',
            'dx': 'DX Map',
            'sdf': 'SDF Molecule',
            'mol2': 'MOL2 Molecule',
            'xyz': 'XYZ Coordinates',
            'ccp4': 'CCP4 Map',
            'as': 'RDock Grid'
        }
        
        return format_map.get(extension, f"{extension.upper()} File" if extension else "Unknown")
        
    def _on_file_selection_changed(self):
        """Handle file selection change"""
        selected_items = self.files_table.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.open_file_button.setEnabled(has_selection)
        self.open_system_button.setEnabled(has_selection)
        
    def refresh_associated_files(self):
        """Refresh the associated files list"""
        if hasattr(self, 'current_external_code'):
            self.load_associated_files(self.current_external_code)
            

    def open_selected_file(self):
        """Open the selected file in ChimeraX"""
        selected_row = self.files_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self.tool_window.ui_area, "Warning", "Please select a file to open")
            return
            
        file_item = self.files_table.item(selected_row, 0)
        if not file_item:
            return
            
        file_info = file_item.data(Qt.UserRole)
        filename = file_item.text()
        file_format = self.files_table.item(selected_row, 3).text()
        
        # Check if format is supported
        supported_formats = ['PDB Structure', 'mmCIF Structure', 'DSN6 Map', 'XPLOR Map', 
                           'CNS Map', 'MTZ Reflection', 'MRC Map', 'DX Map', 'SDF Molecule', 
                           'MOL2 Molecule', 'XYZ Coordinates', 'CCP4 Map']
        
        # Formats that ChimeraX cannot open but can be opened with system apps
        system_open_formats = ['RDock Grid', 'AS File', 'PDF File', 'PNG File', 'JPG File', 
                              'JPEG File', 'TIF File', 'TIFF File', 'DOC File', 'DOCX File',
                              'XLS File', 'XLSX File', 'CSV File', 'TXT File']
        
        if file_format not in supported_formats:
            # Check if it's a format that can be opened with system app
            if file_format in system_open_formats or file_format.endswith(' File'):
                QMessageBox.information(self.tool_window.ui_area, "Use System Application", 
                                      f"'{file_format}' files cannot be opened directly in ChimeraX.\n\n"
                                      f"Use the 'Download & Open with System' button to open this file "
                                      f"with your system's default application.")
            else:
                QMessageBox.warning(self.tool_window.ui_area, "Unsupported Format", 
                                  f"File format '{file_format}' is not supported for direct opening in ChimeraX.\n\n"
                                  f"You can try using 'Download & Open with System' to open it with "
                                  f"your system's default application.")
            return
            
        try:
            self.files_status_label.setText(f"Opening {filename} in ChimeraX...")
            
            # Download file first
            file_data = self.api_client.download_file(file_info)
            
            if file_data:
                # Save to temporary file
                import tempfile
                import os
                
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                # Open in ChimeraX using appropriate command
                from chimerax.core.commands import run
                
                # Determine ChimeraX command based on file format
                if 'Structure' in file_format or 'Molecule' in file_format:
                    model_spec = run(self.session, f'open "{file_path}"')[0]
                elif 'Map' in file_format:
                    model_spec = run(self.session, f'open "{file_path}"')[0]
                elif 'Reflection' in file_format:
                    model_spec = run(self.session, f'open "{file_path}"')[0]
                else:
                    model_spec = run(self.session, f'open "{file_path}"')[0]
                
                # Apply transformation matrix if checkbox is checked and matrix is available
                if self.apply_transform_checkbox.isChecked() and hasattr(self, 'current_transform_matrix') and self.current_transform_matrix:
                    try:
                        # Get the last opened model
                        if self.session.models.list():
                            last_model = self.session.models.list()[-1]
                            
                            # Convert 4x4 matrix to flat list if needed
                            matrix = self.current_transform_matrix
                            if isinstance(matrix, list) and len(matrix) == 4:
                                # Convert nested 4x4 to flat 16-value list
                                flat_matrix = []
                                for row in matrix:
                                    flat_matrix.extend(row)
                                matrix = flat_matrix
                            
                            # Create transformation matrix string for ChimeraX
                            # ChimeraX matrix format: row-major 3x4 (rotation + translation)
                            # We have 4x4, so we use first 3 rows
                            if len(matrix) == 16:
                                # Extract 3x4 transformation (first 3 rows)
                                m = matrix
                                matrix_str = f"{m[0]},{m[1]},{m[2]},{m[3]},{m[4]},{m[5]},{m[6]},{m[7]},{m[8]},{m[9]},{m[10]},{m[11]}"
                                
                                # Apply transformation using ChimeraX move command
                                run(self.session, f'view matrix mod #{last_model.id_string},{matrix_str}')
                                self.files_status_label.setText(f"Opened {filename} with transformation matrix applied")
                            else:
                                self.files_status_label.setText(f"Opened {filename} (transformation matrix format not recognized)")
                    except Exception as matrix_error:
                        # Log warning but don't fail - file is already opened
                        self.session.logger.warning(f"Could not apply transformation matrix: {str(matrix_error)}")
                        self.files_status_label.setText(f"Opened {filename} (could not apply transformation)")
                else:
                    self.files_status_label.setText(f"Opened {filename} in ChimeraX")
                
            else:
                self.files_status_label.setText("Failed to download file")
                QMessageBox.warning(self.tool_window.ui_area, "Error", "Failed to download file for opening")
                
        except Exception as e:
            self.files_status_label.setText(f"Error opening file: {str(e)}")
            QMessageBox.critical(self.tool_window.ui_area, "Open Error", str(e))

    def download_and_open_with_system(self):
        """Download the selected file and open it with the system's default application.
        
        This is useful for files that ChimeraX cannot open directly (PDFs, images, documents, etc.).
        Works cross-platform on Windows, macOS, and Linux.
        """
        selected_row = self.files_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self.tool_window.ui_area, "Warning", "Please select a file to download")
            return
            
        file_item = self.files_table.item(selected_row, 0)
        if not file_item:
            return
            
        file_info = file_item.data(Qt.UserRole)
        filename = file_item.text()
        
        try:
            self.files_status_label.setText(f"Downloading {filename}...")
            
            # Download file
            file_data = self.api_client.download_file(file_info)
            
            if file_data:
                import tempfile
                import os
                import sys
                import subprocess
                
                # Save to a persistent temp location (not just tempfile that gets deleted)
                # Use a subdirectory to keep things organized
                temp_dir = os.path.join(tempfile.gettempdir(), '3decision_downloads')
                os.makedirs(temp_dir, exist_ok=True)
                file_path = os.path.join(temp_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                self.files_status_label.setText(f"Opening {filename} with system application...")
                
                # Open with system default application - cross-platform
                self._open_file_with_system(file_path)
                
                self.files_status_label.setText(f"Downloaded and opened {filename}")
                
            else:
                self.files_status_label.setText("Failed to download file")
                QMessageBox.warning(self.tool_window.ui_area, "Error", "Failed to download file")
                
        except Exception as e:
            self.files_status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self.tool_window.ui_area, "Error", f"Failed to download and open file: {str(e)}")
    
    def _open_file_with_system(self, file_path: str):
        """Open a file with the system's default application.
        
        Cross-platform implementation for Windows, macOS, and Linux.
        
        Args:
            file_path: The path to the file to open
        """
        import sys
        import subprocess
        import os
        
        if sys.platform == 'darwin':  # macOS
            subprocess.run(['open', file_path], check=True)
        elif sys.platform == 'win32':  # Windows
            # os.startfile is Windows-only and opens with default app
            os.startfile(file_path)
        else:  # Linux and other Unix-like systems
            # xdg-open is the standard way to open files on Linux
            subprocess.run(['xdg-open', file_path], check=True)

    def _build_simple_interface(self):
        """Build simple interface when Qt is not available"""
        # Create a simple label
        simple_widget = QLabel("3decision Tool\n\nQt interface not available.\nUse command: threedecision search <query>")
        simple_widget.setAlignment(Qt.AlignCenter)
        self.tool_window.ui_area.setWidget(simple_widget)
        
        # Log that the tool is available
        self.session.logger.info("3decision tool loaded - use 'threedecision search <query>' command")

    def on_tab_changed(self, index):
        """Handle tab change events"""
        if index == 1:  # Projects tab (0=Search, 1=Projects, 2=Files)
            # Auto-load projects if not already loaded and API client is configured
            if not self.projects_loaded and self.api_client and self.api_client.is_configured():
                self.load_projects()

    def open_help(self):
        """Open help documentation in default browser"""
        import webbrowser
        help_url = "https://3decision-help.discngine.cloud/en/plugins/chimerax"
        try:
            webbrowser.open(help_url)
            self.api_client.log_info(f"Opening help documentation: {help_url}")
        except Exception as e:
            self.api_client.log_error(f"Failed to open help URL: {e}")
            QMessageBox.warning(self.tool_window.ui_area, "Error", 
                              f"Failed to open help documentation.\nPlease visit: {help_url}")

    def open_settings(self):
        """Open the settings dialog"""
        if QT_AVAILABLE:
            dialog = SettingsDialog(self.api_client, self.tool_window.ui_area)
            # Use exec() for PyQt6/PySide6 or exec_() for PyQt5
            try:
                result = dialog.exec()
            except AttributeError:
                result = dialog.exec_()
            
            if result == dialog.Accepted:
                self.check_login_status()
        else:
            self.session.logger.info("Settings dialog requires Qt interface")

    def check_login_status(self):
        """Check login status and update UI"""
        if hasattr(self, 'status_label'):
            if self.api_client.is_authenticated():
                self.status_label.setText("Connected to 3decision API")
                self.status_label.setStyleSheet("color: green; padding: 5px;")
                if hasattr(self, 'submit_button'):
                    self.submit_button.setEnabled(True)
            else:
                self.status_label.setText("Not connected - Configure API settings")
                self.status_label.setStyleSheet("color: red; padding: 5px;")
                if hasattr(self, 'submit_button'):
                    self.submit_button.setEnabled(False)

    def submit_search(self):
        """Submit search query"""
        if not QT_AVAILABLE:
            return
            
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self.tool_window.ui_area, "Warning", "Please enter a search term")
            return
            
        if not self.api_client.is_configured():
            QMessageBox.warning(self.tool_window.ui_area, "Warning", "Please configure API settings first")
            return
            
        # Start search in background thread
        self.search_thread = SearchThread(self.api_client, query)
        self.search_thread.results_ready.connect(self.display_results)
        self.search_thread.error_occurred.connect(self.handle_search_error)
        self.search_thread.status_update.connect(self.update_status)
        
        self.submit_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        self.search_thread.start()

    def display_results(self, structures):
        """Display search results"""
        if not QT_AVAILABLE:
            return
            
        self.submit_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Store all results for filtering
        self.all_search_results = structures
        
        # Display all results initially
        self.populate_search_results_table(structures)
        
        if len(structures) == 0:
            QMessageBox.information(self.tool_window.ui_area, "Search Results", "No structures found.")
        else:
            QMessageBox.information(self.tool_window.ui_area, "Search Results", f"Found {len(structures)} structures.")
    
    def populate_search_results_table(self, structures):
        """Populate the search results table with given structures"""
        # Disable sorting while populating for better performance
        self.results_table.setSortingEnabled(False)
        
        self.results_table.setRowCount(len(structures))
        
        for row, structure in enumerate(structures):
            # Get general info
            general = structure.get('general', {})
            
            # External Code
            external_code = general.get('external_code', str(structure.get('structure_id', '')))
            item = QTableWidgetItem(external_code)
            item.setData(Qt.UserRole, structure)  # Store structure data
            self.results_table.setItem(row, 0, item)
            
            # Label
            self.results_table.setItem(row, 1, QTableWidgetItem(external_code))
            
            # Title
            title = general.get('title', 'N/A')
            self.results_table.setItem(row, 2, QTableWidgetItem(title))
            
            # Method
            method = general.get('method', 'N/A')
            self.results_table.setItem(row, 3, QTableWidgetItem(method))
            
            # Resolution - use custom numeric sorting
            resolution = general.get('resolution')
            resolution_text = f"{resolution:.2f} Å" if resolution else "N/A"
            # Use large number for N/A to sort to the end
            numeric_value = resolution if resolution is not None else float('inf')
            resolution_item = NumericTableWidgetItem(resolution_text, numeric_value)
            self.results_table.setItem(row, 4, resolution_item)
            
            # Source
            source = general.get('source', 'N/A')
            self.results_table.setItem(row, 5, QTableWidgetItem(source))
        
        # Re-enable sorting after populating
        self.results_table.setSortingEnabled(True)
        
        self.load_button.setEnabled(len(structures) > 0)

    def handle_search_error(self, error_message):
        """Handle search errors"""
        if QT_AVAILABLE:
            self.submit_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self.tool_window.ui_area, "Search Error", error_message)

    def update_status(self, message):
        """Update status message"""
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)

    def clear_search_filters(self):
        """Clear all search filter inputs"""
        # Block signals to prevent triggering apply_search_filters while clearing
        self.filter_external_code.blockSignals(True)
        self.filter_label.blockSignals(True)
        self.filter_title.blockSignals(True)
        self.filter_method.blockSignals(True)
        self.filter_resolution.blockSignals(True)
        self.filter_source.blockSignals(True)
        
        self.filter_external_code.clear()
        self.filter_label.clear()
        self.filter_title.clear()
        self.filter_method.clear()
        self.filter_resolution.clear()
        self.filter_source.clear()
        
        # Unblock signals
        self.filter_external_code.blockSignals(False)
        self.filter_label.blockSignals(False)
        self.filter_title.blockSignals(False)
        self.filter_method.blockSignals(False)
        self.filter_resolution.blockSignals(False)
        self.filter_source.blockSignals(False)
        
        # Apply empty filters to show all results
        self.apply_search_filters()
    
    def parse_resolution_filter(self, filter_text):
        """
        Parse resolution filter string.
        Supports formats: <2.0, >1.5, <=2.0, >=1.5, 1.5-3.0, 2.0
        Returns: (min_value, max_value, operator)
        """
        if not filter_text:
            return None, None, None
        
        filter_text = filter_text.strip()
        
        # Range format: 1.5-3.0
        if '-' in filter_text and not filter_text.startswith('-'):
            parts = filter_text.split('-')
            if len(parts) == 2:
                try:
                    min_val = float(parts[0].strip())
                    max_val = float(parts[1].strip())
                    return min_val, max_val, 'range'
                except ValueError:
                    return None, None, None
        
        # Operator formats: <, >, <=, >=
        if filter_text.startswith('<='):
            try:
                val = float(filter_text[2:].strip())
                return None, val, '<='
            except ValueError:
                return None, None, None
        elif filter_text.startswith('>='):
            try:
                val = float(filter_text[2:].strip())
                return val, None, '>='
            except ValueError:
                return None, None, None
        elif filter_text.startswith('<'):
            try:
                val = float(filter_text[1:].strip())
                return None, val, '<'
            except ValueError:
                return None, None, None
        elif filter_text.startswith('>'):
            try:
                val = float(filter_text[1:].strip())
                return val, None, '>'
            except ValueError:
                return None, None, None
        
        # Exact value or equals
        try:
            val = float(filter_text)
            return val, val, '='
        except ValueError:
            return None, None, None
    
    def check_resolution_filter(self, resolution, min_val, max_val, operator):
        """Check if resolution value passes the filter"""
        if resolution is None:
            return False  # N/A values don't pass numeric filters
        
        if operator == 'range':
            return min_val <= resolution <= max_val
        elif operator == '<':
            return resolution < max_val
        elif operator == '<=':
            return resolution <= max_val
        elif operator == '>':
            return resolution > min_val
        elif operator == '>=':
            return resolution >= min_val
        elif operator == '=':
            # Allow small tolerance for floating point comparison
            return abs(resolution - min_val) < 0.01
        
        return True
    
    def apply_search_filters(self):
        """Apply column filters to the search results table"""
        if not hasattr(self, 'all_search_results') or not self.all_search_results:
            return
        
        # Get filter values
        filter_ext_code = self.filter_external_code.text().strip().lower()
        filter_lbl = self.filter_label.text().strip().lower()
        filter_ttl = self.filter_title.text().strip().lower()
        filter_mth = self.filter_method.text().strip().lower()
        filter_res = self.filter_resolution.text().strip()
        filter_src = self.filter_source.text().strip().lower()
        
        # Parse resolution filter
        res_min, res_max, res_operator = self.parse_resolution_filter(filter_res)
        
        # Filter structures
        filtered_structures = []
        for structure in self.all_search_results:
            general = structure.get('general', {})
            
            # Text filters (case-insensitive contains)
            if filter_ext_code and filter_ext_code not in general.get('external_code', '').lower():
                continue
            if filter_lbl and filter_lbl not in general.get('external_code', '').lower():  # Label same as external code
                continue
            if filter_ttl and filter_ttl not in general.get('title', '').lower():
                continue
            if filter_mth and filter_mth not in general.get('method', '').lower():
                continue
            if filter_src and filter_src not in general.get('source', '').lower():
                continue
            
            # Resolution filter (numeric)
            if filter_res:
                resolution = general.get('resolution')
                if not self.check_resolution_filter(resolution, res_min, res_max, res_operator):
                    continue
            
            filtered_structures.append(structure)
        
        # Update table with filtered results
        self.populate_search_results_table(filtered_structures)

    def load_selected_structures(self):
        """Load selected structures from search results"""
        if not QT_AVAILABLE:
            return
            
        selected_structures = []
        
        # Get selected rows
        selected_rows = self.results_table.selectionModel().selectedRows()
        
        for index in selected_rows:
            row = index.row()
            structure_data = self.results_table.item(row, 0).data(Qt.UserRole)
            if structure_data:
                # Extract structure info for loading
                general = structure_data.get('general', {})
                structure_id = str(structure_data.get('structure_id', general.get('structure_id', '')))
                external_code = general.get('external_code', structure_id)
                label = general.get('title', '')  # Use title as label for search results
                source = general.get('source', '')
                
                selected_structures.append({
                    'structure_id': structure_id,
                    'external_code': external_code,
                    'label': label,
                    'source': source,
                    'matrix': None  # Search results don't have matrices
                })
        
        if not selected_structures:
            QMessageBox.warning(self.tool_window.ui_area, "Warning", "Please select structures to load")
            return
        
        # Start loading in background thread
        self.load_thread = LoadStructuresThread(self.api_client, selected_structures)
        self.load_thread.pdb_content_ready.connect(self.handle_pdb_content_ready)
        self.load_thread.all_completed.connect(self.handle_all_completed)
        self.load_thread.error_occurred.connect(self.handle_load_error)
        self.load_thread.status_update.connect(self.update_status)
        
        self.load_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        self.load_thread.start()
    
    def handle_pdb_content_ready(self, pdb_content, structures):
        """Handle PDB content ready for loading"""
        try:
            from chimerax.core.commands import run
            from Qt.QtCore import QTimer
            
            def load_structures_on_main_thread():
                try:
                    if pdb_content:
                        # Load from PDB content (either with transformations or individual downloads)
                        self.api_client.log_info(f"Loading {len(structures)} structures from PDB content")
                        
                        # Save to temporary file
                        import tempfile
                        import os
                        
                        temp_dir = tempfile.mkdtemp()
                        temp_file = os.path.join(temp_dir, "3decision_structures.pdb")
                        
                        with open(temp_file, 'w') as f:
                            f.write(pdb_content)
                        
                        # Open the multi-MODEL PDB file
                        models = run(self.session, f'open "{temp_file}"')
                        
                        if models:
                            # Rename models based on structure info using get_object_name
                            for i, (model, structure_info) in enumerate(zip(models, structures)):
                                structure_id = structure_info['structure_id']
                                external_code = structure_info['external_code']
                                label = structure_info.get('label')
                                source = structure_info.get('source')
                                
                                # Use smart object naming (same as PyMOL plugin)
                                object_name = get_object_name(external_code, label, source)
                                model.name = object_name
                                
                                # Set metadata attributes
                                model.structure_id = structure_id
                                model.external_code = external_code
                                model.source = "3decision"
                                
                                self.api_client.log_info(f"Loaded {object_name} (external_code: {external_code}) from 3decision")
                        
                        # Clean up temp file
                        try:
                            os.remove(temp_file)
                            os.rmdir(temp_dir)
                        except:
                            pass
                    else:
                        self.api_client.log_error("No PDB content received")
                    
                except Exception as e:
                    self.api_client.log_error(f"Error in load_structures_on_main_thread: {e}")
                    import traceback
                    self.api_client.log_error(traceback.format_exc())
            
            # Execute on main thread
            QTimer.singleShot(0, load_structures_on_main_thread)
            
        except Exception as e:
            self.api_client.log_error(f"Error handling PDB content: {e}")

    def handle_all_completed(self):
        """Handle completion of all structure loading"""
        if QT_AVAILABLE:
            self.load_button.setEnabled(True)
            if hasattr(self, 'load_project_structures_button'):
                self.load_project_structures_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.information(self.tool_window.ui_area, "Success", "Structures loaded successfully!")

    def handle_load_error(self, error_message):
        """Handle structure loading errors"""
        if QT_AVAILABLE:
            self.load_button.setEnabled(True)
            if hasattr(self, 'load_project_structures_button'):
                self.load_project_structures_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self.tool_window.ui_area, "Load Error", error_message)

    def clear_projects_filters(self):
        """Clear all projects filter inputs"""
        # Block signals to prevent triggering apply_projects_filters while clearing
        self.projects_filter_name.blockSignals(True)
        self.projects_filter_structures.blockSignals(True)
        self.projects_filter_owner.blockSignals(True)
        
        self.projects_filter_name.clear()
        self.projects_filter_structures.clear()
        self.projects_filter_owner.clear()
        
        # Unblock signals
        self.projects_filter_name.blockSignals(False)
        self.projects_filter_structures.blockSignals(False)
        self.projects_filter_owner.blockSignals(False)
        
        # Apply empty filters to show all projects
        self.apply_projects_filters()
    
    def apply_projects_filters(self):
        """Apply column filters to the projects table"""
        if not hasattr(self, 'all_projects') or not self.all_projects:
            return
        
        # Get filter values
        filter_name = self.projects_filter_name.text().strip().lower()
        filter_structures = self.projects_filter_structures.text().strip()
        filter_owner = self.projects_filter_owner.text().strip().lower()
        
        # Parse structures filter (supports >, <, >=, <=, =, or range)
        struct_min, struct_max, struct_operator = self.parse_resolution_filter(filter_structures)
        
        # Filter projects
        filtered_projects = []
        for project in self.all_projects:
            # Project name
            project_name = project.get('project_label', '').lower()
            
            # Owner
            owner = project.get('created_by', project.get('updated_by', '')).lower()
            # Clean up email format if present
            if '___' in owner:
                owner = owner.split('___')[0].replace('.', ' ')
            
            # Structures count
            structures_count = project.get('count_structures_in_project', 0)
            
            # Text filters (case-insensitive contains)
            if filter_name and filter_name not in project_name:
                continue
            if filter_owner and filter_owner not in owner:
                continue
            
            # Numeric filter for structures count
            if filter_structures:
                if not self.check_resolution_filter(structures_count, struct_min, struct_max, struct_operator):
                    continue
            
            filtered_projects.append(project)
        
        # Update table with filtered results
        self.populate_projects_table(filtered_projects)
    
    def populate_projects_table(self, projects):
        """Populate the projects table with given projects"""
        # Disable sorting while populating for better performance
        self.projects_table.setSortingEnabled(False)
        
        self.projects_table.setRowCount(len(projects))
        
        for row, project in enumerate(projects):
            # Project Name
            project_name = project.get('project_label', '')
            name_item = QTableWidgetItem(project_name)
            name_item.setData(Qt.UserRole, project)  # Store full project data
            self.projects_table.setItem(row, 0, name_item)
            
            # Structures count - use numeric sorting
            count = project.get('count_structures_in_project', 0)
            count_item = NumericTableWidgetItem(str(count), count)
            self.projects_table.setItem(row, 1, count_item)
            
            # Owner
            owner = project.get('created_by', project.get('updated_by', 'Unknown'))
            # Clean up the email format if present
            if '___' in owner:
                owner = owner.split('___')[0].replace('.', ' ').title()
            self.projects_table.setItem(row, 2, QTableWidgetItem(owner))
        
        self.projects_table.resizeColumnsToContents()
        
        # Re-enable sorting after populating
        self.projects_table.setSortingEnabled(True)

    def load_projects(self):
        """Load projects from 3decision API"""
        try:
            self.update_status("Loading projects...")
            projects = self.api_client.get_projects()
            
            if projects:
                # Filter out the "3decision" project
                filtered_projects = [
                    p for p in projects 
                    if p.get('project_label', '').lower() != '3decision'
                ]
                
                # Store all projects (filtered) for further filtering
                self.all_projects = filtered_projects
                
                # Display filtered projects initially
                self.populate_projects_table(filtered_projects)
                
                self.update_status(f"Loaded {len(filtered_projects)} projects")
                self.projects_loaded = True
            else:
                self.all_projects = []
                self.update_status("No projects found")
                self.projects_table.setRowCount(0)
                self.projects_loaded = True
                
        except Exception as e:
            self.update_status(f"Error loading projects: {str(e)}")
            self.api_client.log_error(f"Error loading projects: {e}")

    def on_project_selection_changed(self):
        """Handle project selection change"""
        selected_items = self.projects_table.selectedItems()
        if selected_items:
            # Get the first column item which contains the project data
            name_item = self.projects_table.item(selected_items[0].row(), 0)
            project_data = name_item.data(Qt.UserRole)
            project_id = project_data.get('project_id')
            if project_id:
                self.fetch_project_structures(project_id)
        else:
            self.project_structures_table.setRowCount(0)
            self.load_project_structures_button.setEnabled(False)

    def clear_project_structures_filters(self):
        """Clear all project structures filter inputs"""
        # Block signals to prevent triggering apply_project_structures_filters while clearing
        self.project_filter_structure_id.blockSignals(True)
        self.project_filter_external_code.blockSignals(True)
        self.project_filter_description.blockSignals(True)
        
        self.project_filter_structure_id.clear()
        self.project_filter_external_code.clear()
        self.project_filter_description.clear()
        
        # Unblock signals
        self.project_filter_structure_id.blockSignals(False)
        self.project_filter_external_code.blockSignals(False)
        self.project_filter_description.blockSignals(False)
        
        # Apply empty filters to show all structures
        self.apply_project_structures_filters()
    
    def apply_project_structures_filters(self):
        """Apply column filters to the project structures table"""
        if not hasattr(self, 'all_project_structures') or not self.all_project_structures:
            return
        
        # Get filter values
        filter_structure_id = self.project_filter_structure_id.text().strip().lower()
        filter_ext_code = self.project_filter_external_code.text().strip().lower()
        filter_desc = self.project_filter_description.text().strip().lower()
        
        # Filter structures
        filtered_structures = []
        for structure in self.all_project_structures:
            # Structure ID
            structure_id = str(structure.get('STRUCTURE_ID', structure.get('structure_id', ''))).lower()
            
            # External Code
            external_code = structure.get('EXTERNAL_CODE', structure.get('external_code', structure_id)).lower()
            
            # Description
            description = structure.get('PROJECT_LABEL', structure.get('description', '')).lower()
            
            # Text filters (case-insensitive contains)
            if filter_structure_id and filter_structure_id not in structure_id:
                continue
            if filter_ext_code and filter_ext_code not in external_code:
                continue
            if filter_desc and filter_desc not in description:
                continue
            
            filtered_structures.append(structure)
        
        # Update table with filtered results
        self.populate_project_structures_table(filtered_structures)
    
    def populate_project_structures_table(self, structures):
        """Populate the project structures table with given structures"""
        # Disable sorting while populating for better performance
        self.project_structures_table.setSortingEnabled(False)
        
        self.project_structures_table.setRowCount(len(structures))
        
        for row, structure in enumerate(structures):
            # Structure details
            structure_id = str(structure.get('STRUCTURE_ID', structure.get('structure_id', '')))
            external_code = structure.get('EXTERNAL_CODE', structure.get('external_code', structure_id))
            description = structure.get('PROJECT_LABEL', structure.get('description', ''))
            
            id_item = QTableWidgetItem(structure_id)
            id_item.setData(Qt.UserRole, structure)  # Store full structure data
            self.project_structures_table.setItem(row, 0, id_item)
            
            self.project_structures_table.setItem(row, 1, QTableWidgetItem(external_code))
            self.project_structures_table.setItem(row, 2, QTableWidgetItem(description))
            
            # View Files button
            view_files_btn = QPushButton("View Files")
            view_files_btn.clicked.connect(lambda checked, s=structure: self.view_structure_files(s))
            self.project_structures_table.setCellWidget(row, 3, view_files_btn)
        
        self.project_structures_table.resizeColumnsToContents()
        
        # Re-enable sorting after populating
        self.project_structures_table.setSortingEnabled(True)
        
        self.load_project_structures_button.setEnabled(len(structures) > 0)

    def fetch_project_structures(self, project_id):
        """Fetch structures for the selected project from API"""
        try:
            self.update_status(f"Loading structures for project {project_id}...")
            structures = self.api_client.get_project_structures(str(project_id))
            
            if structures:
                # Store all structures for filtering
                self.all_project_structures = structures
                
                # Display all structures initially
                self.populate_project_structures_table(structures)
                
                self.update_status(f"Loaded {len(structures)} structures from project")
            else:
                self.all_project_structures = []
                self.project_structures_table.setRowCount(0)
                self.load_project_structures_button.setEnabled(False)
                self.update_status("No structures found in selected project")
                
        except Exception as e:
            self.update_status(f"Error loading project structures: {str(e)}")
            self.api_client.log_error(f"Error loading project structures: {e}")

    def select_all_project_structures(self):
        """Select all project structures"""
        self.project_structures_table.selectAll()

    def select_none_project_structures(self):
        """Deselect all project structures"""
        self.project_structures_table.clearSelection()

    def load_selected_project_structures(self):
        """Load selected structures from the project with transformation matrices"""
        selected_structures = []
        
        # Get selected rows
        selected_rows = self.project_structures_table.selectionModel().selectedRows()
        
        for index in selected_rows:
            row = index.row()
            id_item = self.project_structures_table.item(row, 0)
            structure_data = id_item.data(Qt.UserRole)
            
            # Extract structure info
            structure_id = str(structure_data.get('STRUCTURE_ID', structure_data.get('structure_id', '')))
            external_code = structure_data.get('EXTERNAL_CODE', structure_data.get('external_code', structure_id))
            # Note: PROJECT_LABEL is the project name, not the structure label
            # For project structures, we use external_code as the primary name
            # Only use a label if there's a structure-specific one (not the project name)
            label = structure_data.get('STRUCTURE_LABEL', structure_data.get('label', ''))
            source = structure_data.get('SOURCE', structure_data.get('source', ''))
            
            # Get transformation matrix from stored data
            # Check for matrix in TRANSFORM_MATRIX (enriched data) or ReferenceTransforms.transform
            matrix = structure_data.get('TRANSFORM_MATRIX')
            if not matrix:
                ref_transforms = structure_data.get('ReferenceTransforms')
                if ref_transforms and isinstance(ref_transforms, dict):
                    transform = ref_transforms.get('transform')
                    if transform and isinstance(transform, list) and len(transform) == 16:
                        # Convert flat 16-value array to 4x4 nested array
                        matrix = [
                            transform[0:4],
                            transform[4:8],
                            transform[8:12],
                            transform[12:16]
                        ]
            
            selected_structures.append({
                'structure_id': structure_id,
                'external_code': external_code,
                'label': label,
                'source': source,
                'matrix': matrix  # May be None if no transformation
            })
            
            self.api_client.log_info(f"Preparing to load {external_code} (ID: {structure_id}, has_matrix: {matrix is not None})")
        
        if not selected_structures:
            QMessageBox.warning(self.tool_window.ui_area, "Warning", "Please select structures to load")
            return
        
        # Use the same loading mechanism as search results
        self.load_thread = LoadStructuresThread(self.api_client, selected_structures)
        self.load_thread.pdb_content_ready.connect(self.handle_pdb_content_ready)
        self.load_thread.all_completed.connect(self.handle_all_completed)
        self.load_thread.error_occurred.connect(self.handle_load_error)
        self.load_thread.status_update.connect(self.update_status)
        
        self.load_project_structures_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        self.load_thread.start()

    def perform_search(self, query):
        """Perform search from command line"""
        if hasattr(self, 'search_input'):
            self.search_input.setText(query)
            self.submit_search()
        else:
            self.session.logger.info(f"Performing search for: {query}")
            # TODO: Implement command-line search

    def delete(self):
        """Cleanup when tool is closed"""
        # Clean up any running threads
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            self.search_thread.wait()
        
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.terminate()
            self.load_thread.wait()
        
        super().delete()
