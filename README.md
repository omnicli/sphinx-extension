# OmniCLI Sphinx Plugin

A Sphinx extension for automatically documenting omni commands by extracting their help information.

This uses the `--output json` flag of the help command which was introduced in `omni` `0.0.29`.

## Installation

```bash
pip install omnicli-sphinx
```

## Usage

1. Add 'omnicli_sphinx' to your extensions in conf.py:

```python
extensions = [
    'omnicli_sphinx',
    # ... other extensions
]
```

2. Use the directive in your RST files:

```rst
.. omnicli:: command
```

## Development

Use `omni clone omnicli/sphinx-extension` to clone this repository.
You can also clone it with `git clone` and then use `omni up` to install dependencies.

Use `omni test` to run the tests.

## License

MIT License
