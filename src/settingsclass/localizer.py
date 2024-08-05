# -*- coding: utf-8 -*-
"""
Created on Fri Apr  8 10:50:50 2022

@author: uid7067
"""

# 翻訳に関する関数
from os import listdir
from os.path import join, exists, isdir, splitext, dirname
from collections import OrderedDict
import csv
import warnings
import re

DEFAULT_EXTENSIONS = ["csv"]
DEFAULT_FOLDER = join(dirname(__file__), "loc")


def _has_parameters(key):
    """翻訳キーがパラメータを望むかどうか"""
    return key[-2] in ("_", "＿") and key[-1].isdigit()


# 早い入力のためC0103（関数名が短い）をこの関数に未効果する
def tr(key: str, *params) -> str:  # pylint: disable=C0103
    """ストリングを翻訳し、パラメーターを入れる。
    フォーマットは<要約>_<任意：引数数>。
    例：tr('webpage_title')
    例：tr(invalid_path_1, '/usr/xyz')
    例：tr(bad_request_3, request_type, request_id, request_content)

    キーが存在しない場合はそのまま使用する。引数の数を指定する場合は自動で追加される
    例：tr('does_not_exits_3',x,y,z) => 'does_not_exist_{}_{}_{}'

    パラメーター数が一致していない場合はできる範囲で入れる：
    例：tr('triplet_conf_invalid_3, 135) => 'Triplet configuration invalid: 135 - {} - {}'
    例：tr('invalid_path_1', 'usr/loc', 'Username') => 'Invalid path supplied <usr/loc>'

    Args:
        key (str): loc.csvの文字列ID。
        params: keyに差し替えるパラメータ

    Returns:
        str: 翻訳された文字列
    """

    formatted_string = ""

    # tr.active_words：現在の言語の{id: 翻訳された文字列}の辞書
    if key in tr.active_words:
        entry = tr.active_words[key]
    else:
        # 入っていない場合は[_count]の程の｛｝を追加する
        # _は半角でも全角でもOK
        if _has_parameters(key):
            entry = key[:-1] + "_".join(["{}"] * int(key[-1]))
        else:
            entry = key

    entry = entry.replace("\\n", "\n")
    if not _has_parameters(key):
        return entry

    try:
        formatted_string = entry.format(*params)
    except IndexError:
        # 引数の数が一致していない場合は発生する
        param_list = list(params)
        # 「{{」等でエスケープされたとしても上限は【｛】の数です
        # 多すぎるの場合はエラーが発生しない
        bracket_count = entry.count("{")
        param_list += ["{}"] * (bracket_count - len(param_list))
        formatted_string = entry.format(*param_list)
    except ValueError:
        # 団体テストを実行しなった場合の安全装置
        # 例：value=="{1}の{0}=={}"
        formatted_string = re.sub(r"\{\d+\}", "{}", entry)
        formatted_string = formatted_string.format(*params)

    return formatted_string


def current_language() -> str:
    """現在の言語コードを返す"""
    try:
        return tr.current_lang
    except AttributeError:
        return None


def set_language(language: str) -> None:
    """言語を設定する。プロパティが精定期であるため、実行は初期化と言語変更のときのみ必要。

    Args:
        language (str): 国際化ファイルにある言語のコード（"ja", "en"等）

    Raises:
        AttributeError: _description_
    """

    # "ja" == "JA" == "Ja"
    language = language.lower()
    if language in tr.words:
        tr.active_words = tr.words[language]
        tr.current_lang = language
    else:
        raise AttributeError(
            "指定された言語は存在しません。Requested language does not exist: "
            + f"{language} (可能／available: {'・'.join(list(tr.words.keys()))})"
        )


def _listup_files(
    folder: str = DEFAULT_FOLDER, extensions: list[str] = None, recursive: bool = False
) -> list[str]:
    """
    フォルダーのすべてのファイルをリストアップする。(utils.pyにもありますが循環参照回避のため自作)

    Args:
        folder (str): 対象フォルダー
        extensions (list[str]): 拡張子のリスト。
            Noneの場合はすべてのファイル対象
            例：画像の場合['png','jpg','bmp']
            例：Pythonファイルの場合：['py']
        recursive (bool, optional): 大気的有無. Defaults to False.

    Returns:
        list[str]:ファイルパスのリスト
    """
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS
    if extensions:
        extensions = [e.lower() for e in extensions]
    files = listdir(folder)
    collected_files = []

    for fname in files:
        _, ext = splitext(fname)
        full_path = join(folder, fname)
        ext = ext[1:]
        if extensions is None or ext.lower() in extensions:
            collected_files.append(full_path)

        if recursive and isdir(join(folder, fname)):
            collected_files += _listup_files(join(folder, fname), extensions, True)
    return collected_files


def _load_translations(langfile_directory: list[str] = None):
    if langfile_directory is None:
        langfile_directory = _listup_files()
    words = OrderedDict()
    langs = []
    for langfile_path in langfile_directory:
        with open(langfile_path, encoding="utf-8") as lang_file:
            lang_reader = csv.reader(lang_file, delimiter=",", quotechar='"')
            for row in lang_reader:
                if row and not (
                    len(row) >= 1 and len(row[0]) >= 1 and row[0][0] in ("#", "＃")
                ):
                    # 　最初の行は言語の定義
                    if not words:
                        assert (
                            len(row) > 1
                        ), "翻訳ファイルに1つの言語も入っていません。Language file must have at least 1 language in it"
                        # "ja" == "JA" == "Ja"
                        langs = [lang.lower() for lang in row[1:]]
                        for lang in langs:
                            words[lang] = {}
                    else:
                        # 「,」等の数がずれたら全翻訳ファイルが読めなくなるかもしれせんのでこれがエラーとする
                        assert len(row) - 1 == len(langs), (
                            "言語と文書の数は一致していません。Number of languages and entries does not match for entry: "
                            + f"{len(langs)}/{len(row)-1}:key={row[0]} in file {langfile_path}"
                        )
                        key = row[0]
                        for lang_id, entry in enumerate(row[1:]):
                            ## 1行目の言語設定が重複するのでスキップする
                            if key != "id":
                                lang = langs[lang_id]
                                if key in words[lang]:
                                    warnings.warn(
                                        f"キーの重複を発見しました。Duplicate key found: {key}",
                                        UserWarning,
                                    )
                                words[lang][key] = entry
    return words, langs


def refresh_contents(file_path: list[str] = None):
    """格納されたファイルから内容を読み込む。インポートの時に一回実行される"""
    ## 指定がない場合はlocフォルダの.csvをすべて読み込む
    if file_path is None:
        file_path = _listup_files()
    ## 指定があった場合は指定のファイルを読み込む
    ## listで扱うのでlist担っていない場合は変換する。
    if not isinstance(file_path, list):
        file_path = [file_path]
    # ディレクトリのファイルチェック
    for langfile_path in file_path:
        assert exists(
            langfile_path
        ), f"翻訳ファイルは指定されたパスに存在しません。Localization not found at {langfile_path}"
    tr.words, langs = _load_translations(file_path)

    # 最初の言語はデフォルトとする
    try:
        selected_language = tr.current_lang
    except AttributeError:
        selected_language = langs[-1]
        tr.current_lang = selected_language
    set_language(selected_language)


refresh_contents()
