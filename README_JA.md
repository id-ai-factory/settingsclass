![image](https://github.com/user-attachments/assets/16ff1e5a-bf35-412c-9dc2-65bc98f9661e)[![Python Tests](https://github.com/id-ai-labo/settingsclass/actions/workflows/tests.yml/badge.svg)](https://github.com/id-ai-labo/settingsclass/actions/workflows/tests.yml)
[![Tests Status](./tests/reports/coverage-badge.svg?dummy=8484744)](./tests/reports/www/index.html)  

# settingsclass  
[English Version](README.md)

使いやすさと豊富な機能を兼ね備えた、Pythonで使用する設定を保存するためのソリューション。

このライブラリは、変数を設定値として扱う独自のカスタムクラスをマークするためのデコレータを提供します。もし以前に[dataclass](https://docs.python.org/3/library/dataclasses.html)を使用したことがあるなら、このライブラリに親しみを感じるでしょう。また、外部のiniファイルとの同期や、[configparser](https://docs.python.org/3/library/configparser.html) バックエンドを使用してiniファイルと同期する設定用のランダム文字列など、実行時に生成される値にも対応しています。


---
 
# クイックスタート・使用例（1/2）
この例では、重要な概念のみを説明しており、説明よりも実際に手を動かして試してみたいという方を対象としている。 
**dataclassやconfigparserについてよく知らない場合や、より詳しい説明を希望する場合は、例2へ進んでください**  

```
from settingsclass import settingsclass, RandomString, RandomInt, RandomFloat, Hidden, Encrypted

@settingsclass
class WebConfig:
    class console:
        language: str = "en"
        machine_id: RandomString[4] = ""
        backdoor_password: Encrypted[RandomString[14, 20]] = ""
        debug_pin: Encrypted[RandomInt[1000, 9999]] = 0
        maxiumum_message_per_second: int = 5
        colored_output: Hidden[bool] = True

    class agent:
        api_key: Encrypted[str] = ""
        seed: RandomFloat[0, 12345] = 0
 
# 「config.ini」に保存または読み込み。カスタムパスも指定可能。
config = WebConfig()

# 型の指定を RandomInt、RandomFloat、RandomString とすると、
# クラスインスタンス化の際、指定された範囲内でプリミティブが生成される
[=] の後のデフォルト値は無視される
m_id = config.console.machine_id 
print(f'{m_id} w/ {type(m_id)}) # <string>型の4文字長さの文字列を出す、例： 4G_b

# インスタンス変数は、Encrypted[type] オブジェクトで型がヒントされるが、 
# エンカプセル化された型を持つオブジェクトを返すが、ディスクに保存する際は暗号化される
dbp = config.console.debug_pin
print(f'{dbp} w/ {type(dbp)}) # 4桁の整数を表示。例：「4521 w/ <class 'int'>」

# config.ini ファイルには、encrypted の値として次のような値が設定される。
# debug_pin = ?ENC22e6de0f80d81f54fbae752d27cd5663e693758554d3520466e7c90423fd3997

# iniファイルに新しいカスタム値を指定することもでき、その値は次にconfig = WebConfig()が呼び出されたときに暗号化される。
# config = WebConfig() が次に呼び出されたときに暗号化される。

# 隠された[型]変数も、カプセル化された型の値を生成し、
# すでに存在していない限り、設定ファイルに保存されたり読み込まれたりすることはない。
co = config.console.colored_output
print(f'{co} w/ {type(co)}) # プリント結果： "True w/ <class 'bool'>"

# --
# すでに存在していない限り、configファイルから# 隠された[]値は保存/読み込まれない
co = config.console.colored_output
print(f'{co} w/ {type(co)}) # プリント結果： "True w/ <class 'bool'>"

# 変更されたインスタンスは任意のパスに保存できる
# デフォルト値は、読み込み元のパスである
# クラスインスタンスを変更する際は、変数の型は強制されない。
# クラスインスタンスの修正時には、ディスクからの読み込み時のみ、
config.agent.seed = "foo"
config.save_to_file("config2.ini")

config2 = WebConfig("config2.ini") # エージェント/シードの型不一致警告を表示する
print(config2.agent.seed) # ランダムな数字、例えば「4281.154」を Float 型で表示
``````
 
# 詳細な使用例 (2/2)

ログイン機能を備えたチャットアプリケーションを開発し、サーバーに導入しようとしているが、環境に応じて設定を変更できるようにしたいとする。Pythonに精通していない人でも理解できる設定ファイルに保存し、そこから読み込むのが理想的だろう。 

### クラス定義
可読性を高めるため、コンソール関連の設定とチャットエージェントの設定の2つのセクションを定義する。 


以下の説明のコードは、[こちら](demo_jp.py)でもご覧いただけます*
<details>
<summary><i>命名規則に関する注記</i></summary>
定義時には<code>class Settings</code>/<code>class Section</code>（大文字）が適切と思われるが、使用時には同じ名前で呼ばれる。したがって、ほとんどの使用時にはオブジェクトとなるため、<code>class Settings</code>/<code>class section</code>（内部小文字）の使用が推奨される。実行時に名前の大文字小文字を変更することも検討したが、特に<code>ClassNamesOfMultipleWords</code> -> <code>class_names_of_multiple_words</code>を使用する場合は、かえって混乱を招くと考えた。
</details>


```
from settingsclass import settingsclass, RandomString, RandomInt, RandomFloat, Hidden, Encrypted, set_language
 
# まずはコンソールの出力言語を日本語に設定しよう
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

```

 
## ディスク入出力と変数タイプ
次に、.ini ファイルと一致させ、後でカスタム値を設定できるようにしたい。 
このケースでは、設定ファイル名は関係ないので、デフォルト値（config.ini）のままにします。

``` 
config = WebConfig()
```

完了！生成されたファイルの内容を確認すると、次のような内容になっている。

```
[console]
language = en
machine_id = b8_Q
backdoor_password = ?ENC5d51bb10d835ff680ce50c99dc512678cb6cb3525d18129a56c7b417c6847339790dbe0cd264ca201a7b82a0dbb4c130
debug_pin = ?ENC7cac31ac5bb2a5a6078d770b17a5a6728766adafa43409a2917b0c09903fcce5
maximum_message_per_second = 5

[agent]
api_key = 
seed = 8881.079
```

`machine_id` はより読みやすいものに変更したい。また、`api_key` は現在空欄なので、config.ini ファイル内の二つの値を変更する。


```
[console]
language = en
machine_id = GIT0
backdoor_password = ?ENC5d51bb10d835ff680ce50c99dc512678cb6cb3525d18129a56c7b417c6847339790dbe0cd264ca201a7b82a0dbb4c130
debug_pin = ?ENC7cac31ac5bb2a5a6078d770b17a5a6728766adafa43409a2917b0c09903fcce5
maximum_message_per_second = 5

[agent]
api_key = super_secret_api_key_556
seed = 8881.079
```

`config = WebConfig()`を再度実行すると、api_key が暗号化されていることが確認できる。すでに暗号化されている値は変更されていない。

```
[console]
language = en
machine_id = GIT0
backdoor_password = ?ENC5d51bb10d835ff680ce50c99dc512678cb6cb3525d18129a56c7b417c6847339790dbe0cd264ca201a7b82a0dbb4c130
debug_pin = ?ENC7cac31ac5bb2a5a6078d770b17a5a6728766adafa43409a2917b0c09903fcce5
maximum_message_per_second = 5

[agent]
api_key = ?ENCd60d7fad60db92ace78261377c629ebad7926916bcae90a4a8aea5a2c296e4f8c7119229d88546374b0ce857fb8e332e
seed = 8881.079
```


クラス全体またはセクションの1つだけを印刷することも可能だ。データは平文形式で復号化されるため、ログ記録時にはデータの取り扱いには注意が必要である。セクションの内容のみを確認したい場合は以下を使う。

```
print(f"Complete class:\n{config}")
print("----+++----")
print(f"A section only:\n{config.agent}")
```

とその結果は：

```
Complete class:
SettingsClass [WebConfig]:
console: 
	language: <str> = en
	machine_id: <RandomString[4]> = YM5W
	backdoor_password: <Encrypted[RandomString[14,20]]> = Qt15Jk0jprCwqFQQs2ob
	debug_pin: <Encrypted[RandomInt[1000,9999]]> = 1516
	maximum_message_per_second: <int> = 5
	colored_output: <Hidden[bool]> = True
 agent: 
	api_key: <Encrypted[str]> = 
	seed: <RandomFloat[0,12345]> = 8796.928
 
----+++----
A section only:
WebConfig section: [agent]
	api_key: <Encrypted[str]> = 
	seed: <RandomFloat[0,12345]> = 8796.928
```

変数型は、単純な型とランダムな値の両方で保証されており、他の変数と同様に扱うことができる。 
以下のコードを実行することで、それを確認しよう。

```
def print_val_and_type(x: int):  # Placeholder for user function
    print(f"{type(x)} 型の値は：{x} ")

print_val_and_type(config.agent.seed)  
```

以上は、浮動小数点型の値とその型を出力します。

`<class 'float'> 型の値は：8796.928`

*浮動小数点の精度は、`RandomFloat[0, 2, precision=5]`という精度パラメータを使用することで設定できる*

### 手動保存

 
シナリオを続けると、管理者がマシンIDを変更できるウェブページがあるとしよう。
プログラムを再起動した後も、同じ値を使用できるようにディスクに保存しておきたい。 
この処理は、`settingsclass` メンバ関数 `save_to_file` を使用して行うことができる。

この例では、管理者が値を TIG1 に変更している。関連するコードは、以下のコードと同じ効果を持つ。

```
config.console.machine_id = "TIG1"
```

上記のコードを実行しても、メモリ内のオブジェクトが変更されるだけで、iniファイルとは自動的に同期されるためsave関数は手動で呼び出す。

```
# 保存する前にバックアップを取る
config.save_to_file("config_bk.ini")

# 元のファイルを上書きする
config.save_to_file()
```


iniファイルとPythonオブジェクトの両方に変更が反映されているはずだ。 
上記のコードが示すように、`save_to_file` はパラメータなしで呼び出すことができ、その場合、元のファイルが上書きされる。

2つのファイルで変更された値を確認しよう。

```
old_value = config.console.machine_id # int型なので、コピーなどは必要ない

# ディスクから際読み込む
config = WebConfig()
verify_value = config.console.machine_id 

# バックアップした値を読み込む
config_bk = WebConfig("config_bk.ini")

# 値を比べる
print(f"メモリー内の値： {old_value}")
print(f"際読み込んだ値： {config.console.machine_id}")
print(f"バックアップの値： {config_bk.console.machine_id}")
```

## タイプチェック

前節では、型ヒントが string 型として指定されている変数に string 型の値を代入した。ここでは、型を誤って int 型として指定されている変数に string 型の値を代入してしまうシナリオを見てみよう。 

```
config.agent.seed = "abcd"
config.save_to_file()
```

Pythonなので、さすがに変数代入時のタイプチェックは行われない。しかし、ディスクから値を読み込む際にはチェックされる。これを確認するために、もう一度ディスクからファイルの内容を読み込んでみよう。

```
config = WebConfig()
```

下記のようなタイプをキャストできないことについて、警告メッセージがポップアップ表示されるはずです。

```
2024-XX-YY HH:MM:SS.MSS | WARNING  | settingsclass.settingsclass:_set_members:753 - 【agent】セクションのパラメータ【seed】に対して、【abcd】をタイプ<class 'float'>に変換できませんでした。
```

実際に設定されている値を確認すると、新しく生成されたランダムな値であることがわかる。

```
print(config.agent.seed)
```

`11392.713`のようなが出力される。

その逆の場合、変数を文字列として暗示しているが、実際にはintを使用するというケースも考えられます。この場合、意図的な可能性があるため、警告が表示されますが、値自体は変更されません。

これをシミュレートするために、以下の値を設定する。実際には、言語をリスト内のインデックスとして定義し、マシンIDを表示または非表示にしたかった。もう1つの可能性は、config.iniファイルで値が表すものを間違えていることである。どちらの場合でも結果は同じであり、以下のコードを実行することで何が起こるかを確認できる。iniファイルで値を変更した場合も、同じことが起こる。


```
config.console.language = 3
config.console.machine_id = False

config.save_to_file()
```

ディスクに保存されたら、警告が表示される。

```
config = WebConfig()

lang = config.console.language
m_id = config.console.machine_id
print(f"Lang = {lang} ；変数型： {type(lang)}")
print(f"Password = {m_id} ；変数型： {type(lang)}")
```

コードの出力は、潜在的な型不一致に関する2つの警告となるが、最終的には変数の型と値は影響を受けない。

2024-XX-YY HH:MM:SS.MSS | DEBUG    | settingsclass.settingsclass:_load_settings_init:635 - 以下のファイルから設定を読み込みます。：config.ini
2024-XX-YY HH:MM:SS.MSS | WARNING  | settingsclass.settingsclass:warn_confusing_types:576 - 設定ファイルの【console】セクション【language】の【3】値を設定されているパラメーターは文字列ですが、intに見えます。
2024-XX-YY HH:MM:SS.MSS | WARNING  | settingsclass.settingsclass:warn_confusing_types:560 - 設定ファイルの【console】セクション【machine_id】の【False】値を設定されているパラメーターは文字列ですが、boolに見えます。
Lang = 3 ；変数型： <class 'str'>
Password = False ；変数型： <class 'str'>

## 詳細設定
特定の使用ケースでは、カスタム暗号化アルゴリズムの使用やRandomFloatの精度の設定など、より高度な設定を使用したい場合がある。[全機能リスト](#full-feature-list)を参照のこと。

# 存在意義


設定ファイルを保存するための最も一般的な推奨方法は以下のとおりですが、それぞれに欠点があります。
1. [configparser](https://docs.python.org/3/library/configparser.html)
    - 基本的な考え方
       - ディスク上の【ini】ファイル内に値を保存します
       - メモリ内に2層構造の辞書のようなオブジェクトを使用します
    - メリット：
        - プログラマーでなくてもシンプルで読みやすい
        - 一般的な【ini】フォーマットから読み取ることができます
        - 変更したバージョンの保存が容易です
    - デメリット:
        - 型ヒントや型チェック機能がありません
        - 存在しない値は【try-except】する必要があります
        - オプション設定や高度な設定には対応していません
        - 暗号化に対応していません
        - IDEからの自動入力補完機能がありません
2. .py ファイル
    - 基本概念
        - データを保存するだけの通常のPythonコードを記述します
    - メリット
        - 型の表示が容易です
        - 追加の計算や処理を組み込むことができます
        - 簡単にインポートできます
    - デメリット
       - プログラミング言語である Python の知識が必要であり、プログラマーでない人には簡単に教えることができません
       - 任意のコードを含めることができるため、非常に安全性が低い 
       - 異なる値を持つバリエーションは手動で保存する必要があります
       - デフォルト値とカスタム値を個別に設定することが困難です
       - 秘密鍵を隠しておくのは難しい場合があります

3. 環境変数
    - 基本概念：
        - デフォルト値はコード内で定義され、カスタム値は環境から読み取られます
    - メリット:
        - コンテナ内で作業する場合、値を簡単に設定できます。
    - デメリット:
        - 開発者でない場合、値の設定が難しい
        - 型ヒントや型チェック機能がありません
        - IDE による自動入力補完機能がありません
        - デバッグが困難です
        - 変数名が他のプログラムと重複する可能性があります。

## 本ライブラリー

- 基本概念：
    - 開発者にとって使いづらい【ini】ファイルでカスタム値を定義した、pythonコード内に定義された設定テンプレート
- 利点：
    - 開発者でもそうでない人でも理解しやすい標準の ini ファイル
    - ユーザー定義のプレフィックスを持つ環境変数のサポート（型キャストも自動的に実行されます）。
    - ファイルの読み込み時に、型がヒントとして表示され、型が強制されます
    - 実行時にランダムに生成された文字列・int・floatをサポート
    - 隠し設定/高度な設定をサポート
    - ユーザーが追加した値やデフォルト値の自動暗号化に対応
    - データクラスバックボーンによるオートコンプリート機能
    - 型の不一致に対する警告 
        - 例えば、var 定義では bool ですが、コードでは「5」となっています。
        - **逆も同様です。例えば、コードでは str ヒントですが、設定では「False」**
    - 変更後の新しいバリアントを簡単に保存できます
    - 任意のコンテンツに対する安全対策（警告メッセージが表示され、代わりにデフォルト値が使用されます）。
    - 基本的に定型文コードは必要ありません
- デメリット:
    - 単一レベルのコンフィギュレーションには対応していません
        - 【config.color】は【config.general.color】または【config.ui.color】などに変換する必要があります）。
    - 初期設定では、ファイル変更の監視をサポートしていません
    -【ini】ファイルのみをサポート（【JSON】サポートは予定されています）

# Requirements
Python 3.11+  
- loguru
- pycryptodome


# 機能一覧と使用例

## Decorator

`@settingsclass(env_prefix: str = "", common_encryption_key: type[str | Callable[[Any], str] | None] = None, salt: bytes = None)`

### ユースケース
1. パラメータなし

クラスの内容は、カレントディレクトリの【congfig.ini】に保存されます。暗号化キーはライブラリのローカルフォルダに保存されます。

```
@settingsclass
class Settings:
    [...]
```
--- 

2. カスタム設定

 
パラメータを指定しない場合、すべてのインスタンスが同じ【webconfig.ini】ファイルを参照します。**フォルダ `my_folder` が指定された場合、クラスは `my_folder/config.ini` を参照します**  
暗号化キーを指定すると、特に指定がない限り、そのクラスをインスタンス化すると、以降のすべてのインスタンスでそのキーが使用されます。
【_salt】パラメータが指定されているため、ファイルを他のマシンにコピーし、「my_encrpytion_key」を使用すると、設定ファイルが正しく読み取られます。


```
@settingsclass(file_path = "webconfig.ini", common_encryption_key = "my_encryption_key", _salt=b'\x87\x14~\x88\xf8\xfd\xb3&\xe2\xd4\xd9|@\xfb\x80\x9e')
class Settings:
    [...]
```
--- 
3. メモリー内
```
@settingsclass(None)
class Settings:
    [...]
```

関数を使うと初期化後でも保存できます。

```
conf = Settings(None)
conf.save_to_file("now_im_ready.ini")

```

## コンストラクタ

### ランダムな文字列
`RandomString[max_length, min_length=-1, /, random_function: Callable = secrets.token_urlsafe]`

指定した長さの間のランダムな文字列を生成します。`max`が指定されていない場合、文字列の長さはminで指定された固定長になります。オプションで、`random_function`を指定することもできます。これは`random_function(max_length)[:true_length]`として呼び出されます。また、直接呼び出してテストすることもできます。例えば、`RandomString(5)`は`Ku_nR`を返します。`secrets.token_urlsafe` を使用します。  
**ユーザーによって指定されたデフォルト値は無視されます。**


### RandomInt[min_value, max_value, /, random_function] / RandomFloat[~]
`RandomInt[min_value: int, max_value: int, random_function: Callable = random.randint]`  
`RandomFloat[min_value: float, max_value: float, random_function: Callable = random.random]` 

2つの限界値の間にある数値を生成します。オプションで、2つの限界値をパラメータとして受け取る関数を指定することができます  
**ユーザーによって指定されたデフォルト値は無視されます**

### Hidden[type]

指定されたパラメータは、指定された場合、ファイルには書き込まれませんが、環境変数と指定したファイルの両方から読み込まれます。  

### Encryted[type]

暗号化は AES128 に基づいています（256 は処理速度が遅く、実用的な利点はありません）。 
デフォルトでは、キーとソルトはランダムに生成され、ライブラリディレクトリ内に保存されます。 IV は暗号化文字列のフィールド内に含まれます。 
これは、オブジェクトごとに `encryption_key` を指定するか、クラス定義レベルで `common_encryption_key` を指定することで上書きできます。
これは文字列またはそのまま呼び出される関数ハンドルです。 
ソルトは環境ごとに生成され保存されるため、ある環境から別の環境に暗号キーをコピー＆ペーストできないようにし、暗号キーの保護にさらなる層を追加します。ディレクトリがユーザー書き込み可能でない環境では、ソルトをバイナリ文字列形式で指定することもできます。クラスごとの指定は想定される使用例ではないため、サポートされていません。   
完全な指定の例は以下の通りです。 


```
@settingsclass(encryption_key="123X456", _salt=b"\x86\xce'?\xbc\x1eA\xd3&\x84\x82\xb4\xa3\x99\x10P")
class Settings:
    class program:
        password: Encrypted[str] = "will be encrypted on save"
    
s = Settings(encryption_key="abcdefgh") # this takes percendence over the encryption_key defined in the decorator
```  

文字列に変換できるあらゆる型をサポートします

## 便利な関数

### 【ini】ファイルからの読み込み
 `update_from(self, config: configparser.ConfigParser, secrets_only: False) -> list[str]`   

configparser ハンドラは、大文字小文字の設定などを含め、ユーザー側で用意する必要があります。暗号化されるべきであったのに暗号化されなかったフィールドの一覧を返します。自動暗号化にはコンストラクタを使用してください。

### iniファイルへの保存
`save_to_file(self, path)`  


 
指定したパスにコンテンツを保存します（暗号化を含む）。

# 完全な例

print文を使用した詳細な使用例シナリオは、[demo_jp.py](demo_jp.py)内に記載されています。

生成された ini ファイルは、以下のようになります。暗号化されている値は異なります。


```
[login]
min_passw_len = 12
backdoor_pint = ?ENCbef0e2e3a58995f50af7b2807a49779ca43cdfc59521a7528222fb4897db0d75

[agent]
api = google.com/api
seed = ?ENC7d2ee77afc4d0c51971adf2fdc853e437a78361a6ba55cfcb20d63d5a6599186
temperature = 0.10883235127062094
```
