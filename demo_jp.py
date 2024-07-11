# %% ご挨拶

# このコードは、変数や入出力ファイルを連結する複数のセクションから構成されている
# そのため、オブジェクトの値やファイルの内容を確認しながら、ファイルをセクションごとに実行することをお勧めします。

# %% インポート
from settingsclass import (
    settingsclass,
    Hidden,
    Encrypted,
    RandomFloat,
    RandomInt,
    RandomString,
    set_language,
)

set_language("ja")

# %% 環境の確認

# テストを複数回実行した場合、上書きステップが含まれるため、結果は説明と一致しない。

import os  # noqa

if os.path.exists("config.ini"):
    raise NotImplementedError(
        "ログメッセージが混乱が分かりずらくならないため、既存の config.ini を削除してください"
    )

# %% Define the class

set_language("ja")


@settingsclass
class WebConfig:
    class console:
        # 複数の言語をサポートするための設定
        # 言語コードを文字列として保存される
        # デフォルトでは日本語に設定されている。
        language: str = "ja"
        # => 初期値が「ja」の文字列にされる

        # クラウド上のマシンを一般的なログデータベースで簡単に識別ができると嬉しい
        # そのため、マシンをデプロイする際に設定される短い文字列を追加する
        # 忘れた場合に備えて、4文字の文字列を設定する
        machine_id: RandomString[4] = ""
        # => 4文字の固定長ランダムな文字列

        # Web画面からシステムに重要な情報を操作するためのパスワードが必用
        # これは長い文字列（14～２０文字）で生成初期化する
        # 生成器は、暗号学的安全性を確保するために、Pythonのsecretsライブラリを使用している
        backdoor_password: Encrypted[RandomString[14, 20]] = ""
        # => 14～20文字の暗号化された文字列を生成する
        # ユーザーがマシンごとに使用するカスタムパスワードを作成したい場合は、
        # 希望する値を設定ファイルに編集する。コードが変更後に初めて実行されると
        # 変更後に初めてコードが実行される際、値は暗号化され、元のファイルは
        # 書き換えられる

        # セキュリティレベルが低いエリアでは、4桁の暗証番号で十分である。
        debug_pin: Encrypted[RandomInt[1000, 9999]] = 0
        # => 4桁の整数が生成される

        # コンソールに表示されるメッセージが多すぎると、実行速度が低下する可能性がある。
        # そのため、環境に応じて後で変更できる制限値が設定されている。
        maximum_message_per_second: int = 5
        # => デフォルト値が 5 の整数

        # 環境によっては、コンソール出力に色が付いていると、
        # ANSI エスケープコードが文字コードとして表示されるため、表示テキストが変更されず、
        # 表示されるテキストを変更するのではなく、ANSI エスケープコードが文字コードとして
        # 表示される可能性があるため、これを無効にするオプションが役に立つかもしれない。
        # しかし、このようなケースはまれであるため、このオプションを常に表示しておくと可読性が損なわれる可能性がある。
        colored_output: Hidden[bool] = True
        # => オブジェクトインスタンスは真（True）のブール値を持つが、
        # ディスクに保存されることはない。ディスクから読み込まれたり、ディスクに書き込まれたりするのは、
        # 設定ファイルにセクションと変数がすでに含まれている場合のみ、

    class agent:
        # APIキーは暗号化すべきだが、デフォルト値の設定は不可能なので、
        # 空文字列に設定される。
        api_key: Encrypted[str] = ""
        # => 最初は空文字列のみが保存されるが、INIファイルが変更されると、
        # 暗号化済みの値で上書きされる。

        # いくつかのランダム要素に使用されるシードは、再現性を確保するために設定可能にするべきだが、
        # ただし、それ以外の値であれば何でも構わない。プログラムを再起動した際に再生成する必要はない。
        seed: RandomFloat[0, 12345] = 0
        # => 0 から 12345 までの間のランダムな浮動小数点を生成する


# %%
# デフォルトファイルは作業ディレクトリーの【config.ini】です
config = WebConfig()

# オブジェクト全体を印刷すると、セクションに分割されて表示される
print(f"Complete class:\n{config}")
print("----+++----")

# セクションだけを印刷すると、親クラス名（この場合は WebConfig）も表示されます
# 暗号化されたデータは復号され、表示される
print(config.agent)
print("=====")


# 読み込み時に正しい変数型になっていることを確認する
def foo(x: int):  # ユーザー関数代わり
    print(f"{type(x)}の{x}値")


foo(config.agent.seed)

print("+++++")
# %% 内容を編集して保存する

config.console.machine_id = "TIG1"
config.console.maximum_message_per_second = 1

# これ自体は、メモリ内のオブジェクトのみを変更し、元のファイル自体は変更しない。
# このことは、ファイルを再度読み込むことで確認できる。また、このことは、
# オブジェクト間で値が共有されていないこと、つまり、値が静的ではないことも示している。
config_reloaded = WebConfig()


def check_values(conf_obj) -> str:
    return (
        f"{conf_obj.console.machine_id}; {conf_obj.console.maximum_message_per_second}"
    )


print(
    f"Modified config values = {check_values(config)}\n"
    f"New values: {check_values(config_reloaded)}"
)

# ファイルを保存するには、save_to_file(self, path=None) メソッドを呼び出す。
# path は出力 ini ファイルのパスである。指定されない場合は、読み込まれたファイルのパスが
# 使用される（必ずしも config.ini とは限らない）。
# ただし、関数の動的バインディングのためヒントを示さない場合がある。
config.save_to_file()

# 比較用に、以前のバージョンもディスクに保存しておこう。

config_reloaded.save_to_file("config_bk.ini")

print("**********")

# %% 変数型チェックと強制キャスト

# これはPythonなので、値を設定する際に変数の型はチェックされないが、
# その値をディスクに保存して再読み込みすると問題が発生する可能性がある。

config.agent.seed = "abcd"
config.save_to_file()

# 再読み込む
config = WebConfig()

# 警告メッセージがポップアップし、型をキャストできない旨が表示される。
# % 値を確認すると、新たに生成されたランダム値が設定されていることがわかる。
print(config.agent.seed)

print("-----------")

# %% 警告のみの変数型チェック

# settingsclassは逆のパターンのユーザミスも確認する

config.console.language = 3
config.console.machine_id = False

config.save_to_file()

# 警告メッセージにより、両方の値が文字列として定義されているものの、
# 一方は int のように見え、もう一方は boolean のように見えることが通知される。
config = WebConfig()

# わざとやっている場合は無視しても結構
lang = config.console.language
m_id = config.console.machine_id
print(f"Lang = {lang} of type {type(lang)}")
print(f"Password = {m_id} of type {type(lang)}")

# %%
