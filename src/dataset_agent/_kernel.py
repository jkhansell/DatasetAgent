"""Installation of the IPython kernel for Jupyter notebooks."""

import sys
from ipykernel.kernelspec import install


def install_kernel() -> None:
    """Install the Jupyter kernel pointing to this virtual environment.

    The kernel is installed to ``~/.local/share/jupyter/kernels/dataset_agent``
    so notebooks can use the project's dependencies directly.
    """
    print("Installing Jupyter kernel to ~/.local/share/jupyter/kernels/dataset_agent ...")
    install(
        user=True,
        kernel_name="dataset_agent",
        display_name="Python (dataset_agent)",
    )
    print("Kernel installed successfully.")


if __name__ == "__main__":
    install_kernel()
