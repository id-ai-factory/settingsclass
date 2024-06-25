"""直接、一行ずつテスト
"""

# %% imports

from os.path import join

import pytest

from localizer import tr, refresh_contents, set_language, current_language

xfail = pytest.mark.xfail


# %%


def set_tr_test(file_name):
    """国際化ファイルを【tests/input/loc/<file_name>.csv】に設定する"""
    refresh_contents(join('tests', 'input', 'loc', file_name + '.csv'))


def teardown_module():
    """テストの後に基に戻す"""
    refresh_contents()
    set_language('ja')


# %%
_ = tr('ut_this_key_does_not_exist')


def test_lang_change():
    """言語変更のテスト"""

    set_tr_test('test_strings_correct')
    set_language('ja')
    assert current_language() == 'ja'
    assert tr('ut_parameterless') == "零の引数"

    set_language('en')
    assert current_language() == 'en'
    assert tr('ut_parameterless') == "No params"

    with pytest.raises(
        AttributeError, match=r'指定された言語は存在しません。Requested language does not exist: qx \(可能／avaiable: ja・en\)'
    ):
        set_language('qx')
    assert current_language() == 'en'


def test_parameter_insertion():
    """正しいフォーマットの場合、引数が超どういい、多すぎる、なりないことのテスト"""

    set_tr_test('test_strings_correct')
    set_language('en')
    assert tr('ut_parameterless') == "No params"
    assert tr('ut_parameterless', 1) == "No params"
    assert tr('ut_parameterless', 2, 3, 4) == "No params"

    assert tr('ut_one_param_1') == "The single parameter is {}"
    assert tr('ut_one_param_1', 1) == "The single parameter is 1"
    assert tr('ut_one_param_1', 2, 3, 4) == "The single parameter is 2"

    assert tr('ut_three_param_3') == "The three parameters are {}, {} and {}"
    assert tr('ut_three_param_3', 1) == "The three parameters are 1, {} and {}"
    assert tr('ut_three_param_3', 1, 2) == "The three parameters are 1, 2 and {}"
    assert tr('ut_three_param_3', 2, 3, 4) == "The three parameters are 2, 3 and 4"
    assert tr('ut_three_param_3', 2, 3, 4, 5, 6, 7) == "The three parameters are 2, 3 and 4"

    assert tr('ut_ordered_params_3') == "{} and {} caused {}"
    assert tr('ut_ordered_params_3', 1, 2) == "2 and {} caused 1"
    assert tr('ut_ordered_params_3', 2, 3, 4) == "3 and 4 caused 2"
    assert tr('ut_ordered_params_3', 2, 3, 4, 5, 6) == "3 and 4 caused 2"

    set_language('ja')
    assert tr('ut_ordered_params_3') == "{}のため{}と{}"
    assert tr('ut_ordered_params_3', 1, 2) == "1のため2と{}"
    assert tr('ut_ordered_params_3', 2, 3, 4) == "2のため3と4"
    assert tr('ut_ordered_params_3', 2, 3, 4, 5, 6, 7) == "2のため3と4"


def __this_is_used_by_test_localization_py():
    _ = tr('ut_this_key_does_not_exist')
