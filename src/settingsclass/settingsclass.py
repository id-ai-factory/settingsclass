# -*- coding: utf-8 -*-
"""
Created on Thu May 11 16:54:34 2023

@author: uid7067
"""

# %% Imports
# from __future__ import annotations  # do NOT use! Makes strings become uncallable

from dataclasses import dataclass
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import hashlib
from secrets import token_bytes
import configparser
import random
import secrets
from types import GenericAlias, MethodType, FunctionType
from typing import Any, Callable, TypeVar
import os
from threading import Lock

from loguru import logger

from .localizer import tr
from .localizer import set_language as _set_language


# %%
ENC_PREFIX = "?ENC"
DEFAULT_FLOAT_PRECISION = 3

_key_lock = Lock()

ClassType = TypeVar("ClassType")


def availalbe_languages():
    """Returns the avaiable logging and error message languages"""
    return ("ja", "en")


def set_language(lang: str):
    """Changes the language and error messages

    Args:
        lang (str): Two character code of the language see <avaialbe_languages>
    """
    _set_language(lang)


class KeyfileLocationError(RuntimeError):
    """キーファイルがアクセスできないときに発生する"""


def hash_value(value: str):
    hash = hashlib.sha256()
    hash.update(value.encode("utf-8"))
    return hash.hexdigest()


def _load_key(plain_filename: str, parent_dir: str = None):
    """Loads a key from the specified path. If not parent_dir, the library directory is used"""
    true_filename = hash_value(plain_filename)

    if not parent_dir:
        parent_dir = os.path.dirname(__file__)
    elif not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    full_path = os.path.join(parent_dir, true_filename)

    try:
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, "rb") as f:
                key_content = f.read()
        else:
            key_content = token_bytes(16)
            with open(full_path, "wb") as f:
                f.write(key_content)
    except PermissionError as ex:
        logger.error(error_string := tr("keyfile_location_unaccessable_1", full_path))
        raise PermissionError(error_string) from ex

    return key_content


def _load_guard(key, iv, salt: bytes = None):
    if key:
        hash = hashlib.sha256()
        hash.update(key.encode("utf-8"))
        key = hash.digest()
    with _key_lock:
        if not salt:
            try:
                _load_guard._salt
            except AttributeError:
                _load_guard._salt = _load_key("salty_boy")
            salt = _load_guard._salt

        if not key:
            try:
                _load_key._key
            except AttributeError:
                _load_key._key = _load_key("keygirl")
            key = _load_key._key

    hash = hashlib.sha256()
    hash.update(key)
    hash.update(salt)
    key = hash.digest()[: AES.block_size]
    return AES.new(key, AES.MODE_CFB, iv)


# TODO optimize this
def encrypt_message(message: str, key=None, salt: bytes = None):
    iv = secrets.token_bytes(AES.block_size)
    guard = _load_guard(key, iv, salt)
    message = pad(str(message).encode("utf-8"), AES.block_size)
    return iv + guard.encrypt(message)


def decrypt_message(message: str, key=None, salt: bytes = None):
    iv = message[: AES.block_size]
    guard = _load_guard(key, iv, salt)
    return unpad(guard.decrypt(message[AES.block_size :]), AES.block_size).decode(
        "utf-8"
    )


def _is_encoded(message: str):
    return len(message) > len(ENC_PREFIX) and message[: len(ENC_PREFIX)] == ENC_PREFIX


class _TypeWarpper:
    def __class_getitem__(cls, item):
        # class Secret[Generic]: # req. python>=3.12
        return GenericAlias(cls, item)


class _Encrypted:  # TODO change to expected_type.__origin__
    pass


class _Hidden:  # TODO change to expected_type.__origin__
    pass


class Encrypted(_TypeWarpper, _Encrypted):
    pass


class Hidden(_TypeWarpper, _Hidden):
    pass


class _RandomType:
    def __class_getitem__(cls, item):
        """see __new__ for parameters"""
        return GenericAlias(cls, item)


