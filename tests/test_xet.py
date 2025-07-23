import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

import xet

patcher = patch(
    "xet.xet.get_history_path",
    lambda: os.path.join(os.path.abspath(os.getcwd()), "tmp", xet.HISTORY_FILE),
)
patcher.start()


@pytest.fixture(autouse=True)
def change_test_dir(monkeypatch):
    monkeypatch.chdir(os.path.abspath(__file__.rstrip(".py").rstrip(__name__)))


@pytest.fixture(autouse=True)
def delete_dot_xet():
    if os.path.exists(os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE)):
        os.remove(os.path.join(os.path.abspath(os.getcwd()), xet.CONFIG_FILE))
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
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
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

    config = xet.parse_config()

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

    xet.main(["get", "-v"])

    output = capsys.readouterr().out.rstrip()

    assert output == (
        "\x1b[34mTEST1 = \x1b[0m\x1b[31mABC\x1b[0m\n"
        '\x1b[34mTEST2 = \x1b[0m"\x1b[31mDEF\x1b[0m"\n'
        "\x1b[34mTEST3: \x1b[0m'\x1b[31mghi\x1b[0m'\n"
        "\x1b[34mTEST4, \x1b[0m__\x1b[31mjkl\x1b[0m__\n"
        "\x1b[34mTEST5: \x1b[0m\x1b[31mmno\x1b[0m\n"
        "\x1b[34mTEST5: \x1b[0m\x1b[31mpqr\x1b[0m"
    )

    xet.main(["get", "-vv"])

    output = capsys.readouterr().out.rstrip()
    filepath = os.path.abspath(data_path / "test.txt")
    assert output == (
        f"\x1b[32mtest_1\x1b[36m:\x1b[35m"
        f"{filepath}"
        f"\x1b[36m:\x1b[34mTEST1 = \x1b[36m:\x1b[0m\n"
        f"\x1b[34mTEST1 = \x1b[0m\x1b[31mABC\x1b[0m\n"
        f"\x1b[32mtest_2\x1b[36m:\x1b[35m"
        f"{filepath}"
        f"\x1b[36m:\x1b[34mTEST2 = \x1b[36m:\x1b[0m\n"
        f'\x1b[34mTEST2 = \x1b[0m"\x1b[31mDEF\x1b[0m"\n'
        f"\x1b[32mtest_3\x1b[36m:\x1b[35m"
        f"{filepath}"
        f"\x1b[36m:\x1b[34mTEST3: \x1b[36m:\x1b[0m\n"
        f"\x1b[34mTEST3: \x1b[0m'\x1b[31mghi\x1b[0m'\n"
        f"\x1b[32mtest_4\x1b[36m:\x1b[35m"
        f"{filepath}"
        f"\x1b[36m:\x1b[34mTEST4, \x1b[36m:\x1b[0m\n"
        f"\x1b[34mTEST4, \x1b[0m__\x1b[31mjkl\x1b[0m__\n"
        f"\x1b[32mtest_5\x1b[36m:\x1b[35m"
        f"{filepath}"
        f"\x1b[36m:\x1b[34mTEST5: \x1b[36m:\x1b[0m\n"
        f"\x1b[34mTEST5: \x1b[0m\x1b[31mmno\x1b[0m\n"
        f"\x1b[34mTEST5: \x1b[0m\x1b[31mpqr\x1b[0m"
    )


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

    xet.main(["get", "-v"])

    output = capsys.readouterr().out.rstrip()

    assert output == (
        "TEST6....7:16: \x1b[31msTu\x1b[0m" "\n\x1b[31mvwx\x1b[0m 8:1 TEST7"
    )


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

    xet.main(
        [
            "add",
            "regex",
            "test_10",
            os.path.abspath(data_path / "test.txt"),
            r"(^\w* rege)(_)(\w*)(_)",
            "-c",
            "3",
            "-f",
            "group",
        ]
    )

    xet.main(["get", "-e", "group"])

    output = capsys.readouterr().out.rstrip()

    assert output == "xyz\nxyz"

    xet.main(["get", "-o", "group"])

    output = capsys.readouterr().out.rstrip()

    assert output == "xyz"

    xet.main(["get", "-e", "group", "-v"])

    output = capsys.readouterr().out.rstrip()

    assert output == ("TEST8 rege_\x1b[31mxyz\x1b[0m_" "\nTEST9 rege\x1b[31mxyz\x1b[0m")


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


