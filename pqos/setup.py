from setuptools import setup

setup(
    name="pqos-wrapper",
    version="0.0.1",
    packages=["pqos_wrapper"],
    entry_points={
        "console_scripts": ["pqos_wrapper = pqos_wrapper.main:PqosWrapper.main"]
    },
)
