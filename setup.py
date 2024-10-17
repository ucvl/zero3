from setuptools import setup, find_packages

setup(
    name="ucvl.zero3",
    version="0.1.0",
    author="你的名字",
    author_email="123003020@qq.com",
    description="ucvl",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ucvl/zero3",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