def test_tag_equality(capsys, data_path):
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


def test_set_lc(capsys, data_path):
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

    xet.main(["set", "TEST"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "TEST\nTEST"


def test_set_regex(capsys, data_path):
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
    xet.main(
        [
            "add",
            "regex",
            "test_10",
            os.path.abspath(data_path / "test.txt"),
            r"(^\w* rege)(_)(\w*)(_)",
            "-c",
            "3",
            "-f",
            "group",
        ]
    )

    xet.main(["set", "TEST", "-e", "group"])

    xet.main(["get", "-e", "group"])

    output = capsys.readouterr().out.rstrip()

    assert output == "TEST\nTEST"

    xet.main(["set", "xyz", "-e", "group"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "xyz\nxyz\nxyz"

    xet.main(["set", "TEST", "-o", "group"])

    xet.main(["get", "-o", "group"])

    output = capsys.readouterr().out.rstrip()

    assert output == "TEST"


def test_preset_snapshot(capsys, data_path):
    xet.main(
        [
            "add",
            "tag",
            "test_1",
            os.path.abspath(data_path / "test.txt"),
            "TEST1 = ",
            "-p",
            "pre1",
            "test",
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
            "-p",
            "pre1",
            "test",
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
            "-p",
            "pre1",
            "test",
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
            "-p",
            "pre1",
            "test",
        ]
    )
    xet.main(
        [
            "add",
            "tag",
            "test_5",
            os.path.abspath(data_path / "test.txt"),
            "TEST5: ",
            "-o",
            "0",
            "-p",
            "pre1",
            "test",
        ]
    )

    xet.main(["snapshot", "pre2"])

    xet.main(["undo"])

    config = xet.parse_config()

    for entry in config.values():
        assert "pre2" not in entry["presets"]

    xet.main(["redo"])

    xet.main(["preset", "pre1"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "test\ntest\ntest\ntest\ntest"

    xet.main(["preset", "pre2"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "ABC\nDEF\nghi\njkl\nmno"

    xet.main(["undo"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "test\ntest\ntest\ntest\ntest"


def test_history(capsys, data_path):
    xet.main(
        [
            "add",
            "tag",
            "test_1",
            os.path.abspath(data_path / "test.txt"),
            "TEST1 = ",
        ]
    )

    xet.main(["undo"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == ""

    xet.main(["redo"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "ABC"

    xet.main(["remove", "-n", "test_1"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == ""

    xet.main(["undo"])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "ABC"

    xet.main(["forget"])

    xet.main(["undo"])

    output = capsys.readouterr().out.rstrip()

    assert output == "Nothing to undo"

    xet.main(["redo"])

    output = capsys.readouterr().out.rstrip()

    assert output == "Nothing to redo"

    xet.main(["set", "TEST"])
    xet.main(["undo"])
    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "ABC"

    xet.main(["redo"])
    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "TEST"


def test_update(capsys, data_path):
    xet.main(
        [
            "add",
            "tag",
            "test_1",
            os.path.abspath(data_path / "test.txt"),
            "TEST1 = ",
        ]
    )

    xet.main(["update", "tag", "TEST2 = "])

    xet.main(["update", "wrapper", '"'])

    xet.main(["get"])

    output = capsys.readouterr().out.rstrip()

    assert output == "DEF"

    xet.main(["update", "name", "renamed_test"])

    xet.main(["get", "-n", "renamed_test"])

    output = capsys.readouterr().out.rstrip()

    assert output == "DEF"


def test_enumerate_slice(capsys):
    length = 10
    sl = xet.parse_index_or_slice("1:5")

    assert [1, 2, 3, 4] == list(range(length))[sl]