class RandomString(str, _RandomType):
    def __new__(
        cls,
        min_length,
        max_length=-1,
        *,
        random_function: Callable = secrets.token_urlsafe,
    ):
        """the random function should take one parameter, and return a string at least the length of the stirng"""

        if max_length < min_length:
            min_length, max_length = max_length, min_length

        if min_length <= 0:
            min_length = max_length

        if min_length == max_length:
            true_length = max_length
        else:
            true_length = random.randint(min_length, max_length)

        value = random_function(max_length)[:true_length]

        return str(value)


class RandomInt(int, _RandomType):
    def __new__(
        cls,
        min_value,
        max_value,
        *,
        random_function: Callable = random.randint,
    ):
        return random_function(min_value, max_value)


class RandomFloat(float, _RandomType):
    def __new__(
        cls,
        min_value: float,
        max_value: float,
        precision: int = DEFAULT_FLOAT_PRECISION,
        *,
        random_function: Callable = random.random,
    ):
        if min_value == max_value:
            uncapped_val = super().__new__(cls, min_value)
        uncapped_val = float(random_function() * (max_value - min_value) + min_value)
        if precision >= 0:
            return round(uncapped_val, precision)
        return precision


# note: use lowercase for  subclasses, they will be shadowed by instance values


def _auto_cast_type(
    expected_type: type, config_param_value: str, *, force_random=False
):
    """設定クラスの型ヒントにに合わせる"""

    # ここのラッパーは全てGenericAliasも継承している
    if isinstance(expected_type, GenericAlias):
        # Randomの場合は、そのタイプのクラスにコンストラクタをあげる
        if issubclass(expected_type.__origin__, _RandomType):
            if config_param_value == "" or force_random:
                param_value_after_cast = _init_randomclass(expected_type)
            else:
                param_value_after_cast = expected_type.__base__(config_param_value)

        # HiddenやEncryptedの場合はクラスで定義している値をとる
        elif issubclass(expected_type, _TypeWarpper):
            # 値確認のためキャストする
            param_value_after_cast = _auto_cast_type(
                expected_type.__args__[0], config_param_value, force_random=force_random
            )

        else:
            raise ValueError(
                tr("unexpected_class_found_2", expected_type, config_param_value)
            )

    # コンフィグファイルに値が入っていない場合は型のヒントで初期化する
    elif config_param_value == "":
        param_value_after_cast = expected_type()

    else:
        # boolのサブクラスは定期不可能
        if expected_type == bool and not isinstance(config_param_value, bool):
            # 'FALSE', 'False', 'false'のすべてがFalseにする
            if config_param_value.upper() == "FALSE" or config_param_value == "0":
                param_value_after_cast = False
            elif config_param_value.upper() == "TRUE" or config_param_value == "1":
                param_value_after_cast = True
            else:
                raise ValueError(tr("cannot_convert_to_bool_1", config_param_value))
        else:
            # キャストが失敗したら関数外で対応する
            param_value_after_cast = expected_type(config_param_value)

    return param_value_after_cast


def user_friendly_type_name(typ):
    """Returns <float> instead of __main__.RandomFloat[5] etc."""
    friendly_type = typ
    if issubclass(typ, _TypeWarpper):
        friendly_type = typ.__args__[0]
    elif issubclass(typ.__origin__, _RandomType):
        friendly_type = typ.__base__

    return friendly_type


def _default_value_for_type(typ, default_value_for_primitive):
    """Returns a default value for simple types, but generates one for random types"""
    if issubclass(typ.__origin__, _RandomType):
        return _init_randomclass(typ)
    return default_value_for_primitive


def _init_randomclass(_cls):
    """Returns a possible value for the random value of the appropriate type"""
    return _cls.__origin__(*_cls.__args__)


