from setuptools import setup

setup(
    name="topology-engine",
    version="3.0.0",
    py_modules=["find_workflow_loops"],
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
        "networkx",
        "matplotlib"
    ],
    entry_points={
        "console_scripts": [
            "topology-engine=find_workflow_loops:app", # Points directly to your typer app instance
        ],
    },
)
