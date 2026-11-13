from common.engine import Engine, EngineHooks
from common.header import shared


def make_engine():
    output: list[str] = []
    forwarded: list[list[str]] = []
    holder: dict[str, Engine] = {}
    hooks = EngineHooks(
        print_=output.append, fatal_error=lambda text: None, server_running=lambda: False,
        game_changed=lambda game: None, user_game_changed=lambda game: None,
        load_file=lambda name: None, milliseconds=lambda: 0,
        forward_to_server=lambda: forwarded.append(list(holder["engine"].commands.argv)))
    engine = Engine(hooks)
    holder["engine"] = engine
    return engine, output, forwarded


def test_commands_see_the_cvars():
    engine, output, forwarded = make_engine()
    engine.cvars.get("name", "Player", shared.CVAR_USERINFO)
    engine.commands.register_builtins()
    engine.commands.execute_string("echo $name")
    assert output[-1] == "Player \n"
    engine.commands.execute_string("name Other")  # a cvar typed as a command
    assert engine.cvars.string("name") == "Other"
    engine.commands.execute_string("kill")  # neither: sent to the server
    assert forwarded == [["kill"]]


def test_engines_are_independent():
    first, _, _ = make_engine()
    second, _, _ = make_engine()
    first.cvars.get("fov", "90", 0)
    assert second.cvars.find("fov") is None
