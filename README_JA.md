[![Python Tests](https://github.com/id-ai-labo/settingsclass/actions/workflows/tests.yml/badge.svg)](https://github.com/id-ai-labo/settingsclass/actions/workflows/tests.yml)
[![Tests Status](./tests/reports/coverage-badge.svg?dummy=8484744)](./tests/reports/www/index.html)  

# settingsclass  
[dataclass](https://docs.python.org/3/library/dataclasses.html)アプローチに基づく設定オブジェクトとして使用されるクラスの[デコレーター](https://peps.python.org/pep-3129/)。 


# 中心となるアディア
設定を保存するための、使いやすく、かつ機能豊富なソリューション。  
定義と使用方法は [dataclass](https://docs.python.org/3/library/dataclasses.html) と同様ですが、外部【ini】ファイルとの同期や、ランダムな文字列など実行時に生成される値にも対応しています。


# 簡単な運用例

```
from settingsclass import settingsclass, Hidden, Encrypted, RandomString, RandomInt

@settingsclass
class WebConfig:
    class login:
        min_passw_len: int = 12 # 普通のint
        debug_passw: Encrypted[RandomString[16]] = "" # 16文字の暗号化されている文字列を生成する
        console_colored_output: Hidden[bool] = True # 自動でディスクに格納されない

    class agent:
        api_key: Encrypted[str] = "" # ファイルの出力は空文字ながら、ユーザーの入力後暗号化し、上書きされる
        seed: RandomInt[0, 12345] = 0 # 0から12345までの間のランダムな整数を生成する

config = WebConfig("webconfig.ini") # ファイルが存在しない場合は、ファイルが作成される。ファイルが存在する場合は、ファイル内に保存されている値が上記の既定値として使用される

print(config) # 設定ファイル全体を人間が読める形式で表示

def foo(x: int):  # ユーザー関数のプレースホルダ
    print(f"Value {x} with type {type(x)}")

foo(config.agent.seed)  # 変数は【int】型であることが保証されている
config.agent.seed = 11 # 値は通常通り設定でき、値はインスタンス間で共有されない
``` 

*全機能紹介は[こちら](demo.py)*をご覧ください。*

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

3. 環境変数：
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

print文を使用した詳細な使用例シナリオは、[demo.py](demo.py)内に記載されています。

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