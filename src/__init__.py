"""
ChimeraX bundle for Discngine 3decision services.

This bundle provides access to 3decision molecular structure search,
project management, and associated file handling capabilities.
"""

from chimerax.core.toolshed import BundleAPI

class ThreeDecisionBundleAPI(BundleAPI):
    """Bundle API for the Discngine 3decision ChimeraX plugin."""
    
    api_version = 1

    @staticmethod
    def start_tool(session, bundle_info, tool_info):
        """Start a tool instance."""
        tool_name = tool_info.name
        # Handle both possible tool names
        if tool_name in ("Discngine 3decision", "ChimeraX-threedecision"):
            from .gui import ThreeDecisionTool
            return ThreeDecisionTool(session, "Discngine 3decision")
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    @staticmethod
    def register_command(bundle_info, command_info, logger):
        """Register commands with ChimeraX."""
        command_name = command_info.name
        if command_name == "threedecision":
            from .commands import threedecision_desc, threedecision_cmd
            return (threedecision_desc, threedecision_cmd)
        else:
            raise ValueError(f"Unknown command: {command_name}")

# Required bundle API instance
bundle_api = ThreeDecisionBundleAPI()
