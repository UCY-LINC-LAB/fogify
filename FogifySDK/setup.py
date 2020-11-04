import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="FogifySDK",
    version="0.0.1",
    author="Moysis Symeonides",
    author_email="symeonidis.moysis@cs.ucy.ac.cy",
    description="The fogify's SDK library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(where="src"),
    package_dir={'': 'src'},  # Optional
    python_requires='>=3.5',
)