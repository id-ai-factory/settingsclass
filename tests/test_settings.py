# -*- coding: utf-8 -*-
"""
Created on 2023.05.24

@author: uid7067
"""

# %%
from shutil import rmtree
import sys
from os.path import join, exists, isdir
from os import makedirs, environ, listdir
from contextlib import contextmanager
import re
from secrets import token_bytes
import platform

from configparser import DuplicateSectionError, DuplicateOptionError
import logging
from mock import patch

import pytest
from loguru import logger
from loguru_caplog import loguru_caplog as caplog  # noqa: F401


from src.settingsclass.settingsclass import (
    settingsclass,
    RandomFloat,
    RandomInt,
    RandomString,
    Encrypted,
    Hidden,
    available_languages,
    _encrypt_field,
    _decrypt_field,
    _load_key,
    encrypt_message,
    decrypt_message,
    _within_random_limits,
    _safe_decrypt_field,
    hash_value,
    MissingSettingsError,
)

from src.settingsclass.settingsclass import set_language as set_language_settings
from src.settingsclass import settingsclass as settingclass_lib
from src.settingsclass.localizer import tr, set_language

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

    class llm:
        api_key: Encrypted[str] = ""
        backup_pin: Encrypted[int] = -1
        timeout = 300
        temperature: Hidden[float] = 5
        versions: list[int] = [35, 40, 50]
        extra: tuple = (5, "x")


@settingsclass(
    encryption_key="987X654", _salt=b"'?\xbc\x1eA\x82\xa3\xb4\xd3&\x84\x99\x10P\x86\xce"
)
class SettingsShort:
    class alpha:
        beta: str = "gamma"
        delta: int = 5
        unchanged: str = "omega"
        unchint: int = 1
        will_be_edited: Encrypted[RandomFloat[0, 2**16]] = 1.2
        should_be_partially_affected: Encrypted[RandomFloat[0, 2**16]] = -1

    class beta:
        beta: str = "not mod"


# %% Test loc wrapper functions


def test_available_languages():
    av_lang = available_languages()
    assert isinstance(av_lang, tuple)
    assert len(av_lang) >= 2


def test_wrapped_set_lang():
    set_language_settings("ja")

    with pytest.raises(TypeError) as ex:
        _within_random_limits(str, "abcde")
    assert (
        ex.value.args[0]
        == "この関数は_RandomTypeのみで呼び出すことができます：<class 'str'>"
    )
    set_language_settings("en")

    with pytest.raises(TypeError) as ex:
        _within_random_limits(str, "abcde")
    assert (
        ex.value.args[0]
        == "This function can only be called on _RandomType: <class 'str'>"
    )


# %% Test internal functions


def hamming_distance(chain1, chain2):
    return sum(c1 != c2 for c1, c2 in zip(chain1, chain2))


def test_hash():
    assert hamming_distance(hash_value("12345"), hash_value("123456")) > 20
    assert len(hash_value("a")) >= 32


def test_safe_decrypt_field_safety(caplog):
    for test_string in [
        ",",
        "123456",
        "?ENCd7d21f6c54087d7b668c4e0d2c9717270d0d8b04114db64dea6262553975b538",
        "?ENCd7d21f6c54087d7b668c4e0d2c9717270d0d8b04114db64dea6262553975b53",
    ]:
        caplog.clear()
        with caplog.at_level(logging.ERROR):
            _safe_decrypt_field(
                test_string,
                parameter_name_debug=(pnd := "test_param_1"),
                encryption_key="123X456",
                salt=b"\x86\xce'?\xbc\x1eA\xd3&\x84\x82\xb4\xa3\x99\x10P",
            )
        assert tr("could_not_decode_string_1", pnd) in caplog.text


def test_random_str():
    for minval, maxval in ((0, 5), (6, 11)):
        vals = []
        for _ in range(1000):
            val = RandomString(minval, maxval) if minval else RandomString(maxval)
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
        vals.add(RandomString(10, 105, random_function=lambda _: "alma"))

    assert vals == {"alma"}


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

    # test precision
    at_least_6_once = False
    for i in range(50):
        rv = RandomFloat(78, 79, precision=-1)
        assert rv >= 78 and rv <= 79 and len(str(rv)) >= 8

        rv = RandomFloat(78, 79, precision=0)
        assert (
            rv >= 78
            and rv <= 79
            and len(sv := str(rv)) == 4
            and sv[-1] == "0"
            and sv[-2] == "."
        )

        rv = RandomFloat(78, 79, precision=3)
        assert rv >= 78 and rv <= 79 and len(sv := str(rv)) <= 6 and sv[2] == "."
        if len(sv) == 6:
            at_least_6_once = True

    assert at_least_6_once

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
        vals.add(RandomInt(-5, 100, random_function=lambda a, b: 92))

    assert vals == {92}


