from setuptools import setup, find_packages

setup(
    name="story_engine",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["pydantic>=2.0", "shared_types", "originality_engine"],
)
