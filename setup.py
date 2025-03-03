from setuptools import setup, find_packages

setup(
    name="nova",
    packages=find_packages(include=["nova", "nova.*"]),
)