def test_random_float():
    """エラー発生、1000回実行し、全ての値が範囲内にあるかどうかを確認する"""

    for minval, maxval in ((1.3, 4.1), (8, 12)):
        vals = []
        for i in range(1000):
            val = RandomFloat(minval, maxval)
            assert val <= maxval and val >= minval
            vals.append(val)

        # 3分の一に入る値がある
        for v in vals:
            if v < minval + (maxval - minval) / 4:
                break
        else:
            raise AssertionError(tr("lower_third_not_reached"))  # pragma: no cover

        # 上の3分の一に入る値がある
        for v in vals:
            if v > minval + 3 * (maxval - minval) / 4:
                break
        else:
            raise AssertionError(tr("higher_third_not_reached"))  # pragma: no cover

    for _ in range(100):
        x = 1.324
        assert RandomFloat(x, x) == RandomFloat(x, x)

    # パラメータ数
    with pytest.raises(TypeError):
        RandomFloat(5.1)

    # パラメータ型
    with pytest.raises(TypeError):
        RandomFloat("5")

    # 指定された関数を使っていること
    vals = set()
    for _ in range(1000):
        vals.add(RandomFloat(1, 2, random_function=lambda: 92))

    assert vals == {93}

    # 制限の確認
    # 1. 自動
    long_one_found = False
    str_len = 5  # 3 + one digit + decimal point
    for _ in range(1000):
        fv = RandomFloat(1, 2)
        if len(str(fv)) == str_len:
            long_one_found = True
        assert len(str(fv)) <= str_len, fv
    assert long_one_found

    # 2. 固定

    long_one_found = False
    for limit in (0, 1, 4, 5):
        str_len = max(3, limit + 2)  # 3 + one digit + decimal point
        for _ in range(1000):
            fv = RandomFloat(1, 2, limit)
            if len(str(fv)) == str_len:
                long_one_found = True
            cast_len = len(str(fv))
            assert cast_len <= str_len, f"{str(fv)} over the limit of {str_len}"
        assert long_one_found


def test_limit_verification():
    assert _within_random_limits(RandomString[5], "abcde")

    assert _within_random_limits(RandomString, "abcde")
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


# the other variants are tested below
def test_encrypt_field_custom_method():
    original_value = "12345"
    resulting_value = "olikujyhtg"
    encrpytion_functions = (lambda s: resulting_value, lambda s: original_value)
    for salt in (None, 12, "asd", b"asd"):
        resulting_hat = _encrypt_field(
            original_value, encryption_key=encrpytion_functions, salt=salt
        )
        assert resulting_hat == resulting_value

        original_hat = _decrypt_field(
            resulting_hat, encryption_key=encrpytion_functions, salt=salt
        )
        assert original_hat == original_value


# Mock load key to not use any files
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

    assert config.llm.api_key == "sk-123kld-12141"  # dmod
    assert config.llm.backup_pin == 852  # mod

    assert config.llm.temperature == 0.15  # mod
    assert config.llm.timeout == 281
    assert config.llm.versions == [10, 20, 30]  # mod
    assert config.llm.extra == ("abc",)  # mod

    # Validate, that the implied parameter is also printed,
    # and at the correct place
    assert "timeout: <int> = 281" in str(config).split("\n")[-5]


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

    assert config.llm.api_key == ""
    assert config.llm.backup_pin == -1
    assert config.llm.temperature == 5
    assert config.llm.timeout == 300
    assert config.llm.versions == [35, 40, 50]
    assert config.llm.extra == (5, "x")

    # Validate, that the implied parameter is also printed,
    # and at the correct place (2nd from the back + 1x newline)
    assert "timeout: <int> = 300" in str(config).split("\n")[-5]


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


def test_load_key():
    parent = join(PARENT_OUT, RandomString(5), RandomString(4))
    fn1 = RandomString(10)
    fn1_full = join(parent, fn1)
    fn2 = RandomString(10)
    fn2_full = join(parent, fn2)

    key1 = _load_key(fn1, parent_dir=parent)
    assert not exists(fn1_full)  # fn should be hashed
    assert len(key1) >= 16
    key2 = _load_key(fn2_full, parent_dir=parent)
    assert len(key2) >= 16
    assert not exists(fn2)  # fn should be hashed
    assert len(listdir(parent)) == 2

    assert hamming_distance(key1, key2) > 11

    key1_hat = _load_key(fn1, parent_dir=parent)
    assert key1 == key1_hat


