# -*- coding: utf-8 -*-
"""
Created on 2023.05.24

@author: uid7067
"""

# %%
from shutil import rmtree
import sys
from os.path import join, exists, isdir
from os import makedirs, environ
from contextlib import contextmanager
import re
from secrets import token_bytes

from configparser import DuplicateSectionError, DuplicateOptionError
import logging
from mock import patch

import pytest
from loguru import logger
from loguru_caplog import loguru_caplog as caplog  # noqa: F401

from localizer import tr, set_language
from settingsclass.settingsclass import (
    settingsclass,
    RandomFloat,
    RandomInt,
    RandomString,
    Encrypted,
    Hidden,
    encrypt_message,
    decrypt_message,
    _within_random_limits,
)
from settingsclass import settingsclass as settingclass_lib

import warnings

# %%
PARENT_IN = join("tests", "input", "settingsclass")
PARENT_OUT = join("tests", "output", "settingsclass")
set_language("en")


@pytest.fixture(scope="session", autouse=True)
def clean_output():
    """テストの前に出力フォルダーを削除し、再生成する"""
    if exists(PARENT_OUT):
        rmtree(PARENT_OUT)

    makedirs(PARENT_OUT)


# %%


@contextmanager
def silent_output():
    logger.disable("settingsclass")
    try:
        yield None
    finally:
        logger.enable("settingsclass")


@settingsclass(
    encryption_key="123X456", _salt=b"\x86\xce'?\xbc\x1eA\xd3&\x84\x82\xb4\xa3\x99\x10P"
)
class Settings:
    """設定ファイルを初期化するときに使われる値。ロードするときにタイプヒントを確認する。
    RandomString・RandomInt・RandomFloatの初期値値は無視される"""

    # file_path = '<NOT_SET>'

    class program:
        lang: str = "ja"
        log_level: str = "debug"
        colored_console_output: Hidden[bool] = True  # ログをカラー表示するか
        machine_id: RandomString[5] = ""
        auto_update_model: bool = False
        rfph: RandomFloat[0, 2**16] = 1.2
        seed: Encrypted[RandomFloat[0, 2**16]] = 1.2
        api_id: RandomInt[1000, 9999] = 0

    class gpt:
        api_key: Encrypted[str] = ""
        backup_pin: Encrypted[int] = -1
        temperature: Hidden[float] = 5
        timeout: int = 300


# %% Test internal functions


def test_random_int():
    """エラー発生、1000回実行し、全ての値が範囲内にあるかどうかを確認する"""
    maxval = 7
    minval = 2
    vals = []
    for i in range(1000):
        val = RandomInt(minval, maxval)
        assert val <= maxval and val >= minval
        vals.append(val)

    for i in range(minval, maxval + 1):
        assert i in vals

    # パラメータ数
    with pytest.raises(TypeError):
        RandomInt(5)

    # パラメータ型
    with pytest.raises(ValueError), pytest.warns(DeprecationWarning):
        warnings.warn(
            "Just to ignore this specific wanring, since it trows Exception anyway",
            DeprecationWarning,
        )
        RandomInt(1.2, 3.3)

    with pytest.raises(TypeError):
        RandomInt("5")

    # 指定された関数を使っていること
    vals = set()
    for _ in range(1000):
        vals.add(RandomInt(-5, 100, lambda a, b: 92))

    assert vals == {92}


def test_random_float():
    """エラー発生、1000回実行し、全ての値が範囲内にあるかどうかを確認する"""

    for minval, maxval in ((1.3, 4.1), (8, 12)):
        vals = []
        for i in range(1000):
            val = RandomFloat(minval, maxval)
            assert val < maxval and val >= minval
            vals.append(val)

        # 3分の一に入る値がある
        for v in vals:
            if v < minval + (maxval - minval) / 4:
                break
        else:
            raise AssertionError(tr("lower_third_not_reached_during_ddcsst"))

        # 上の3分の一に入る値がある
        for v in vals:
            if v > minval + 3 * (maxval - minval) / 4:
                break
        else:
            raise AssertionError(tr("higher_third_not_reached_during_ddcsst"))

    # パラメータ数
    with pytest.raises(TypeError):
        RandomFloat(5.1)

    # パラメータ型
    with pytest.raises(TypeError):
        RandomFloat("5")

    # 指定された関数を使っていること
    vals = set()
    for _ in range(1000):
        vals.add(RandomFloat(1, 2, lambda: 92))

    assert vals == {93}


