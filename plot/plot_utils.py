import matplotlib.pyplot as plt
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def maximize_figure_window():
    """
    Maximize the current figure window to take all available screen space without going full screen.
    This preserves window decorations and taskbar visibility.
    """
    try:
        # Get the figure manager
        fig_manager = plt.get_current_fig_manager()

        # Try different approaches based on backend, prioritizing maximize over full screen
        if hasattr(fig_manager, 'window') and hasattr(fig_manager.window, 'showMaximized'):
            # Qt backend (most common)
            fig_manager.window.showMaximized()
        elif hasattr(fig_manager, 'window') and hasattr(fig_manager.window, 'state') and hasattr(fig_manager.window, 'tk'):
            # TkAgg backend
            fig_manager.window.state('zoomed')  # Windows 'zoomed' state
        elif hasattr(fig_manager, 'frame') and hasattr(fig_manager.frame, 'Maximize'):
            # WX backend
            fig_manager.frame.Maximize(True)
        elif hasattr(fig_manager, 'window') and hasattr(fig_manager.window, 'maximize'):
            # Other backends with maximize function
            fig_manager.window.maximize()
        elif hasattr(fig_manager, 'full_screen_toggle'):
            # Only use full screen as a last resort
            logger.debug("Using full_screen_toggle as fallback")
            fig_manager.full_screen_toggle()
        elif hasattr(fig_manager, 'resize'):
            # MacOSX backend
            fig_manager.resize(*fig_manager.window.get_screen().get_size())
    except Exception as e:
        logger.debug(f"Could not maximize window: {str(e)}")