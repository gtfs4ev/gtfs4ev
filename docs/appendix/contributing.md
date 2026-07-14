# Contributing

Thank you for your interest in contributing to this project!

We welcome contributions of all kinds to this library, including non-code contributions.

## Ways to contribute

Possible ways to contribute include:
- Reporting bugs or suggesting features via GitHub Issues
- Opening pull requests with improvements or fixes
- Writing new examples or tutorials
- Improving or expanding test coverage
- Enhancing documentation, comments, or overall code readability

If you are unsure where to start, feel free to open an issue to discuss your ideas.

## Code and documentation contributions

Code contributions follow the standard GitHub fork-and-pull-request workflow.

1. Fork the repository to your own GitHub account.
2. Create a new branch from `main` in your fork.
3. Make your changes and commit them to your branch.
4. Open a pull request to the `main` branch of this repository, describing what you changed and why.

Once a pull request is opened:
- The maintainers will review the proposed changes.
- Feedback or requested modifications may be discussed directly in the pull request.
- The pull request may be updated by pushing additional commits to the same branch.
- When the changes are ready, a maintainer will merge the pull request into the `main` branch.

Please note that changes are only incorporated into the codebase after being reviewed and merged by a maintainer. Small, focused contributions are preferred.

## Code style

Please follow the existing style and structure in the codebase.

## Continuous Integration (CI)

This repository uses GitHub Actions to automatically run CI on every push to `main` and every pull request.

CI on every pull request:
- Runs on Ubuntu, Windows, and macOS (Python 3.12)
- Installs the package and executes the test suite with `pytest`

If changes affect the `docs/` folder or `setup.py` (i.e. in case of version change prior to release on PyPI), documentation will be rebuilt automatically and deployed to GitHub Pages using `mkdocs gh-deploy` when pushing to the `main` branch.

## PyPI release

PyPI releases are **not automated** and must be coordinated with the main developer. 
Note that only code changes (not documentation-only updates) are eligible for release.

Main steps of the release process (main developper only):

1. **Update version**: Bump the version in `setup.py` (or equivalent)

2. **Create a GitHub release**: After merging into `main`, create a GitHub release with a tag matching the version (e.g. `vX.Y.Z`). This can be done using the GitHub web interface directly.

3. **Build locally and upload with Twine**
   ```bash   
   python -m build
   twine upload dist/*
   ```
