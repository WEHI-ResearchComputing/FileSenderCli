from pytest import Parser, Metafunc

def pytest_addoption(parser: Parser):
    # Require the user to provide these arguments
    parser.addoption("--base-url", required=True)
    parser.addoption("--apikey", required=True)
    parser.addoption("--username", required=True)
    parser.addoption("--recipient", help="Email address that will be used as the recipient of the invitations", required=True)

def pytest_generate_tests(metafunc: Metafunc):
    argnames = []
    argvalues = []

    for fixture in metafunc.fixturenames:
        if hasattr(metafunc.config.option, fixture):
            argnames.append(fixture)
            argvalues.append(getattr(metafunc.config.option, fixture))

    metafunc.parametrize(argnames, [argvalues])
