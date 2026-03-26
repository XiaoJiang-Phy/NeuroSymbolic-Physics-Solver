import matplotlib.pyplot as plt
import numpy as np
import os

class PlotEngine:
    """
    Phase 4.3: Publication-Quality Scientific Plotting Engine
    Adheres to the APS/Nature standard (sci_plot skill).
    """
    def __init__(self):
        self.set_aps_style()

    def set_aps_style(self):
        """Sets the matplotlib rcParams to APS publication standards."""
        # Note: text.usetex requires a local LaTeX distribution. 
        # For robustness, we try to use it, but provide a fallback if it fails later.
        plt.rcParams.update({
            "font.family": "serif",
            "figure.figsize": (3.4, 2.8), # Single column APS
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "axes.linewidth": 1.0,
            "lines.linewidth": 1.5,
        })
        try:
            # We explicitly test if we can render a simple string with usetex
            # If not, we fall back to mathtext (internal rendering)
            import matplotlib as mpl
            old_tex = mpl.rcParams['text.usetex']
            mpl.rcParams['text.usetex'] = True
            fig = plt.figure(figsize=(1,1))
            fig.text(0.5, 0.5, r"$x$")
            plt.close(fig)
            plt.rcParams["text.usetex"] = True
            plt.rcParams["font.serif"] = ["Computer Modern Roman"]
        except Exception:
            plt.rcParams["text.usetex"] = False
            plt.rcParams["mathtext.fontset"] = "cm" # Fallback to Computer Modern mathtext

    def plot_2d_heatmap(self, X: np.ndarray, Y: np.ndarray, Z: np.ndarray, 
                       xlabel: str, ylabel: str, 
                       title: str = "", output_path: str = "heatmap.pdf", 
                       cmap: str = "magma", zlabel: str = ""):
        """
        Plots a publication-quality 2D heatmap (e.g., Berry curvature or DOS in k-space).
        """
        fig, ax = plt.subplots(figsize=(3.4, 2.8))
        
        # Use pcolormesh or contourf
        c = ax.contourf(X, Y, Z, levels=100, cmap=cmap)
        
        # Add colorbar
        cbar = fig.colorbar(c, ax=ax, pad=0.02)
        if zlabel:
            cbar.set_label(zlabel)
            
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title)
            
        fig.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_band_structure(self, k_path: np.ndarray, bands: list, 
                          high_sym_points: list, high_sym_labels: list,
                          ylabel: str = r"$E - E_F$ (eV)", 
                          output_path: str = "bands.pdf"):
        """
        Plots a 1D band structure along high-symmetry paths.
        bands: List of 1D numpy arrays representing energy eigenvalues.
        """
        fig, ax = plt.subplots(figsize=(3.4, 2.8))
        
        for band in bands:
            ax.plot(k_path, band, color='blue', lw=1.2)
            
        # Draw vertical lines for high-symmetry points
        for p in high_sym_points:
            ax.axvline(x=p, color='k', lw=0.5, linestyle='--')
            
        # Fermi level
        ax.axhline(y=0, color='r', lw=0.8, linestyle=':')
        
        ax.set_xticks(high_sym_points)
        ax.set_xticklabels(high_sym_labels)
        ax.set_xlim(k_path[0], k_path[-1])
        ax.set_ylabel(ylabel)
        
        fig.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_1d_curves(self, x: np.ndarray, y_list: list, labels: list,
                       xlabel: str, ylabel: str, title: str = "",
                       output_path: str = "plot.pdf"):
        """Plots multiple 1D curves."""
        fig, ax = plt.subplots(figsize=(3.4, 2.8))
        for y, label in zip(y_list, labels):
            ax.plot(x, y, lw=1.5, label=label)
        
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title)
        ax.legend()
        fig.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return output_path

def get_plot_engine() -> PlotEngine:
    return PlotEngine()