def test_create_subdirs():
    parent = join(PARENT_OUT, RandomString(5), RandomString(4))
    assert not exists(parent), "Incorrect test setup"
    with silent_output():
        config = Settings(parent, "xy.ini")
    validate_init_contents(config)


def test_object_not_static():
    with silent_output():
        config1 = Settings(join(PARENT_IN, "config_modified.ini"))
        config2 = Settings(join(PARENT_IN, "config_modified.ini"))
    validate_good_contents(config1)
    validate_good_contents(config2)

    config1.llm.api_key = "aqsd"
    config1.program.seed = 21

    validate_good_contents(config2)

    config2.program.seed = 99
    assert config1.program.seed == 21

    config1.program = None

    assert not config1.program
    assert config2.program.seed == 99


def test_missing_init_value_msg():
    @settingsclass
    class LocalSettingsNone:
        class subc:
            a: str

    # This triggers inside the decorator,
    # but should be understandable without a wrapper
    # @settingsclass
    # class LocalSettingsLast:
    #     class subc:
    #         a: str = "asd"
    #         b: str

    @settingsclass
    class LocalSettingsFirst:
        class subc:
            t: str
            z: str = "2"

    missing_pn_error_pattern = re.compile(
        tr("no_initial_value_3", "LocalSettingsNone", "subc", "a")
    )

    with pytest.raises(MissingSettingsError, match=missing_pn_error_pattern):
        _ = LocalSettingsNone(join(PARENT_OUT, "pl.ini"))

    missing_pn_error_pattern = re.compile(
        tr("no_initial_value_3", "LocalSettingsFirst", "subc", "t")
    )
    with pytest.raises(MissingSettingsError):
        _ = LocalSettingsFirst(join(PARENT_OUT, "plpl.ini"))


def test_invalid_list_hint_msg():
    @settingsclass
    class LocalSettingsTooMany:
        class subc:
            too_many: tuple[int, str] = [1, "a"]

    too_many_error_pattern = re.escape(
        tr("iterable_class_annotation_too_many_1", "tuple[int, str]")
    )
    with pytest.raises(ValueError, match=too_many_error_pattern):
        _ = LocalSettingsTooMany(join(PARENT_OUT, "list_hint_many.ini"))

    @settingsclass
    class LocalSettingsTooMany:
        class subc:
            too_many: tuple[()] = [1, "a"]

    too_few_error_pattern = re.escape(
        tr("iterable_class_annotation_too_few_1", "tuple[()]")
    )
    with pytest.raises(ValueError, match=too_few_error_pattern):
        _ = LocalSettingsTooMany(join(PARENT_OUT, "list_hint_few.ini"))


def test_unsupported_types():
    @settingsclass
    class LocalSettingsDictType:
        class subc:
            too_many: dict[int, str] = {1: "a"}

    dictionary_type = re.escape(
        tr("dictionary_not_supported_2", "{1: 'a'}", "dict[int, str]")
    )
    with pytest.raises(ValueError, match=dictionary_type):
        _ = LocalSettingsDictType(join(PARENT_OUT, "dict_type.ini"))

    @settingsclass
    class LocalSettingsUnknownType:
        class subc:
            too_many: set[int] = {1, 2}

    dictionary_type = re.escape(tr("unexpected_class_found_2", "set[int]", "{1, 2}"))
    with pytest.raises(ValueError, match=dictionary_type):
        _ = LocalSettingsUnknownType(join(PARENT_OUT, "unknown_type.ini"))


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
    assert exists(ini_dir) and isdir(ini_dir), (
        f"Test setup is incorrect, {ini_dir} should be a directory"
    )

    # path <- config.ini/config.ini、最初はフォルダー

    with silent_output():
        config = Settings(ini_dir)
    validate_good_contents(config)

    # path <- config.iniのフォルダー
    with pytest.raises(IsADirectoryError), silent_output():
        config = Settings(PARENT_IN)


def test_unaccessible_location():
    if platform.system() == "Windows":
        with pytest.raises(PermissionError):
            _ = _load_key("kf.kf", f"{RandomString(10)}:\\")


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


