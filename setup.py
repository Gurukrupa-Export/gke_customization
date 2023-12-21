from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in gke_customization/__init__.py
from gke_customization import __version__ as version

setup(
	name="gke_customization",
	version=version,
	description="App made for gurukrupa\'s internal development team",
	author="Gurukrupa Export",
	author_email="vishal@gurukrupaexport.in",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
