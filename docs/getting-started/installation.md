GTFS4EV comes as a Python package. If this is your first time using Python, we recommend using **pip** or **conda** as package
managers. Both are available on Windows, macOS, and GNU/Linux systems.

GTFS4EV has been tested with **Python 3.12 and 3.13**. While newer Python versions may work,
they are not officially tested yet.

Also, we recommend installing GTFS4EV inside a **dedicated virtual environment**.
For guidance, see:
- [Using pip and venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
- [Using conda](https://docs.conda.io/projects/conda/en/stable/user-guide/getting-started.html)

---

## From PyPI
GTFS4EV is available as a PyPI package. Activate your virtual environment (if any) and install the latest stable version with:

```bash
pip install gtfs4ev
```

## From source
For developers (testing, etc), the model can be installed with:

```bash
git clone https://github.com/gtfs4ev/gtfs4ev.git
cd gtfs4ev
pip install -e .
```

> The source code can be forked or cloned depending on the intended usage. If you clone the repository directly, 
  make sure to create and work on your own branch instead of working the `main` branch.

    
## Checking proper installation

Run any of the provided examples. See [Quickstart](quickstart.md) section for minimal working case, and other examples in [Examples](examples.md). 
If the installation is successful, each example should run without errors and produce output result files.

For developers or advanced users, GTFS4EV also provides an automated test suite. When installing from source, the tests can be executed using `pytest`. All tests should pass. 

```bash
pip install pytest
pytest
```