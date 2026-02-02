# Settings dialog for 3decision plugin

try:
    from Qt.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
        QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox, QComboBox,
        QSizePolicy
    )
    from Qt.QtCore import Qt, QThread
    
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
    
except ImportError:
    # Fallback imports
    try:
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
            QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox, QComboBox,
            QSizePolicy
        )
        from PyQt5.QtCore import Qt, QThread, pyqtSignal
    except ImportError:
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
            QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox, QComboBox,
            QSizePolicy
        )
        from PyQt6.QtCore import Qt, QThread, pyqtSignal

class ConnectionTestThread(QThread):
    """Thread for testing API connection"""
    test_completed = pyqtSignal(bool, str)
    
    def __init__(self, api_client, base_url, api_key):
        super().__init__()
        self.api_client = api_client
        self.base_url = base_url
        self.api_key = api_key
        
    def run(self):
        try:
            # Configure API client with new settings
            self.api_client.configure(self.base_url, self.api_key)
            
            # Test connection
            if self.api_client.test_connection():
                self.test_completed.emit(True, "Connection successful!")
            else:
                self.test_completed.emit(False, "Connection failed - check credentials")
                
        except Exception as e:
            self.test_completed.emit(False, f"Connection error: {str(e)}")

class SettingsDialog(QDialog):
    """Settings dialog for 3decision credentials"""
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.test_thread = None
        self.setWindowTitle("3decision API Settings")
        self.setModal(True)
        self.setMinimumSize(450, 300)
        
        # Remove the question mark from title bar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.init_ui()
        self.load_current_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("3decision API Configuration")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0066cc; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Settings group
        settings_group = QGroupBox("API Settings")
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Server URL
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("https://your-3decision-server.com")
        self.server_url_edit.setMinimumWidth(300)
        self.server_url_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addRow("Server URL:", self.server_url_edit)
        
        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Your API key")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setMinimumWidth(300)
        self.api_key_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addRow("API Key:", self.api_key_edit)
        
        # Show API key checkbox
        self.show_key_checkbox = QCheckBox("Show API key")
        self.show_key_checkbox.toggled.connect(self.toggle_key_visibility)
        form_layout.addRow("", self.show_key_checkbox)
        
        # Private structure naming attribute dropdown
        self.naming_attribute_combo = QComboBox()
        self.naming_attribute_combo.addItems(["label", "title", "external_code", "internal_id"])
        self.naming_attribute_combo.setToolTip(
            "Choose which attribute to use for naming private structures when loaded into ChimeraX.\n"
            "Public structures (PDB, AlphaFold, etc.) always use external_code."
        )
        self.naming_attribute_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addRow("Private structure name:", self.naming_attribute_combo)
        
        settings_group.setLayout(form_layout)
        main_layout.addWidget(settings_group)
        
        # Test connection button
        test_layout = QHBoxLayout()
        test_layout.addStretch()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)
        
        main_layout.addLayout(test_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def load_current_settings(self):
        """Load current API settings"""
        if self.api_client.base_url:
            self.server_url_edit.setText(self.api_client.base_url)
        if self.api_client.api_key:
            self.api_key_edit.setText(self.api_client.api_key)
        
        # Load private structure naming attribute setting
        from .api_client import get_private_structure_naming_attribute
        naming_attr = get_private_structure_naming_attribute()
        index = self.naming_attribute_combo.findText(naming_attr)
        if index >= 0:
            self.naming_attribute_combo.setCurrentIndex(index)
            
        # Show connection status
        if self.api_client.is_authenticated():
            self.status_label.setText("✅ Currently connected to 3decision API")
            self.status_label.setStyleSheet("color: green;")
        elif self.api_client.is_configured():
            self.status_label.setText("⚠️ Configured but not connected")
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setText("❌ Not configured")
            self.status_label.setStyleSheet("color: red;")
            
    def toggle_key_visibility(self, show):
        """Toggle API key visibility"""
        if show:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            
    def test_connection(self):
        """Test the API connection"""
        base_url = self.server_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        
        if not base_url or not api_key:
            QMessageBox.warning(self, "Warning", "Please enter both server URL and API key")
            return
            
        # Start connection test in background
        self.test_button.setEnabled(False)
        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("color: blue;")
        
        self.test_thread = ConnectionTestThread(self.api_client, base_url, api_key)
        self.test_thread.test_completed.connect(self.on_test_completed)
        self.test_thread.start()
        
    def on_test_completed(self, success, message):
        """Handle connection test completion"""
        self.test_button.setEnabled(True)
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: red;")
    
    def save_settings(self):
        """Save the settings"""
        base_url = self.server_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        
        if not base_url or not api_key:
            QMessageBox.warning(self, "Warning", "Please enter both server URL and API key")
            return
            
        try:
            # Configure and save
            self.api_client.configure(base_url, api_key)
            
            # Save private structure naming attribute setting
            from .api_client import set_private_structure_naming_attribute
            naming_attr = self.naming_attribute_combo.currentText()
            set_private_structure_naming_attribute(naming_attr)
            
            self.api_client.save_config()
            
            # Test the configuration
            if self.api_client.test_connection():
                QMessageBox.information(self, "Success", "Settings saved and connection verified!")
                self.accept()
            else:
                reply = QMessageBox.question(
                    self, 
                    "Save Settings", 
                    "Settings saved but connection test failed. Keep settings anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.accept()
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Clean up test thread
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.terminate()
            self.test_thread.wait()
        event.accept()