def test_random_str():
    for minval, maxval in ((0, 5), (6, 11)):
        vals = []
        for _ in range(1000):
            val = RandomString(maxval, minval) if minval else RandomString(maxval)
            assert len(val) <= maxval and len(val) >= minval
            vals.append(val)

        val_lens = {len(v) for v in vals}
        if minval:
            for i in range(minval, maxval):
                assert i in val_lens
        else:
            assert val_lens == {maxval}

    vals = set()
    for _ in range(10000):
        vals.add(RandomString(105, 10, lambda _: "alma"))

    assert vals == {"alma"}


def test_limit_verification():
    assert _within_random_limits(RandomString[5], "abcde")
    # with pytest.raises():
    assert not _within_random_limits(RandomString[5], "abcd")
    assert not _within_random_limits(RandomString[5], "")
    assert not _within_random_limits(RandomString[5], "abcdef")

    assert not _within_random_limits(RandomString[2, 5], "")
    assert not _within_random_limits(RandomString[2, 5], "a")
    assert _within_random_limits(RandomString[2, 5], "ab")
    assert _within_random_limits(RandomString[2, 5], "abc")
    assert _within_random_limits(RandomString[2, 5], "abcd")
    assert _within_random_limits(RandomString[2, 5], "abcde")
    assert not _within_random_limits(RandomString[2, 5], "abcdef")

    # random.randintを使用しているため、下限と上限も含む
    assert not _within_random_limits(RandomInt[2, 5], 1)
    assert _within_random_limits(RandomInt[2, 5], 2)
    assert _within_random_limits(RandomInt[2, 5], 4)
    assert _within_random_limits(RandomInt[2, 5], 5)
    assert not _within_random_limits(RandomInt[2, 5], 6)

    # random.randomを使用しているため、上限は含まないが、設定的に両方を含む場合は多い気がします
    assert not _within_random_limits(RandomFloat[2, 5], 1.99)
    assert _within_random_limits(RandomFloat[2, 5], 2)
    assert _within_random_limits(RandomFloat[2, 5], 2.0)
    assert _within_random_limits(RandomFloat[2, 5], 3)
    assert _within_random_limits(RandomFloat[2, 5], 4.99)
    assert _within_random_limits(RandomFloat[2, 5], 5.0)
    assert not _within_random_limits(RandomFloat[2, 5], 5.001)
    assert not _within_random_limits(RandomFloat[2, 5], 6)


# Mock load key to not use any files
@pytest.mark.skip("Temporarily disabled due to patching issue")
@patch.object(settingclass_lib, "_load_key")
def test_encrypt_decrypt_fileless(load_key_fileless):
    load_key_fileless.return_value = token_bytes(16)
    for keylen in range(6, 20):
        key = RandomString(keylen)
        for _ in range(200):
            s = RandomString(RandomInt(1, 30))
            assert s == decrypt_message(encrypt_message(s, key), key)


# Mock load key to not create the files inside the test folder
@patch("os.path.join")
def test_encrypt_decrypt_fileful(load_key_custom_path):
    parent = join(PARENT_OUT, "settingsclass", "keyfiles")
    makedirs(parent)
    load_key_custom_path.return_value = join(parent, "975321984")
    for keylen in range(6, 20):
        key = RandomString(keylen)
        for _ in range(200):
            s = RandomString(RandomInt(1, 30))
            assert s == decrypt_message(encrypt_message(s, key), key)


# %% Define multi-use expected values


def validate_good_contents(config: Settings):
    """予期の内容を確認する。複数のパスで利用するため"""
    assert config.program.lang == "xr"  # modified, shifted down in .ini
    assert config.program.log_level == "debug"  # not ~
    assert config.program.colored_console_output is False  # mod
    assert config.program.machine_id == "U&TG"  # mod
    assert config.program.auto_update_model is True  # mod
    assert config.program.rfph == 34260.804  # mod
    assert config.program.seed == 99.8  # mod
    assert config.program.api_id == 9955  # mod

    assert config.gpt.api_key == "sk-123kld-12141"  # dmod
    assert config.gpt.backup_pin == 852  # mod
    assert config.gpt.temperature == 0.15  # mod
    assert config.gpt.timeout == 281


