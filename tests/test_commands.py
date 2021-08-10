import types
from unittest import mock

import hikari
import pytest

import tanjun

from . import utilities


class Test_LoadableInjector:
    def test_make_method_type(self):
        mock_callback = mock.Mock()
        mock_self = object()
        injector = tanjun.commands._LoadableInjector(mock_callback)

        with mock.patch.object(tanjun.injecting, "check_injecting") as check_injecting:
            injector.make_method_type(mock_self)

            assert injector._needs_injector is check_injecting.return_value
            check_injecting.assert_called_once_with(injector.callback)

        assert injector.is_async is None
        assert isinstance(injector.callback, types.MethodType)
        injector.callback(123)
        mock_callback.assert_called_once_with(mock_self, 123)


class TestPartialCommand:
    @pytest.fixture()
    def command(self) -> tanjun.commands.PartialCommand:
        return utilities.stub_class(tanjun.commands.PartialCommand)()

    def test_metadata_property(self, command):
        assert command.metadata is command._metadata

    def test_needs_injector_when_any_true(self, command):
        command._checks = {mock.Mock(needs_injector=False), mock.Mock(needs_injector=True)}
        assert command.needs_injector is True

    def test_needs_injector_when_all_true(self, command):
        command._checks = {mock.Mock(needs_injector=True), mock.Mock(needs_injector=True)}
        assert command.needs_injector is True

    def test_needs_injector_when_all_false(self, command):
        command._checks = {mock.Mock(needs_injector=False), mock.Mock(needs_injector=False)}
        assert command.needs_injector is False

    def test_needs_injector_when_empty(self, command):
        assert command.needs_injector is False

    def test_copy(self, command):
        mock_check = mock.Mock()
        command._checks = {mock_check}
        command._hooks = mock.Mock()
        command._metadata = mock.Mock()

        new_command = command.copy()

        assert new_command is not command
        new_command._checks is {mock_check.copy.return_value}
        assert new_command._hooks is command._hooks.copy.return_value
        assert new_command._metadata is command.metadata.copy.return_value

    def test_set_hooks(self, command):
        mock_hooks = object()

        assert command.set_hooks(mock_hooks) is command
        assert command.hooks is mock_hooks

    def test_add_check(self, command):
        command.set_injector(object())
        mock_check = mock.Mock()

        assert command.add_check(mock_check) is command

        assert len(command._checks) == 1
        check = next(iter(command._checks))
        assert isinstance(check, tanjun.injecting.InjectableCheck)
        assert check.injector is command._injector
        assert check.callback is mock_check
        assert command.checks == {mock_check}

    def test_remove_check(self, command):
        def mock_check():
            ...

        command._checks = {tanjun.injecting.InjectableCheck(mock_check)}

        command.remove_check(mock_check)

        assert command.checks == set()

    def test_with_check(self, command):
        command.set_injector(object())

        def mock_check(self):
            ...

        assert command.with_check(mock_check) is mock_check

        assert len(command._checks) == 1
        check = next(iter(command._checks))
        assert isinstance(check, tanjun.commands._LoadableInjector)
        assert check.injector is command._injector
        assert check.callback is mock_check
        assert command.checks == {mock_check}

    def test_set_injector(self, command):
        mock_injector = object()
        mock_check = mock.Mock()
        command._checks = {mock_check}

        command.set_injector(mock_injector)

        assert command._injector is mock_injector
        mock_check.set_injector.assert_called_once_with(mock_injector)

    def test_set_injector_when_already_set(self, command):
        command._injector = object()
        mock_injector = object()
        mock_check = mock.Mock()
        command._checks = {mock_check}

        with pytest.raises(RuntimeError):
            command.set_injector(mock_injector)

        assert command._injector is not mock_injector
        mock_check.set_injector.assert_not_called()

    def test_bind_client(self, command):
        command.bind_client(object())

    def test_bind_component(self, command):
        mock_component = object()

        command.bind_component(mock_component)

        assert command.component is mock_component

    def test_load_into_component(self, command):
        mock_check_1 = mock.MagicMock(tanjun.commands._LoadableInjector)
        mock_check_2 = mock.Mock()
        mock_check_3 = mock.MagicMock(tanjun.commands._LoadableInjector)
        mock_component = object()
        command._checks = {mock_check_1, mock_check_2, mock_check_3}

        result = command.load_into_component(mock_component)

        assert result is None
        mock_check_1.make_method_type.assert_called_once_with(mock_component)
        mock_check_2.make_method_type.assert_not_called()
        mock_check_3.make_method_type.assert_called_once_with(mock_component)


def test_slash_command_group():
    command = tanjun.slash_command_group("a_name", "very", command_id=123, default_to_ephemeral=True, is_global=False)

    assert command.name == "a_name"
    assert command.description == "very"
    assert command.tracked_command_id == 123
    assert command.defaults_to_ephemeral is True
    assert command.is_global is False
    assert isinstance(command, tanjun.SlashCommandGroup)