def _within_random_limits(typ, value):
    """Returns true if the provided value is within the type hint limits"""
    if not issubclass(typ, _RandomType) or isinstance(typ, _RandomType):
        raise TypeError(tr("function_can_only_be_called_on_randomtype_1", typ))
    if not hasattr(typ, "__args__"):
        return True
    if issubclass(typ, RandomString) or issubclass(typ.__origin__, RandomString):
        if len(typ.__args__) == 1:
            return len(value) == typ.__args__[0]
        else:
            return typ.__args__[0] <= len(value) and len(value) <= typ.__args__[1]
    else:
        return value >= typ.__args__[0] and value <= typ.__args__[1]
        # the below matches it to python's random function, but settings-wise including both ends seems more reasonable
        #     return value >= typ.__args__[0] and (
        #     value <= typ.__args__[1] if issubclass(typ.__origin__, RandomInt) else value < typ.__args__[1]
        # )


def _is_hidden_variable(obj, member_name) -> bool:
    """Verifies that the member is not a function, method or a hidden variable"""
    return member_name[:1] == "_" or isinstance(
        getattr(obj, member_name), (MethodType, FunctionType)
    )


def is_settingsclass_instance(obj):
    raise NotImplementedError("まだです")


def __post_init__(self):
    for member_name in self.__dir__():
        if not _is_hidden_variable(self, member_name):
            subclass = getattr(self, member_name)
            subclass_instance = subclass()
            setattr(self, member_name, subclass_instance)
            for var_name, var_type in subclass_instance.__annotations__.items():
                var_value = getattr(subclass_instance, var_name)
                dynamicly_set_val = _auto_cast_type(
                    var_type, var_value, force_random=True
                )
                setattr(subclass_instance, var_name, dynamicly_set_val)


def __subrepr__(self) -> str:
    subclass_instance = self
    subclass_contents = ""
    for varialbe_name, variable_type in subclass_instance.__annotations__.items():
        variable_value = getattr(subclass_instance, varialbe_name)
        subclass_contents += f"\n\t{varialbe_name}: {variable_type} = {variable_value}"  # ({type(variable_value)})"

    return subclass_contents


def __repr__(self) -> str:
    concated_str = f"SettingsClass [{self.__class__.__name__}]:\n"
    for subclass_name in self.__dir__():
        if not _is_hidden_variable(self, subclass_name):
            subclass_instance = getattr(self, subclass_name)

            subclass_contents = __subrepr__(subclass_instance)
            concated_str += f"{subclass_name}: {subclass_contents}\n "
            # TODO finish after shadowing with isntances
    return concated_str


def _encrypt_field(
    message, encryption_key: tuple[Callable, Callable] | str, salt: bytes = None
):
    """Encrpyts the field choosing a method depending on the encrpytion key"""
    if isinstance(encryption_key, tuple):
        message = encryption_key[0](message)
    elif encryption_key is None or isinstance(encryption_key, str):
        message = encrypt_message(message, encryption_key, salt)
    else:
        raise NotImplementedError(
            tr("invalid_encrpytion_key_type_1", type(encryption_key))
        )
    return message


def _decrypt_field(
    message, encryption_key: tuple[Callable, Callable] | str, salt: bytes = None
):
    """Decrpyts the field choosing a method depending on the encrpytion key"""
    if isinstance(encryption_key, tuple):
        message = encryption_key[1](message)
    elif encryption_key is None or isinstance(encryption_key, str):
        message = decrypt_message(message, encryption_key, salt)
    else:
        raise NotImplementedError(
            tr("invalid_encrpytion_key_type_1", type(encryption_key))
        )
    return message


def _safe_decrypt_field(
    message: str,
    parameter_name_debug: str,
    encryption_key: tuple[Callable, Callable] | str,
    salt: bytes,
) -> str:
    """Decrpyts the target field swhile only logging ValueError, UnicodeDecodeError exceptions"""
    true_val = message[len(ENC_PREFIX) :]
    try:
        # Both parts can throus\w Valuerror, the user-facing message is the same
        true_val = bytes.fromhex(true_val)
        message = _decrypt_field(true_val, encryption_key, salt)
    except (ValueError, UnicodeDecodeError):
        logger.error(tr("could_not_decode_string_1", parameter_name_debug))
        message = ""
    return message


