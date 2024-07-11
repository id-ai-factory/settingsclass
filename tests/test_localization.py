# -*- coding: utf-8 -*-
"""
Created on 2023.05.24

@author: uid7067
"""

# %%
from typing import Generator
from os.path import join, split, isfile, isdir, splitext
from os import listdir
import warnings
import ast
import re as regex

import pytest

from src.settingsclass.localizer import (
    tr,
    refresh_contents,
    current_language,
    set_language,
)

xfail = pytest.mark.xfail

PYFILE_EXCLUSIONS = [
    "conftest.py",
    "test_localization_fail_cases.py",
    "prompt_test_manual.py",
]

# %%


def split_path(path: str):
    """os.path.splitを使ってパスを分分けする
    例：
    【'hoge/foo'】->【'path','foo'】
    【'hoge/foo/'】->【'path','foo'】
    【'/hoge/foo'】->【'/', 'path','foo'】
    【'C:/hoge/foo'】->【'C:/','path','foo'】
    """
    head, tail = split(path)
    return (
        (split_path(head) if split(head)[0] != head else [head]) if head else []
    ) + ([tail] if tail else [])


def filtered_files(
    folder: str,
    extensions: list[str],
    recursive: bool = False,
    exclude: str = None,
) -> list[str]:
    """
    フォルダーのすべてのファイルをリストアップする。

    Args:
        folder (str): 対象フォルダー
        extensions (list[str]): 拡張子のリスト。
            Noneの場合はすべてのファイル対象
            例：画像の場合['png','jpg','bmp']
            例：Pythonファイルの場合：['py']
        exclude: Regexでは省くパス（フォルダー含めて）
        recursive (bool, optional): 大気的有無. Defaults to False.

    Returns:
        list[str]:ファイルパスのリスト
    """
    if isinstance(extensions, str):
        extensions = [extensions]
    if extensions:
        extensions = [e.lower() for e in extensions]

    files = listdir(folder)
    collected_files = []

    for fname in files:
        if exclude and regex.match(exclude, fname):
            continue
        _, ext = splitext(fname)
        full_path = join(folder, fname)
        ext = ext[1:]
        if isfile(full_path) and (extensions is None or ext.lower() in extensions):
            collected_files.append(full_path)
        elif recursive and isdir(full_path):
            collected_files += filtered_files(full_path, extensions, True)

    return collected_files


# %% JSファイル対応

# %% Pyファイル対応


def pyfiles_ast():
    """プロジェクトのすべてのPYファイルをジェネレーターとして返す

    Yields:
        tuple[str, ast.Node]: file_path, root
    """
    try:
        pyfiles_ast.files
    except AttributeError:
        # starts with venv or .venv
        files = filtered_files(".", ["py"], exclude="\.*venv.*", recursive=True)
        files = [fn for fn in files if split_path(fn)[-1] not in PYFILE_EXCLUSIONS]
        pyfiles_ast.files = files

    for file_path in pyfiles_ast.files:
        with open(file_path, encoding="utf-8") as file:
            root = ast.parse(file.read())
        yield file_path, root


def this_file_ast() -> Generator[tuple[str, ast.Module], None, None]:
    """pyfiles_astのフォーマットで、このファイルのみを返す

    Yields:
        tuple[str, ast.Node]: file_path, root
    """
    with open(__file__, encoding="utf-8") as file:
        root = ast.parse(file.read())

    yield __file__, root


def has_tranlsation_call_errors_ast() -> Generator[tuple[str, ast.Module], None, None]:
    """pyfiles_astのフォーマットで、このファイルのみを返す

    Yields:
        tuple[str, ast.Node]: file_path, root
    """
    with open("tests/test_localization_fail_cases.py", encoding="utf-8") as file:
        root = ast.parse(file.read())

    yield __file__, root


def py_get_tr_key_safe(node, file_path) -> str:
    """ast のノードからtr関数の呼び出しかどうかを確認して、可能な場合trの最初の引数の値を返す。"""
    try:
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "tr"
        ):
            tr_call_args = node.args[0]
            # tr('message')ではなく、tr(message)の場合はvalueは存在しません。
            # すべてのパラメータを表示するなどの場合は必要
            if hasattr(tr_call_args, "value"):
                tr_key = tr_call_args.value
                return tr_key
    except Exception as ex:
        print(f"Could parse {file_path} / {node.lineno}")
        raise ex
    return None


