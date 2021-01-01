![Build Status](https://github.com/pylipp/financeager-flask/workflows/CI/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/pylipp/financeager-flask/badge.svg?branch=master)](https://coveralls.io/github/pylipp/financeager-flask?branch=master)

# financeager-flask

Plugin that enables you to run [financeager](https://github.com/pylipp/financeager) as a Flask-powered webservice!

## Installation

    pip install financeager-flask

For Python>=3.6, installation via [`pipx`](https://pipxproject.github.io/pipx/)  is recommended:

    pipx install financeager
    pipx inject financeager financeager-flask

## Usage

To run `financeager` as client-server application, start the flask webservice by

    export FLASK_APP=financeager_flask.fflask
    flask run  # --help for more info

>   This does not store data persistently! Specify the environment variable `FINANCEAGER_FLASK_DATA_DIR`.

>   For production use, you should wrap `app = fflask.create_app(data_dir=...)` in a WSGI or FCGI (see `examples/` directory).

To communicate with the webservice, the `financeager` configuration has to be adjusted. Create and open the file `~/.config/financeager/config`. If you're on the machine that runs the webservice, put the lines

    [SERVICE]
    name = flask

If you're on an actual remote 'client' machine, put

    [SERVICE]
    name = flask

    [SERVICE:FLASK]
    host = https://foo.pythonanywhere.com
    timeout = 10
    username = foouser
    password = S3cr3t

This specifies the timeout for HTTP requests and username/password for basic auth, if required by the server.

In any case, you're all set up! The available client CLI commands and options are the same as for the native program.

### More Goodies

- `financeager` will store requests if the server is not reachable (the timeout is configurable). The offline backup is restored the next time a connection is established.

## Architecture

The following diagram sketches the relationship between financeager's modules, and this plugin. See the module docstrings for more information.

          +--------+
          | plugin |
          +--------+
           ¦      ¦
           V      V
    +--------+   +-----------+   +---------+
    | config |-->|    cli    |<->| offline |
    +--------+   +-----------+   +---------+

                     ¦   Λ                     +---------+     +---------+
    [pre-processing] ¦   ¦  [formatting]  <--  | listing | <-- | entries |
                     V   ¦                     +---------+     +---------+

    +-------------------------------------+
    |                clients              |
    +-------------------------------------+

            ¦                     Λ
            V                     ¦

    +--------------+   |   +--------------+
    | httprequests |   |   |              |     FRONTEND
    +--------------+   |   |              |
    ================   |   |              |    ==========
    +--------------+   |   | localserver  |
    |    fflask    |   |   |              |     BACKEND
    +--------------+   |   |              |
    |  resources   |   |   |              |
    +--------------+   |   +--------------+

            ¦                     Λ
            V                     ¦
    +-------------------------------------+
    |                server               |
    +-------------------------------------+
            ¦                     Λ
            V                     ¦
    +-------------------------------------+
    |                pocket               |
    +-------------------------------------+

## Known bugs

- see [issues](https://github.com/pylipp/financeager_flask/labels/bug)

## Development

### Set up

    python3 -m venv .venv
    source .venv/bin/activate
    make install

You're all set for hacking!

### Testing

Please adhere to test-driven development, if possible: When adding a feature, or fixing a bug, try to construct a test first, and subsequently adapt the implementation. Run the tests from the root directory via

    make test

If you added a non-cosmetic change (i.e. a change in functionality, e.g. a bug fix or a new feature), please update `Changelog.md` accordingly as well. Check this README whether the content is still up to date.

### Releasing

1. Tag the latest commit on master by incrementing the current version accordingly (scheme `v0.major.minor.patch`).
1. Run `make release`.
