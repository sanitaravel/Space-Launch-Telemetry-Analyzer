"""Global watermarking utilities for plots.

This module patches matplotlib's Figure methods and Plotly's Figure methods
so that any saved or shown figure will have a small, semi-transparent
watermark added automatically.

The watermark text is hard-coded to '@sanitaravel' per repository owner request.
The module is safe to import in environments without matplotlib/plotly.
"""
from typing import Optional

try:
    from utils.logger import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)

# Watermark configuration
WATERMARK_TEXT = "@sanitaravel"
WATERMARK_OPACITY = 0.35
WATERMARK_FONTSIZE = 14
WATERMARK_COLOR = "black"


def _figure_has_watermark(fig, text: str = WATERMARK_TEXT) -> bool:
    try:
        for t in getattr(fig, "texts", []):
            try:
                if hasattr(t, "get_text") and t.get_text() == text:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def apply_watermark_matplotlib(fig, text: str = WATERMARK_TEXT, opacity: float = WATERMARK_OPACITY,
                               fontsize: int = WATERMARK_FONTSIZE, color: str = WATERMARK_COLOR) -> None:
    """Add a watermark to a matplotlib Figure object if not already present.

    This operates directly on the Figure and avoids importing pyplot so
    it is safe for headless/test environments.
    """
    if fig is None:
        return

    try:
        if _figure_has_watermark(fig, text):
            return

        # Add watermark in figure (paper) coordinates - bottom-right
        fig.text(0.99, 0.01, text, ha="right", va="bottom", fontsize=fontsize,
                 color=color, alpha=opacity, zorder=1000)
    except Exception:
        try:
            # Fallback: try to add to first axis in axes coordinates
            if getattr(fig, "axes", None):
                ax = fig.axes[0]
                ax.text(0.99, 0.01, text, transform=ax.transAxes, ha="right", va="bottom",
                        fontsize=fontsize, color=color, alpha=opacity)
        except Exception:
            logger.debug("Failed to apply matplotlib watermark", exc_info=True)


# Patch matplotlib Figure methods at import-time (if matplotlib is present)
try:
    import matplotlib
    from matplotlib.figure import Figure

    _orig_figure_savefig = Figure.savefig
    _orig_figure_show = Figure.show

    def _savefig_wrapper(self, *args, **kwargs):
        try:
            apply_watermark_matplotlib(self)
        except Exception:
            logger.debug("Watermark apply failed in savefig", exc_info=True)
        return _orig_figure_savefig(self, *args, **kwargs)

    def _show_wrapper(self, *args, **kwargs):
        try:
            apply_watermark_matplotlib(self)
        except Exception:
            logger.debug("Watermark apply failed in show", exc_info=True)
        return _orig_figure_show(self, *args, **kwargs)

    Figure.savefig = _savefig_wrapper
    Figure.show = _show_wrapper
    logger.debug("Patched matplotlib.figure.Figure.savefig/show for watermarking")
except Exception:
    logger.debug("matplotlib not available or patch failed", exc_info=True)

# If pyplot is already imported in the process, wrap its `show` to ensure
# watermarks are applied when code calls `plt.show()`.
try:
    import sys
    if "matplotlib.pyplot" in sys.modules:
        try:
            plt = sys.modules.get("matplotlib.pyplot")
            _orig_plt_show = getattr(plt, "show", None)

            if _orig_plt_show is not None:
                def _plt_show_wrapper(*args, **kwargs):
                    try:
                        # Try to apply watermark to all managed figures
                        try:
                            from matplotlib._pylab_helpers import Gcf
                            for m in Gcf.get_all_fig_managers():
                                fig_obj = getattr(m.canvas, "figure", None)
                                if fig_obj:
                                    apply_watermark_matplotlib(fig_obj)
                        except Exception:
                            # Fallback: apply to current figure
                            try:
                                import matplotlib.pyplot as _plt
                                apply_watermark_matplotlib(_plt.gcf())
                            except Exception:
                                pass
                    except Exception:
                        logger.debug("Failed while applying watermark before plt.show()", exc_info=True)
                    return _orig_plt_show(*args, **kwargs)

                plt.show = _plt_show_wrapper
                logger.debug("Patched matplotlib.pyplot.show for watermarking")
        except Exception:
            logger.debug("Failed to patch matplotlib.pyplot.show", exc_info=True)
except Exception:
    # Protect against sys import errors in constrained environments
    pass


# Patch Plotly Figure methods (if plotly is available)
try:
    import plotly.graph_objects as go

    _orig_plotly_show = go.Figure.show
    _orig_plotly_write_image = getattr(go.Figure, "write_image", None)
    _orig_plotly_write_html = getattr(go.Figure, "write_html", None)

    def _has_plotly_watermark(fig, text: str = WATERMARK_TEXT) -> bool:
        try:
            ann = getattr(fig.layout, "annotations", None)
            if not ann:
                return False
            for a in list(ann):
                try:
                    if a.get("text", None) == text or getattr(a, "text", None) == text:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _ensure_plotly_watermark(fig, text: str = WATERMARK_TEXT, opacity: float = 0.25,
                                 fontsize: int = 12, color: str = "rgba(0,0,0,0.35)"):
        try:
            if _has_plotly_watermark(fig, text):
                return

            ann = dict(
                text=text,
                x=1,
                y=0,
                xref="paper",
                yref="paper",
                xanchor="right",
                yanchor="bottom",
                showarrow=False,
                opacity=opacity,
                font=dict(size=fontsize, color=color),
            )

            # Append to existing annotations if present
            existing = getattr(fig.layout, "annotations", None)
            if existing:
                fig.update_layout(annotations=list(existing) + [ann])
            else:
                fig.update_layout(annotations=[ann])
        except Exception:
            logger.debug("Failed to ensure plotly watermark", exc_info=True)

    def _plotly_show_wrapper(self, *args, **kwargs):
        try:
            _ensure_plotly_watermark(self)
        except Exception:
            logger.debug("Plotly watermark failed on show", exc_info=True)
        return _orig_plotly_show(self, *args, **kwargs)

    go.Figure.show = _plotly_show_wrapper

    if _orig_plotly_write_image is not None:
        def _plotly_write_image_wrapper(self, *args, **kwargs):
            try:
                _ensure_plotly_watermark(self)
            except Exception:
                logger.debug("Plotly watermark failed on write_image", exc_info=True)
            return _orig_plotly_write_image(self, *args, **kwargs)

        go.Figure.write_image = _plotly_write_image_wrapper

    if _orig_plotly_write_html is not None:
        def _plotly_write_html_wrapper(self, *args, **kwargs):
            try:
                _ensure_plotly_watermark(self)
            except Exception:
                logger.debug("Plotly watermark failed on write_html", exc_info=True)
            return _orig_plotly_write_html(self, *args, **kwargs)

        go.Figure.write_html = _plotly_write_html_wrapper

    logger.debug("Patched plotly.Figure methods for watermarking")
except Exception:
    logger.debug("plotly not available or patch failed", exc_info=True)


__all__ = [
    "apply_watermark_matplotlib",
]
