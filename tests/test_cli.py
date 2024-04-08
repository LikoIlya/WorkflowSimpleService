import pytest

given = pytest.mark.parametrize


def test_help(cli_client, cli):
    result = cli_client.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout


@given(
    "cmd,args,msg",
    [
        ("run", ["--help"], "--port"),
    ],
)
def test_cmds_help(cli_client, cli, cmd, args, msg):
    result = cli_client.invoke(cli, [cmd, *args])
    assert result.exit_code == 0
    assert msg in result.stdout
