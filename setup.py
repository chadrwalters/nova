from setuptools import setup, find_packages

setup(
    name="nova",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "markitdown>=1.0.0",
        "structlog>=23.1.0",
        "pydantic>=2.0.0",
        "typer>=0.9.0",
        "python-magic>=0.4.27",
        "psutil>=5.9.8",
        "pyyaml>=6.0.1",
        "aiofiles>=23.2.1",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.9",
) 