from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="site-crawler-mcp",
    version="0.1.0",
    author="Andac Guven",
    author_email="andac.guven@example.com",
    description="MCP server for crawling websites and extracting assets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AndacGuven/site-crawler-mcp",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.9.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "mcp>=0.9.0",
        "python-dotenv>=1.0.0",
        "validators>=0.22.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "site-crawler-mcp=site_crawler.server:main",
        ],
    },
)