def validate_init_contents(config: Settings):
    """初期化された状態のパラメータの確認。複数のパスで利用するため"""
    assert config.program.lang == "ja"
    assert config.program.log_level == "debug"
    assert config.program.colored_console_output is True
    assert isinstance(mid := config.program.machine_id, str)
    assert len(mid) == 5
    assert config.program.auto_update_model is False
    assert isinstance(rf := config.program.rfph, float)
    assert rf >= 0 and rf <= 2**16

    assert isinstance(seed := config.program.seed, float)
    assert seed >= 0 and seed <= 2**16

    assert isinstance(api_id := config.program.api_id, int)
    assert api_id >= 1000 and api_id <= 9999

    assert config.gpt.api_key == ""
    assert config.gpt.backup_pin == -1
    assert config.gpt.temperature == 5
    assert config.gpt.timeout == 300


def test_ram_only_init():
    with silent_output():
        ram_settigns = Settings(None)
    validate_init_contents(ram_settigns)


def test_settings_read():
    """りそうな場合の内容確認"""
    # UTF-8とキャストのテストも含む

    with silent_output():
        config = Settings(join(PARENT_IN, "config_modified.ini"))
    validate_good_contents(config)


def test_object_not_static():
    with silent_output():
        config1 = Settings(join(PARENT_IN, "config_modified.ini"))
        config2 = Settings(join(PARENT_IN, "config_modified.ini"))
    validate_good_contents(config1)
    validate_good_contents(config2)

    config1.gpt.api_key = "aqsd"
    config1.program.seed = 21

    validate_good_contents(config2)

    config2.program.seed = 99
    assert config1.program.seed == 21

    config1.program = None

    assert not config1.program
    assert config2.program.seed == 99


def test_case_sensitivity():
    """「case_sensitive」パラメータ効果の有無確認"""
    # UTF-8とキャストのテストも含む

    with silent_output():
        config = Settings(join(PARENT_IN, "config_good_case_var.ini"))
    validate_good_contents(config)

    # 有効化の場合は読み込んだパラメータ名とSettings.pyの名は異なり、デフォルト値になります。
    with silent_output():
        config = Settings(
            join(PARENT_IN, "config_good_case_var.ini"), case_sensitive=True
        )
    with pytest.raises(AssertionError):
        validate_good_contents(config)


def test_settings_is_folder():
    """設定ファイルのパスはフォルダーになった場合のエラーの確認"""
    ini_dir = join(PARENT_IN, "config.ini")
    assert exists(ini_dir) and isdir(
        ini_dir
    ), f"Test setup is incorrect, {ini_dir} should be a directory"

    # path <- config.ini/config.ini、最初はフォルダー

    with silent_output():
        config = Settings(ini_dir)
    validate_good_contents(config)

    # path <- config.iniのフォルダー
    with pytest.raises(IsADirectoryError), silent_output():
        config = Settings(PARENT_IN)


def test_settings_init():
    """初期化値、と生成されたファイルフォーマットの確認"""
    hat_path_constructor = join(PARENT_OUT, "config_generated_constr.ini")
    hat_path_func_call = join(PARENT_OUT, "config_generated_func.ini")
    gold_path = join(PARENT_IN, "config_generated_good.ini")

    with silent_output():
        config = Settings(hat_path_constructor)
        validate_init_contents(config)
    config.save_to_file(hat_path_func_call)

    for hat_path in [hat_path_func_call, hat_path_constructor]:
        with open(hat_path, encoding="utf-8") as file:
            hat = file.read()
            hat = re.sub(
                r"(machine_id = )(.{3,7})(\r*\n)",
                r"\1ABCD\3",
                hat,
            )
            hat = re.sub(
                r"(rfph =)(.*)(\r*\n)",
                r"\1 34260.804\3",
                hat,
            )
            hat = re.sub(
                r"(seed =)(.*)(\r*\n)",
                r"\1 ?ENCa6ae7caffd3723def41c789b52a07cef02d2a476a7280451bac778cba4c43695\3",
                hat,
            )
            hat = re.sub(
                r"(api_id =)(.*)(\r*\n)",
                r"\1 1234\3",
                hat,
            )
            hat = re.sub(
                r"(backup_pin =)(.*)(\r*\n)",
                r"\1 ?ENCef3106b5b827128acf69551ce6d4603fbad14bce053b7105efad047ff13b3cc5\3",
                hat,
            )

        with open(gold_path, encoding="utf-8") as file:
            gold = file.read()
        assert gold == hat


