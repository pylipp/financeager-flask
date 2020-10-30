# financeager-flask

## Installation

    pip install financeager-flask

## Development

### Set up

    python3 -m venv .venv
    source .venv/bin/activate
    make install

### Testing

    python -m unittest discover

## Releasing

1. Tag the latest commit on master by incrementing the current version accordingly (scheme `v0.major.minor.patch`).
1. Run `make release`.