def py_tr_calls(
    ast_root_generator: Generator[tuple[str, ast.Module], None, None] = None,
) -> Generator[tuple[str, int, str, int], None, None]:
    """Pyファイルからすべての【tr】関数呼び出しを集まる。

    Args:
        ast_root_generator (Generator[tuple[str, ast.Module], None, None]): プロジェクトファイルのtrをオバーライドするジェネレーター

    Yields:
        Generator[tuple[str, int, str, int], None, None]: 【tr】呼び出しの（ファイルパス、行目、翻訳文字列キー、引数の数）
    """
    if not ast_root_generator:
        ast_root_generator = pyfiles_ast()
    for file_path, root in ast_root_generator:
        for node in ast.walk(root):
            tr_key = py_get_tr_key_safe(node, file_path)
            if tr_key:
                arg_count = len(node.args) - 1
                yield file_path, node.lineno, tr_key, arg_count


# %% JS+Pyを同時に扱う


def tr_calls(ast_iterator=None) -> Generator[tuple[str, int, str, int], None, None]:
    """PythonとJSファイルを両方集めて翻訳呼び出しを返す

    Args:
        ast_iterator (Generator, optional): していされた場合はそのいたれーたのみを使う. Defaults to None.

    Yields:
        tuple[str, int, str, int]: ファイルパス・行目・キーワード・パラメータース数
    """
    if ast_iterator:
        for file_path, lineno, tr_key, arg_count in ast_iterator:
            yield file_path, lineno, tr_key, arg_count

    else:
        for iterator in (py_tr_calls(this_file_ast()), py_tr_calls()):
            for file_path, lineno, tr_key, arg_count in iterator:
                yield file_path, lineno, tr_key, arg_count


# %%　テストの効用関数


@pytest.fixture(autouse=True)
def reset_tr():
    """国際化ファイルを【./loc/loc.csv】に設定する"""
    refresh_contents()


def set_tr_test(file_name):
    """国際化ファイルを【tests/input/loc/<file_name>.csv】に設定する"""
    refresh_contents(join("tests", "input", "loc", file_name + ".csv"))


# %%　フォーマットに関する確認
def test_param_count_in_csv():
    """CSVの翻訳キーのパラメータ数とすべての言語の翻訳内容の｛｝数と一致すること"""
    # パラメータを使っていない場合は、パラメータではない｛｝も許されますが、個々の指定は必要です
    non_functional_bracket_keys = ["enter_program_explanation_example"]

    original_lang = current_language()
    for lang in tr.words.keys():
        set_language(lang)
        for key, value in tr.active_words.items():
            if key in non_functional_bracket_keys:
                continue
            if key[-2] == "_" and key[-1].isdigit():
                expected_count = int(key[-1])
            else:
                expected_count = 0
            open_count = value.count("{")
            close_count = value.count("}")
            assert open_count == close_count, key
            assert open_count == expected_count, key

    set_language(original_lang)


def test_param_count_in_code(
    ast_root_generator: Generator[tuple[str, ast.Module], None, None] = None,
):
    """国際化ファイルにキーに注釈している数と翻訳ストリングにある｛｝の数の確認"""

    for file_path, lineno, tr_key, arg_count in tr_calls(ast_root_generator):
        if isinstance(tr_key, str):
            expected_param_count = int(tr_key[-1]) if tr_key[-2] == "_" else 0
            # print(f'{file_path} Key = {tr_key}, param count = {arg_count}')
            assert expected_param_count == arg_count, tr(
                "param_count_mismatch_2", file_path, lineno
            )


def test_non_existent_key(
    ast_root_generator: Generator[tuple[str, ast.Module], None, None] = None,
):
    """存在しないキーを使っていないことを確認する"""

    transl_key_list = list(tr.active_words.keys())
    for file_path, lineno, tr_key, _ in tr_calls(ast_root_generator):
        if isinstance(tr_key, str):
            assert tr_key in transl_key_list, tr(
                "translation_key_does_not_exist_3", tr_key, file_path, lineno
            )


def test_unused_keys(
    ast_root_generator: Generator[tuple[str, ast.Module], None, None] = None,
):
    """国際化ファイルに使われていないキーのないことを確認する"""

    used_keys = set()
    used_keys = used_keys.union(
        {js_key for _, _, js_key, _ in py_tr_calls(this_file_ast())}
    )

    transl_key_list = list(tr.active_words.keys())

    if not ast_root_generator:
        ast_root_generator = pyfiles_ast()

    for file_path, root in ast_root_generator:
        for node in ast.walk(root):
            tr_key = py_get_tr_key_safe(node, file_path)
            if tr_key:
                used_keys.add(tr_key)
    for key in transl_key_list:
        if key not in used_keys:
            warnings.warn(tr("unused_key_found_1", key), UserWarning)