def test_missing_section_and_variable(caplog):  # noqa: F811
    """存在しない項目やパラメータがあるの時の警告発生の確認"""

    # 1回目で生成して、保存されていないため２回実行する、最初のログは無視する
    for _ in range(2):
        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            _ = Settings(join(PARENT_IN, "config_missing_section.ini"))

    # エラーがある場合、まずはエラーメッセージ内容、引数などが変わっていないことを確認して下さい
    assert tr("missing_config_section_1", "gpt") in caplog.text
    assert tr("config_param_missing_2", "program", "rfph") in caplog.text
    assert tr("config_param_missing_2", "program", "seed") in caplog.text


def test_extra_section_and_variables(caplog):  # noqa: F811
    """configファイルに不要な項目やパラメータがあるときの時の警告発生の確認"""

    with caplog.at_level(logging.DEBUG):
        _ = Settings(join(PARENT_IN, "config_extra_parts.ini"))

    # エラーがある場合、まずはエラーメッセージ内容、引数などが変わっていないことを確認して下さい
    assert tr("extra_config_sections_1", ["Imaginary_section"]) in caplog.text
    assert (
        tr(
            "extra_config_parameter_2",
            "gpt",
            ["imaginary_variable", "also_doesnt_exist"],
        )
        in caplog.text
    )


def test_duplicate_section():
    """重複の項目のエラー：configparserから発生される"""
    with pytest.raises(DuplicateSectionError), silent_output():
        _ = Settings(join(PARENT_IN, "config_duplicate_section.ini"))


def test_duplicate_parameter():
    """重複のパラメータのエラー：configparserから発生される"""
    with pytest.raises(DuplicateOptionError), silent_output():
        _ = Settings(join(PARENT_IN, "config_duplicate_param.ini"))


def test_invalid_param_type(caplog):  # noqa: F811
    """パラメータヒントと設定ファイルにあるタイプが異なる場合警告とデフォルト値にリセットすること"""

    with caplog.at_level(logging.DEBUG):
        config = Settings(join(PARENT_IN, "config_bad_type.ini"))

    assert (
        tr("invalid_type_4", "program", "colored_console_output", bool, "Igen")
        in caplog.text
    )
    assert tr("invalid_type_4", "program", "rfph", float, "alma") in caplog.text
    assert tr("invalid_type_4", "program", "api_id", int, "bar") in caplog.text

    api_id = config.program.api_id
    assert api_id >= 1000 and api_id <= 9999

    rf = config.program.rfph
    assert rf >= 0 and rf <= 2**16

    assert config.program.colored_console_output


def test_type_confusion(caplog):  # noqa: F811
    with caplog.at_level(logging.DEBUG):
        _ = Settings(join(PARENT_IN, "config_confusing_types.ini"))

    # エラーがある場合、まずはエラーメッセージ内容、引数などが変わっていないことを確認して下さい

    assert (
        tr("param_type_is_string_but_looks_x_4", "program", "lang", "True", "bool")
        in caplog.text
    )
    assert (
        tr("param_type_is_string_but_looks_x_4", "program", "log_level", 1, "int")
        in caplog.text
    )
    assert (
        tr("param_type_is_string_but_looks_x_4", "gpt", "api_key", 3.0, "float")
        in caplog.text
    )


