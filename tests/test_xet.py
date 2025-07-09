import os

import pytest

import xet


@pytest.fixture(autouse=True)
def change_test_dir(monkeypatch):
    monkeypatch.chdir(os.path.abspath(__file__.rstrip(".py").rstrip(__name__)))


@pytest.fixture(autouse=True)
def delete_dot_xet():
    yield
    if os.path.exists(os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE)):
        os.remove(os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE))


@pytest.fixture(autouse=True)
def init_dot_xet(request):
    if "noinit" in request.keywords:
        return
    xet.main(["init"])


def test_tests():
    assert True


@pytest.mark.noinit
def test_which(capsys):
    xet.main(["which"])
    output = capsys.readouterr().out.rstrip()

    expected_output = os.path.join(os.environ.get("XDG_CONFIG_HOME"), xet.CONFIG_FILE)
    assert output == expected_output
    assert xet.get_abs_config_path() == expected_output

    xet.main(["init"])

    xet.main(["which"])
    output = capsys.readouterr().out.rstrip()
    expected_output = os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE)
    assert output == expected_output
    assert xet.get_abs_config_path() == expected_output


@pytest.mark.noinit
def test_init():
    assert not os.path.exists(
        os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE)
    )
    xet.main(["init"])
    assert os.path.exists(os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE))


def test_add():
    global_config_options = [
        "type",
        "filepath",
        "flags",
        "presets",
        "ssh",
        "wrapper",
    ]

    tag_config_options = ["tag", "occurences", "end"]

    lc_config_options = ["line", "column", "end"]

    regex_config_options = ["regex", "occurences", "group"]

    xet.main(["add", "tag", "test_tag", "data/test.txt", "TEST1 = "])
    xet.main(["add", "lc", "test_lc", "data/test.txt", "420", "69"])
    xet.main(["add", "regex", "test_regex", "data/test.txt", "^regex:"])

    config = xet.load_config()

    assert "test_tag" in config
    assert "test_lc" in config
    assert "test_regex" in config

    assert all(
        [
            config_option in config["test_tag"]
            for config_option in global_config_options + tag_config_options
        ]
    )

    assert all(
        [
            config_option in config["test_lc"]
            for config_option in global_config_options + lc_config_options
        ]
    )

    assert all(
        [
            config_option in config["test_regex"]
            for config_option in global_config_options + regex_config_options
        ]
    )


def test_get(capsys):
    xet.main(["add", "tag", "test_1", "./data/test.txt", "TEST1 = "])
    xet.main(["add", "tag", "test_2", "data/test.txt", "TEST2 = ", "-w", '"'])
    xet.main(["add", "tag", "test_3", "data/test.txt", "TEST3: ", "-w", "'"])
    xet.main(["add", "tag", "test_4", "data/test.txt", "TEST4, ", "-w", "__"])
    xet.main(["add", "tag", "test_5", "data/test.txt", "TEST5: "])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "ABC\nDEF\nghi\njkl\nmno\npqr"
