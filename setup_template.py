import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name = "airc",
	packages = setuptools.find_packages(),
	version = "${PACKAGE_VERSION}",
	license = "gpl-3.0",
	description = "Python-based asynchronous IRC client library that supports DCC transfers and anonymization",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	author = "Johannes Bauer",
	author_email = "joe@johannes-bauer.com",
	url = "https://github.com/johndoe31415/airc",
	download_url = "https://github.com/johndoe31415/airc/archive/v${PACKAGE_VERSION}.tar.gz",
	keywords = [ "asyncio", "irc", "client", "dcc" ],
	include_package_data = True,
	classifiers = [
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.10",
	],
)