# %% ENV check
def _set_env_values(
    new_values_dict: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    old_values = {}
    values_to_remove = []
    for key, value in new_values_dict.items():
        if key in environ:
            old_values[key] = environ[key]
        else:
            values_to_remove.append(key)
        environ[key] = str(value)

    return old_values, values_to_remove


def _reset_env_values(old_values: dict[str, str], values_to_remove: list[str]) -> None:
    for key, value in old_values.items():
        environ[key] = str(value)

    for key in values_to_remove:
        environ.pop(key)


def test_environmental_variables_instance():
    """環境変数の影響有無を確認する"""
    settings_path = join(PARENT_OUT, "config_env_test.ini")

    for prefix in ["", "AOYAMA"]:
        with silent_output():
            config = Settings(settings_path, env_prefix=prefix)
            config_disabled = Settings(settings_path, env_prefix=None)

        validate_init_contents(config)
        validate_init_contents(config_disabled)
        env_prefix = f'{prefix}{prefix and "_"}'

        old_values, temp_values = _set_env_values(
            {
                f"{env_prefix}PROGRAM_LANG": "xr",
                f"{env_prefix}PROGRAM_LOG_LEVEL": "debug",
                f"{env_prefix}PROGRAM_COLORED_CONSOLE_OUTPUT": "False",
                f"{env_prefix}PROGRAM_MACHINE_ID": "U&TG",
                f"{env_prefix}PROGRAM_AUTO_UPDATE_MODEL": "True",
                f"{env_prefix}PROGRAM_RFPH": 34260.804,
                f"{env_prefix}PROGRAM_SEED": 99.8,
                f"{env_prefix}PROGRAM_API_ID": 9955,
                f"{env_prefix}GPT_API_KEY": "sk-123kld-12141",
                f"{env_prefix}GPT_BACKUP_PIN": 852,
                f"{env_prefix}GPT_TEMPERATURE": 0.15,
                f"{env_prefix}GPT_TIMEOUT": 281,
            }
        )

        assert (not prefix) == ("PROGRAM_LANG" in environ)
        assert bool(prefix) == ("AOYAMA_PROGRAM_LANG" in environ)

        with silent_output():
            config = Settings(settings_path, env_prefix=prefix)
        validate_good_contents(config)
        validate_init_contents(config_disabled)

        _reset_env_values(old_values, temp_values)


def test_environmental_variables_decorator():
    ### preparation
    def randpath():
        return join(PARENT_OUT, RandomString(8))

    class SettingsEnvDec:
        class general:
            secret: str = "foo"

    # ###########
    class sed_default(SettingsEnvDec):
        pass

    ### Without setting vars
    with silent_output():
        no_env = settingsclass()(sed_default)(randpath())

    assert no_env.general.secret == "foo"
    del sed_default

    ### setting but no prefix, as well as disabled one
    old_values, temp_values = _set_env_values({"GENERAL_SECRET": "bar"})

    class sed_default(SettingsEnvDec):
        pass

    class sed_disabled(SettingsEnvDec):
        pass

    with silent_output():
        no_prefix = settingsclass(env_prefix="")(sed_default)(randpath())
        env_disabled = settingsclass(env_prefix=None)(sed_disabled)(randpath())

    assert no_prefix.general.secret == "bar"
    assert env_disabled.general.secret == "foo"
    _reset_env_values(old_values, temp_values)

    del sed_default
    del sed_disabled

    # Setting w/ prefix
    old_values, temp_values = _set_env_values({"AO_GENERAL_SECRET": "foobar"})

    class sed_default(SettingsEnvDec):
        pass

    class sed_disabled(SettingsEnvDec):
        pass

    class sed_specific(SettingsEnvDec):
        pass

    with silent_output():
        no_prefix = settingsclass(env_prefix="")(sed_default)(randpath())
        env_disabled = settingsclass(env_prefix=None)(sed_disabled)(randpath())
        prefix = settingsclass(env_prefix="AO")(sed_specific)(randpath())
    assert no_prefix.general.secret == "foo"
    assert env_disabled.general.secret == "foo"
    assert prefix.general.secret == "foobar"
    _reset_env_values(old_values, temp_values)

    del sed_default
    del sed_disabled
    del sed_specific


# %%
if __name__ == "__main__":
    pytest.main()