def update_config(self, config: configparser.ConfigParser) -> None:
    """Updates the provided config file with the values inside current instance
    The Hidden type variables are not added.
    Encryption is performed for members of type Encrypted

    Args:
        config (configparser.ConfigParser): target configuration object
    """

    for section_name in self.__dir__():
        if not _is_hidden_variable(self, section_name):
            section_instance = getattr(self, section_name)
            if section_name not in config:
                config[section_name] = {}
            for var_name in section_instance.__dir__():
                if var_name[:1] != "_":
                    var_type = section_instance.__annotations__[var_name]
                    is_wrapper_type = isinstance(var_type, GenericAlias)
                    # 乱数等がGenericAliasを使っています
                    # __origin__ はGenericAliasのみ
                    if not is_wrapper_type or (
                        is_wrapper_type and not issubclass(var_type.__origin__, Hidden)
                    ):
                        var_value = getattr(section_instance, var_name)
                        if var_name in config[section_name]:
                            config_val = config[section_name][var_name]
                        else:
                            config_val = ""

                        if var_value and issubclass(var_type, _Encrypted):
                            current_unencrypted_value = None
                            if _is_encoded(config_val):
                                current_unencrypted_value = _safe_decrypt_field(
                                    config_val,
                                    var_name,
                                    self._encryption_key,
                                    self._salt,
                                )
                            if (not current_unencrypted_value) or str(
                                current_unencrypted_value
                            ) != str(var_value):
                                var_value = _encrypt_field(
                                    var_value, self._encryption_key, self._salt
                                )
                                var_value = f"{ENC_PREFIX}{var_value.hex()}"
                            else:
                                var_value = config_val

                        if (
                            var_value
                            and issubclass(var_type, _RandomType)
                            and var_type.__base__ is float
                        ):
                            precision = (
                                DEFAULT_FLOAT_PRECISION
                                if len(var_type.__args__) < 3
                                else var_type.__args__[2]
                            )
                            var_value = f"{var_value:{precision}}"
                        config[section_name][var_name] = str(
                            var_value
                        )  # windowsのconfigクラスは文字列のみ


def update_from(
    self, config: configparser.ConfigParser, ecnrypted_only: False
) -> list[str]:
    """Overwrites current values with values contained in the specified config object

    Args:
        config (configparser.ConfigParser): ConfigParser object.
            User is responsible for population, case-sensitivity settings etc.
        ecnrypted_only (False): Only copies values that are of type Encrpyted

    Returns:
        list[str]: list of values that should have been encrypted in the ConfigParser object
            but were not
    """

    config_file_sections_remaining = [
        section for section in config if section != "DEFAULT"
    ]

    if ecnrypted_only:
        raise NotImplementedError()  # TODO

    # 期待のクラスを反復処理する
    # 例：[('Program', <class ...Settings.Program'), ('GPT', <class ...), ...]
    need_encryption = []
    for section_name, section_class in self.__class__.__dict__.copy().items():
        # dunder(例：'__doc__'）等を除く
        if section_name[:1] != "_" and isinstance(section_class, type):
            # まずはサブクラスを設定する（「Program」等）
            if section_name in config:
                need_enc_subset = _set_members(
                    self,
                    config[section_name],
                    section_class,
                    getattr(self, section_name),
                )
                need_encryption += [
                    f"{section_name}/{varname}" for varname in need_enc_subset
                ]
                config_file_sections_remaining.remove(section_name)
            else:
                logger.warning(tr("missing_config_section_1", section_name))

    if config_file_sections_remaining:
        logger.warning(tr("extra_config_sections_1", config_file_sections_remaining))

    return need_encryption


def save_to_file(self, path):
    """Generates a config file to the specified path.
    If the file does not exist, both parent folders and file will be generated
    """
    config = configparser.ConfigParser(allow_no_value=True)
    return self._save_to_file(path, config)


def _save_to_file(self, path, config):
    self.update_config(config)
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    with open(path, "w", encoding="utf-8") as configfile:
        config.write(configfile)


