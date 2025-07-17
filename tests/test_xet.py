import os
import shutil
from pathlib import Path

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


@pytest.fixture(autouse=True)
def data_path():
    test_path = os.path.abspath("tmp")
    backup_path = os.path.abspath("data")
    shutil.copytree(backup_path, test_path)
    yield Path(test_path)
    shutil.rmtree(test_path)


def test_tests():
    assert True


def test_file_restore(data_path):
    os.remove(os.path.abspath(data_path / "test.txt"))
    os.remove(data_path / "test_numbers.txt")
    assert not os.path.exists(os.path.abspath(data_path / "test.txt"))
    assert not os.path.exists(data_path / "test_numbers.txt")


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


def test_add(data_path):
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

    xet.main(
        ["add", "tag", "test_tag", os.path.abspath(data_path / "test.txt"), "TEST1 = "]
    )
    xet.main(
        ["add", "lc", "test_lc", os.path.abspath(data_path / "test.txt"), "420", "69"]
    )
    xet.main(
        [
            "add",
            "regex",
            "test_regex",
            os.path.abspath(data_path / "test.txt"),
            "^regex:",
        ]
    )

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


def test_get_tag(capsys, data_path):
    xet.main(
        ["add", "tag", "test_1", os.path.abspath(data_path / "test.txt"), "TEST1 = "]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_2",
            os.path.abspath(data_path / "test.txt"),
            "TEST2 = ",
            "-w",
            '"',
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_3",
            os.path.abspath(data_path / "test.txt"),
            "TEST3: ",
            "-w",
            "'",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_4",
            os.path.abspath(data_path / "test.txt"),
            "TEST4, ",
            "-w",
            "__",
        ]
    )
    xet.main(
        ["add", "tag", "test_5", os.path.abspath(data_path / "test.txt"), "TEST5: "]
    )

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "ABC\nDEF\nghi\njkl\nmno\npqr"


def test_get_lc(capsys, data_path):
    xet.main(
        ["add", "lc", "test_6", os.path.abspath(data_path / "test.txt"), "7", "16"]
    )
    xet.main(
        [
            "add",
            "lc",
            "test_7",
            os.path.abspath(data_path / "test.txt"),
            "8",
            "1",
            "-e",
            " 8:1 TEST7",
        ]
    )

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "sTu\nvwx"


def test_get_regex(capsys, data_path):
    xet.main(
        [
            "add",
            "regex",
            "test_8",
            os.path.abspath(data_path / "test.txt"),
            r"^\w* rege",
            "--wrapper",
            "_",
            "--occurences",
            "0",
        ]
    )
    xet.main(
        [
            "add",
            "regex",
            "test_9",
            os.path.abspath(data_path / "test.txt"),
            r"^\w* rege",
            "--occurences",
            "1",
        ]
    )

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "xyz\nxyz"


def test_get_occurences(capsys, data_path):
    xet.main(
        [
            "add",
            "regex",
            "test_occ",
            os.path.abspath(data_path / "test.txt"),
            r"^TEST\d",
            "--occurences",
            "1:3",
        ]
    )

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == " = \"DEF\"\n: 'ghi'"

    xet.main(
        [
            "add",
            "regex",
            "test_occ",
            os.path.abspath(data_path / "test.txt"),
            r"^TEST\d",
            "--occurences",
            "1",
            "2",
        ]
    )

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == " = \"DEF\"\n: 'ghi'"


def test_filtering(capsys, data_path):
    xet.main(
        [
            "add",
            "tag",
            "test_1",
            os.path.abspath(data_path / "test.txt"),
            "TEST1 = ",
            "-f",
            "f1",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_2",
            os.path.abspath(data_path / "test.txt"),
            "TEST2 = ",
            "-w",
            '"',
            "-f",
            "f1",
            "f2",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_3",
            os.path.abspath(data_path / "test.txt"),
            "TEST3: ",
            "-w",
            "'",
            "-f",
            "f2",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_4",
            os.path.abspath(data_path / "test.txt"),
            "TEST4, ",
            "-w",
            "__",
            "-f",
            "f3",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_5",
            os.path.abspath(data_path / "test.txt"),
            "TEST5: ",
            "--flags",
            "f3",
            "f2",
        ]
    )

    test_scenarios = [
        (["get", "-o", "f1"], "ABC\nDEF"),
        (["get", "-o", "f1", "f2"], "ABC\nDEF\nghi\nmno\npqr"),
        (["get", "--only", "f3"], "jkl\nmno\npqr"),
        (["get", "-e", "f2", "f3"], "ABC"),
        (["get", "--except", "f1"], "ghi\njkl\nmno\npqr"),
        (["get", "-n", "test_2"], "DEF"),
        (["get", "--names", "test_2", "test_3"], "DEF\nghi"),
    ]

    for input, expected in test_scenarios:
        xet.main(input)

        output = capsys.readouterr().out.rstrip()

        assert output == expected


def test_set_tag(capsys, data_path):
    xet.main(
        ["add", "tag", "test_1", os.path.abspath(data_path / "test.txt"), "TEST1 = "]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_2",
            os.path.abspath(data_path / "test.txt"),
            "TEST2 = ",
            "-w",
            '"',
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_3",
            os.path.abspath(data_path / "test.txt"),
            "TEST3: ",
            "-w",
            "'",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_4",
            os.path.abspath(data_path / "test.txt"),
            "TEST4, ",
            "-w",
            "__",
        ]
    )

    xet.main(["set", "TEST"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "TEST\nTEST\nTEST\nTEST"


def test_equality(capsys, data_path):
    xet.main(
        [
            "add",
            "tag",
            "eq_test",
            os.path.abspath(data_path / "test.txt"),
            "TEST_EQUALITY",
        ]
    )

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "TEST_EQUALITY"