def test_slash_command_group_with_default():
    command = tanjun.slash_command_group("a_name", "very")

    assert command.tracked_command_id is None
    assert command.defaults_to_ephemeral is False
    assert command.is_global is True
    assert isinstance(command, tanjun.SlashCommandGroup)


def test_as_slash_command():
    mock_callback = object()

    command = tanjun.as_slash_command(
        "a_very", "cool name", command_id=123321, default_to_ephemeral=True, is_global=False, sort_options=False
    )(mock_callback)

    assert command.name == "a_very"
    assert command.description == "cool name"
    assert command.tracked_command_id == 123321
    assert command.defaults_to_ephemeral is True
    assert command.is_global is False
    assert command._builder._sort_options is False
    assert isinstance(command, tanjun.SlashCommand)


def test_as_slash_command_with_defaults():
    mock_callback = object()

    command = tanjun.as_slash_command("a_very", "cool name")(mock_callback)

    assert command.tracked_command_id is None
    assert command.defaults_to_ephemeral is False
    assert command.is_global is True
    assert command._builder._sort_options is True
    assert isinstance(command, tanjun.SlashCommand)


def test_with_str_slash_option():
    mock_command = mock.MagicMock()
    mock_converter = object()

    tanjun.with_str_slash_option(
        "a_name", "a_value", choices=["ok", ("no", "u")], converters=[mock_converter], default="ANY"
    )(mock_command)

    mock_command.add_option.assert_called_once_with(
        "a_name",
        "a_value",
        hikari.OptionType.STRING,
        default="ANY",
        choices=[("Ok", "ok"), ("no", "u")],
        converters=[mock_converter],
    )


def test_with_str_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_str_slash_option("a_name", "a_value")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "a_name",
        "a_value",
        hikari.OptionType.STRING,
        default=tanjun.commands._UNDEFINED_DEFAULT,
        choices=(),
        converters=(),
    )


def test_with_int_slash_option():
    mock_command = mock.MagicMock()
    mock_converter = object()

    tanjun.with_int_slash_option(
        "im_con", "con man", choices=[("a", "man")], converters=[mock_converter], default=321123
    )(mock_command)

    mock_command.add_option.assert_called_once_with(
        "im_con",
        "con man",
        hikari.OptionType.INTEGER,
        choices=[("a", "man")],
        converters=[mock_converter],
        default=321123,
    )


def test_with_int_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_int_slash_option("im_con", "con man")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "im_con",
        "con man",
        hikari.OptionType.INTEGER,
        choices=None,
        converters=(),
        default=tanjun.commands._UNDEFINED_DEFAULT,
    )


def test_with_bool_slash_option():
    mock_command = mock.MagicMock()

    tanjun.with_bool_slash_option("bool", "bool me man", default=False)(mock_command)

    mock_command.add_option.assert_called_once_with("bool", "bool me man", hikari.OptionType.BOOLEAN, default=False)


def test_with_bool_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_bool_slash_option("bool", "bool me man")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "bool", "bool me man", hikari.OptionType.BOOLEAN, default=tanjun.commands._UNDEFINED_DEFAULT
    )


def test_with_user_slash_option():
    mock_command = mock.MagicMock()

    tanjun.with_user_slash_option("victim", "who're we getting next?", default=123321)(mock_command)

    mock_command.add_option.assert_called_once_with(
        "victim", "who're we getting next?", hikari.OptionType.USER, default=123321
    )


def test_with_user_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_user_slash_option("victim", "who're we getting next?")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "victim", "who're we getting next?", hikari.OptionType.USER, default=tanjun.commands._UNDEFINED_DEFAULT
    )


def test_with_member_slash_option():
    mock_command = mock.MagicMock()

    tanjun.with_member_slash_option("no", "hihihi?", default=123321)(mock_command)

    mock_command.add_option.assert_called_once_with(
        "no", "hihihi?", hikari.OptionType.USER, default=123321, only_member=True
    )


def test_with_member_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_member_slash_option("no", "hihihi?")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "no", "hihihi?", hikari.OptionType.USER, default=tanjun.commands._UNDEFINED_DEFAULT, only_member=True
    )


def test_with_role_slash_option():
    mock_command = mock.MagicMock()

    tanjun.with_role_slash_option("role", "role?", default=333)(mock_command)

    mock_command.add_option.assert_called_once_with("role", "role?", hikari.OptionType.ROLE, default=333)


def test_with_role_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_role_slash_option("role", "role?")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "role", "role?", hikari.OptionType.ROLE, default=tanjun.commands._UNDEFINED_DEFAULT
    )


def test_with_mentionable_slash_option():
    mock_command = mock.MagicMock()

    tanjun.with_mentionable_slash_option("mentu", "mentu?", default=333)(mock_command)

    mock_command.add_option.assert_called_once_with("mentu", "mentu?", hikari.OptionType.MENTIONABLE, default=333)


def test_with_mentionable_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    tanjun.with_mentionable_slash_option("mentu", "mentu?")(mock_command)

    mock_command.add_option.assert_called_once_with(
        "mentu", "mentu?", hikari.OptionType.MENTIONABLE, default=tanjun.commands._UNDEFINED_DEFAULT
    )