def test_param_count_test():
    """【test_param_count】関数が、間違ったファイルにエラーを出すことを確認する"""
    set_tr_test("test_strings_warning")
    key_error_pattern = regex.compile(tr("param_count_mismatch_2", r".+", r"\d+"))
    with pytest.raises(AssertionError, match=key_error_pattern):
        test_param_count_in_code(py_tr_calls(has_tranlsation_call_errors_ast()))

    with pytest.raises(AssertionError, match="ut_not_enough_params_2"):
        test_param_count_in_csv()


def test_non_existent_key_test():
    """【test_non_existent_key】関数が、間違ったファイルにエラーを出すことを確認する"""
    set_tr_test("test_strings_warning")
    key_error_pattern = regex.compile(
        tr("translation_key_does_not_exist_3", ".+", ".+", r"\d+")
    )
    with pytest.raises(AssertionError, match=key_error_pattern):
        test_non_existent_key()


def test_unused_test():
    """【test_unused_keys】関数が、間違ったファイルにエラーを出すことを確認する"""
    with pytest.warns(UserWarning, match=tr("unused_key_found_1", "")):
        test_unused_keys(has_tranlsation_call_errors_ast())


def test_no_empty_entries():
    """すべてのキーが翻訳されていることを確認する"""
    for vocab in tr.words.values():
        for translation in vocab.values():
            assert (
                translation and len(translation.replace(" ", "").replace("　", "")) > 0
            )


def test_keycount_equal():
    """すべての言語で同じ言葉の数があることを試す(失敗するはずはないと思う)"""
    prev_lang_vocab = None
    for vocab in tr.words.values():
        if prev_lang_vocab:
            assert len(prev_lang_vocab) == len(vocab)
        prev_lang_vocab = vocab


def test_actual_use():
    """予想外のフォーマットエラーを確認するため、すべての文字列を一回使う"""
    original_lang = current_language()
    for lang in tr.words.keys():
        set_language(lang)
        for key in tr.active_words.keys():
            if key[-2] == "_" and key[-1].isdigit():
                fake_params = list(range(int(key[-1])))
                try:
                    auto_translate = tr(key, *fake_params)
                    manual_translate = (
                        tr.active_words[key].format(*fake_params).replace("\\n", "\n")
                    )
                except Exception as ex:
                    print(f"Failed on/失敗したキーワード： {key}")
                    raise ex
                assert auto_translate == manual_translate, key
                assert len(auto_translate) > 0, key
                assert len(manual_translate) > 0, key
            else:
                assert len(tr(key)) > 0, key
    set_language(original_lang)


# %% インポートの時のエラー確認
# 通常のファイルであるなら、インポートの時に出る。以下はエラーは出すないかを確認する


def test_duplicate_keys():
    """重複がある場合のエラー発生を確認する"""
    with pytest.warns(
        UserWarning,
        match="キーの重複を発見しました。Duplicate key found: ut_duplicate_message",
    ):
        set_tr_test("test_strings_duplicate_key")


def test_incorrect_language_count():
    """コンマ入力間違い場合のエラー発生を確認する"""
    with pytest.raises(
        AssertionError,
        match="言語と文書の数は一致していません。Number of languages and entries does not match for entry: 2/1:key=ut_not_enough_langs",
    ):
        set_tr_test("test_strings_error_few")

    with pytest.raises(
        AssertionError,
        match="言語と文書の数は一致していません。Number of languages and entries does not match for entry: 2/3:key=ut_too_many_langs",
    ):
        set_tr_test("test_strings_error_many")


def test_bad_path():
    """パス入力ミス場合のエラー発生を確認する"""
    with pytest.raises(
        AssertionError,
        match=r"翻訳ファイルは指定されたパスに存在しません。Localization not found at .+THIS_PATH_DOES_NOT_EXIST",
    ):
        set_tr_test("THIS_PATH_DOES_NOT_EXIST")


def test_empty_contents():
    """ファイルに情報がない場合のエラー発生を確認する"""
    with pytest.raises(
        AssertionError,
        match="翻訳ファイルに1つの言語も入っていません。Language file must have at least 1 language in it",
    ):
        set_tr_test("test_strings_error_nostr")


# %%

if __name__ == "__main__":
    pytest.main()

# %%