def warn_confusing_types(value: Any, section_name: str, parameter_name: str) -> None:
    """Checks for types that could be a user input mistake.
    Currently checked types:
    bool:
        if the value is "true", "False", "FALSE" etc, but is marked as :str
    int, float:
        the value can be cast to int of float, but is marked as :str

    Args:
        value (Any): The value of the option
        section_name (str): name of the section in the config file
        parameter_name (str): name of the option insde the config section
    """
    if isinstance(value, str):
        if value.upper() in ("TRUE", "FALSE"):
            logger.warning(
                tr(
                    "param_type_is_string_but_looks_x_4",
                    section_name,
                    parameter_name,
                    value,
                    "bool",
                )
            )
        else:
            for typ in (int, float):
                try:
                    typ(value)
                except ValueError:
                    pass
                else:
                    logger.warning(
                        tr(
                            "param_type_is_string_but_looks_x_4",
                            section_name,
                            parameter_name,
                            value,
                            typ.__name__,
                        )
                    )
                    return


def _load_settings_init(
    self,
    path: str = "config.ini",
    secret_config_path="/run/secrets/flask_settings",
    case_sensitive: bool = False,
) -> None:
    """Loads the settings values after the @dataclass initialization has already taken place

    Args:
        path (str, optional): The file path to read from and write to. Defaults to "config.ini".
        secret_config_path (str, optional): If this file exists, it will be used instead of path.
            See https://docs.docker.com/engine/swarm/secrets/
            Defaults to "/run/secrets/flask_settings".
        case_sensitive (bool, optional): If true section and variable names will be case sensitive
            Defaults to False.

    Raises:
        IsADirectoryError: If the target is a folder AND there is a [config.ini] folder inside

    """

    # flow: <file exists?> YES -> [read file (Config)] -> [Enforce Types (w/ warnings)] -> [Convert to Settings]
    #                      NO  -> [init values (Config)] -> [Enforce Types] (w/out warnigns)]-> [Convert to Settings]

    # メモリーのみの設定
    if not path:
        return

    if secret_config_path and os.path.exists(secret_config_path):
        path = secret_config_path

    config = configparser.ConfigParser(allow_no_value=True)

    # 大文字小文字区別
    if case_sensitive:
        config.optionxform = str

    # 指定されたパスがフォルダーの場合は、ユーザーの意思はおそらくその中に生成することだろう
    if os.path.exists(path) and os.path.isdir(path):
        path = os.path.join(path, "config.ini")

    # 通常、returnやraise後のelseは紛らしいが、この場合ある方が意思を伝える
    # pylint: disable=R1705
    need_encryption = []
    if path_exists := os.path.exists(path):
        if os.path.isfile(path):
            # 通常に存在する場合
            logger.debug(tr("loading_settings_from_1", path))
            config.read(path, encoding="utf-8")
            need_encryption = self.update_from(config, ecnrypted_only=False)
        else:
            # config.iniはフォルダーである可能性はある
            raise IsADirectoryError(tr("file_is_folder_1", path))

    if need_encryption:
        logger.info(tr("unencrypted_data_found_1", need_encryption))
    if need_encryption or not path_exists:
        # 存在しない場合は初期化し、初期化された値を返す
        logger.debug(tr("initing_settings_1", path))
        self._save_to_file(path, config)
    self.update_from_env()

    self._file_path = path


# %%


def _set_param_from_env(
    section_class, section_name, parameter_name, parameter_type, env_prefix
):
    env_prefix = env_prefix.upper()
    environmental_key = f"{env_prefix}{env_prefix and '_'}{section_name.upper()}_{parameter_name.upper()}"
    used_keys = []

    if environmental_key in os.environ:
        env_value = os.environ[environmental_key]
        env_value = _auto_cast_type(parameter_type, env_value)
        setattr(section_class, parameter_name, env_value)

    return used_keys


