from setuptools import setup, find_packages

setup(
    name="KameleonS",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A brief description of KameleonS",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Lukifuki1/KameleonS",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        # Add your project dependencies here
    ],
)