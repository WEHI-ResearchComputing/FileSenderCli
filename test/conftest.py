from pytest import Parser, Metafunc, skip

def pytest_addoption(parser: Parser):
    parser.addoption("--base-url", required=False)
    parser.addoption("--apikey", required=False)
    parser.addoption("--username", required=False)
    parser.addoption("--delay", required=False, default="0")
    parser.addoption("--recipient", help="Email address that will be used as the recipient of the invitations", required=False)

def pytest_generate_tests(metafunc: Metafunc):
    argnames = []
    argvalues = []

    for fixture in metafunc.fixturenames:
        if hasattr(metafunc.config.option, fixture):
            value = getattr(metafunc.config.option, fixture)
            if value is None:
                skip(f"--{fixture} not provided")
            argnames.append(fixture)
            argvalues.append(value)

    metafunc.parametrize(argnames, [argvalues])
