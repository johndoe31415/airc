import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name = "airc",
	packages = setuptools.find_packages(),
	version = "0.0.1",
	license = "gpl-3.0",
	description = "Python-based asynchronous IRC client library that supports DCC transfers and anonymization",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	author = "Johannes Bauer",
	author_email = "joe@johannes-bauer.com",
	url = "https://github.com/johndoe31415/airc",
	download_url = "https://github.com/johndoe31415/airc/archive/v0.0.1.tar.gz",
	keywords = [ "asyncio", "irc", "client", "dcc" ],
	include_package_data = True,
	install_requires = [
		"aiohttp",
	],
	classifiers = [
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.10",
	],
)