def update_from_env(self) -> None:
    """環境変数から設定変更を取得する。存在しない場合は設定ファイルから抽出する。

    Args:
        config_section (configparser.SectionProxy): configparserの項目
        parameter_name (str): パラメーター名
            Defaults to None.

    Returns:
        str: 変数の値
    """
    if self._env_prefix is None:
        return

    used_keys = []
    for section_name, section_instance in self.__dict__.items():
        if section_name[:1] != "_":
            # for parameter_name in section_class.__dict__.copy().keys():
            for parameter_name, var_type in section_instance.__annotations__.items():
                if parameter_name[:1] != "_":
                    used_keys += _set_param_from_env(
                        section_instance,
                        section_name,
                        parameter_name,
                        var_type,
                        self._env_prefix,
                    )

    if used_keys:
        logger.info(tr("using_key_var_from_env_1", used_keys))


# pylint: disable=C2801
def _set_members(
    self,
    config_section: configparser.SectionProxy,
    section_class: type,
    section_inst: Any,
):
    # section(項目)をインスタンスにする。クラスだと静的となる
    # 使用されていないパラメーターを見つかるため
    config_section_parameter_names = list(config_section)

    need_encrpytion = []
    # 例：[('lang','ja'),'verbosity','DEBUG')...]
    for (
        parameter_name,
        default_parameter_value,
    ) in section_class.__dict__.copy().items():
        # __dict__, __eq__等をのぞく
        if parameter_name[:1] != "_":
            # コンフィグファイルから読み込んだ値

            expected_type: type = section_class.__annotations__[parameter_name]
            if parameter_name in config_section:
                # 使用されていないパラメーターから削除
                config_section_parameter_names.remove(parameter_name)
                config_param_value = config_section[parameter_name]

                # 例：{'mock_model': bool}
                if parameter_name in section_class.__annotations__:
                    # 設定クラスの型ヒントにに合わせてみる

                    if issubclass(expected_type, _Encrypted):
                        if _is_encoded(config_param_value):
                            config_param_value = _safe_decrypt_field(
                                config_param_value,
                                parameter_name,
                                self._encryption_key,
                                self._salt,
                            )

                        elif config_param_value:
                            need_encrpytion.append(parameter_name)

                    try:
                        param_value_after_cast = _auto_cast_type(
                            expected_type, config_param_value
                        )

                        # キャストが失敗したらValueErrorになる
                    except ValueError:
                        logger.warning(
                            tr(
                                "invalid_type_4",
                                config_section.name,
                                parameter_name,
                                user_friendly_type_name(expected_type),
                                config_param_value,
                            )
                        )
                        # 失敗したらデフォルト値にする

                        param_value_after_cast = _default_value_for_type(
                            expected_type, default_parameter_value
                        )

                else:
                    # 　ヒントがない場合はそのままに残る（str）
                    param_value_after_cast = config_param_value

                section_inst.__setattr__(parameter_name, param_value_after_cast)
                warn_confusing_types(
                    param_value_after_cast, config_section.name, parameter_name
                )

            elif not issubclass(expected_type, _Hidden):
                config_param_value = section_class.__dict__[parameter_name]
                logger.warning(
                    tr("config_param_missing_2", config_section.name, parameter_name)
                )

    # 使用されていないパラメーター確認
    if config_section_parameter_names:
        logger.warning(
            tr(
                "extra_config_parameter_2",
                config_section.name,
                config_section_parameter_names,
            )
        )
    return need_encrpytion