def test_settings_overwrite():
    backup_path = join(PARENT_OUT, "config_mutable_bk.ini")
    modified_path = join(PARENT_OUT, "config_mutable.ini")

    with silent_output():
        config = SettingsShort(modified_path)

    config.save_to_file(backup_path)
    # edit
    config.alpha.beta = "modified string"
    config.alpha.delta = 1234
    config.alpha.will_be_edited = 33.24

    config.save_to_file()

    # check files
    original = SettingsShort(backup_path)
    modified = SettingsShort(modified_path)

    # unmodified bits
    assert original.alpha.unchanged == modified.alpha.unchanged
    assert original.alpha.unchint == modified.alpha.unchint
    assert (
        original.alpha.should_be_partially_affected
        == modified.alpha.should_be_partially_affected
    )
    assert original.beta.beta == modified.beta.beta

    # modified bits
    assert (
        original.alpha.beta != modified.alpha.beta
        and modified.alpha.beta == "modified string"
    )
    assert original.alpha.delta != modified.alpha.delta and modified.alpha.delta == 1234
    assert (
        original.alpha.will_be_edited != modified.alpha.will_be_edited
        and modified.alpha.will_be_edited == 33.24
    )

    # with open(backup_path, encoding="utf-8") as original, open(modified_path, encoding="utf-8") as modified:

    assert config


def test_missing_section_and_variable(caplog):  # noqa: F811
    """存在しない項目やパラメータがあるの時の警告発生の確認"""

    # 1回目で生成して、保存されていないため２回実行する、最初のログは無視する
    for _ in range(2):
        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            _ = Settings(join(PARENT_IN, "config_missing_section.ini"))

    # エラーがある場合、まずはエラーメッセージ内容、引数などが変わっていないことを確認して下さい
    assert tr("missing_config_section_1", "llm") in caplog.text
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
            "llm",
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
        tr("invalid_type_5", "program", "colored_console_output", bool, "Igen", True)
        in caplog.text
    )
    assert (
        tr("invalid_type_5", "program", "rfph", float, "alma", config.program.rfph)
        in caplog.text
    )
    assert (
        tr("invalid_type_5", "program", "api_id", int, "bar", config.program.api_id)
        in caplog.text
    )
    assert tr("json_decode_failed_3", '("abc","a")', tuple, "(5, 'x')") in caplog.text

    api_id = config.program.api_id
    assert api_id >= 1000 and api_id <= 9999

    rf = config.program.rfph
    assert rf >= 0 and rf <= 2**16

    assert config.program.colored_console_output

    assert config.llm.versions == [35, 40, 50]
    assert config.llm.extra == (5, "x")


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
        tr("param_type_is_string_but_looks_x_4", "llm", "api_key", 3.0, "float")
        in caplog.text
    )


def test_need_encryption(caplog):
    with (
        open(join(PARENT_IN, "config_generated_good_half_enc.ini"), "rb") as f,
        open(copied_file := join(PARENT_OUT, "cgghe.ini"), "wb") as g,
    ):
        g.write(f.read())
    caplog.clear()
    with caplog.at_level(logging.INFO):
        _ = Settings(copied_file)
    assert tr("unencrypted_data_found_1", "['llm/backup_pin']") in caplog.text


# %% ENV check
def _set_env_values(
    new_values_dict: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    old_values = {}
    values_to_remove = []
    # no cover note -- the clause is only triggered if the key already exists in the env
    # This is added as a safety measure to not mess up the original python env that runs it
    for key, value in new_values_dict.items():
        if key in environ:  # pragma: no cover
            old_values[key] = environ[key]
        else:
            values_to_remove.append(key)
        environ[key] = str(value)

    return old_values, values_to_remove


def _reset_env_values(old_values: dict[str, str], values_to_remove: list[str]) -> None:
    for key, value in old_values.items():
        environ[key] = str(value)  # pragma: no cover

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
        env_prefix = f"{prefix}{prefix and '_'}"

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
                f"{env_prefix}LLM_API_KEY": "sk-123kld-12141",
                f"{env_prefix}LLM_BACKUP_PIN": 852,
                f"{env_prefix}LLM_TEMPERATURE": 0.15,
                f"{env_prefix}LLM_TIMEOUT": 281,
                f"{env_prefix}LLM_VERSIONS": [10, 20, 30],
                f"{env_prefix}LLM_EXTRA": '["abc"]',
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
    pytest.main()  # pragma: no cover
