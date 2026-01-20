# ChimeraX command definitions

from chimerax.core.commands import CmdDesc, RestOfLine


def threedecision_cmd(session, action="", query=""):
    """Execute the threedecision command"""
    from .gui import ThreeDecisionTool
    
    # Start the tool
    from chimerax.core import tools
    tool = tools.get_singleton(session, ThreeDecisionTool, "3decision")
    
    # If search action is specified, perform search
    if action == "search" and query:
        tool.perform_search(query)
    
    # Display the tool
    tool.display(True)


# Command description
threedecision_desc = CmdDesc(
    optional=[
        ("action", RestOfLine),
        ("query", RestOfLine)
    ],
    synopsis="Open 3decision tool interface"
)