# %%
def _add_settings_layer(
    cls: ClassType,
    env_prefix: str = "",
    common_encryption_key: type[str | tuple[Callable[[Any], str]] | None] = None,
    salt: bytes = None,
) -> ClassType:
    """Dynamically binds the necessary functions after applying the @dataclass decorator.

    Args:
        env_prefix (str, optional): prefix to be attached when checking env vars.
            e.g. if set to foo, in case of config.ui.color the checked name is FOO_UI_COLOR
            No check is performed if set to None.
            Defaults to "", in which case only the section and var names are used,
            e.g config.ui.color -> UI_COLOR
        common_encryption_key (type[str  |  tuple[Callable[[Any], str]]  |  None], optional):
            Key used to encrypt values. If no key is set when using the class constructor,
            this value is used. If you do not wish to use the default encrpyiton method,
            you can also defy a tuple of encrpytion and decryption functions.
            Defaults to None.
        salt (bytes, optional): The salt that is used in combination with the key.
            By default, a random file is generated on the machine, but can be set manually.
            Defaults to None.

    Returns:
        ClassType: Returns the decorated class
    """

    for subclass_name, subclass_proper in cls.__dict__.items():
        if not _is_hidden_variable(cls, subclass_name):
            setattr(cls, subclass_name, dataclass(getattr(cls, subclass_name)))

            def repr_wrapper(_self, subclass_name=subclass_name):
                return f"{cls.__name__} section: [{subclass_name}]{__subrepr__(_self)}"

            subclass_proper.__repr__ = repr_wrapper

    for extra_func in [
        __post_init__,
        __repr__,
        update_config,
        update_from,
        update_from_env,
        save_to_file,
        _save_to_file,
    ]:
        # _set_qualname(cls, extra_func.__name__)
        # extra_func.__qualname__ = f"{cls.__qualname__}.{extra_func.__name__}"  # TODO is this necessary? Interferes with inheritance?
        setattr(cls, extra_func.__name__, extra_func)

    # add wrapper for easier access
    for static_func in (availalbe_languages, set_language):
        setattr(cls, static_func.__name__, staticmethod(static_func))

    cls = dataclass(cls)

    # obj = cls()
    # cls.__new__ = lambda *args, **kwargs: load_settings_self(*args, **kwargs)

    def double_init(
        self,
        *args,
        env_prefix: str = env_prefix,
        encryption_key: type[str | Callable[[Any], str] | None] = None,
        **kwargs,
    ):
        if common_encryption_key and not encryption_key:  # local has priority
            encryption_key = common_encryption_key
        self._encryption_key = encryption_key
        self._salt = salt
        self._env_prefix = env_prefix
        self.original_init()
        _load_settings_init(self, *args, **kwargs)

    cls.original_init = cls.__init__
    # cls.additional_init = load_settings
    cls.__init__ = double_init

    return cls


# placeholder for the wrapper
def settingsclass(
    cls=None,
    /,
    *,
    env_prefix="",
    encryption_key: type[str | Callable[[Any], str] | None] = None,
    _salt: bytes = None,
):
    """Dynamically binds the necessary functions after applying the @dataclass decorator.

    Args:
        env_prefix (str, optional): prefix to be attached when checking env vars.
            e.g. if set to foo, in case of config.ui.color the checked name is FOO_UI_COLOR
            No check is performed if set to None.
            Defaults to "", in which case only the section and var names are used,
            e.g config.ui.color -> UI_COLOR
        encryption_key (type[str  |  Callable[[Any], str]  |  None], optional):
            Key used to encrypt values. Takes priority over decorator setting
            this value is used.If you do not wish to use the default encrpyiton method,
            you can also defy a tuple of encrpytion and decryption functions.
            Defaults to None.
        _salt (bytes, optional): The salt that is used in combination with the key.
            By default, a random file is generated on the machine, but can be set manually.
            Defaults to None.

    Returns:
        ClassType: Returns the decorated class
    """

    # ↓ copied from dataclass
    def wrap(cls):
        return _add_settings_layer(
            cls,
            env_prefix,
            common_encryption_key=encryption_key,
            salt=_salt,
        )

    # See if we're being called as @dataclass or @dataclass().
    if cls is None:
        # We're called with parens.
        return wrap

    # We're called as @dataclass without parens.
    return wrap(cls)


# %%

# TODO add option to enforce limits for Random Types
# TODO add option to be silent - How?
# TODO add option to silence type confusion warnings
# TODO Having the options for JSON etc. would be nice


if __name__ == "__main__":  # pragma: no cover
    # Only for quick testing during development
    @settingsclass  # (encryption_key="123456789")
    class _Settings:
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
            model: str = "gpt-3.5-turbo"  # GPTモデルの識別文字列
            temperature: Hidden[float] = 5
            timeout: int = 300

    conf = _Settings("cx.ini")
    # conf = _Settings(f"conf/{RandomString(5)}.ini")
    print(conf)

# %%
