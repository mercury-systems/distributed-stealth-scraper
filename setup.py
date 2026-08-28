from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="distributed-stealth-scraper",
    version="2.0.0",
    author="MERCURY-OPS",
    description="Dual-mode stealth scraper with automatic WAF challenge escalation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mercury-systems/distributed-stealth-scraper",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    keywords="scraping web-scraping cloudflare bypass waf stealth playwright curl-cffi",
    python_requires=">=3.10",
    install_requires=["curl-cffi>=0.6.0"],
    extras_require={
        "heavy": ["playwright>=1.40.0", "greenlet>=3.1.0"],
        "dev": ["pytest>=7.0", "pytest-asyncio>=0.21"],
    },
    entry_points={
        "console_scripts": ["stealth-scraper=stealth_scraper.cli:main"],
    },
)
