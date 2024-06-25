# settingsclass
A decorator for classes to be used as settings objects based on the dataclass approach.

[日本語の説明](REAMDE_JA.md)

# Core idea
An easy-to-use, but feature rich solution to storing settings.   
Defining the class is similar to dataclass, with a few differences.

A more complex example with the full feature list can be found at the end.  
### Simple use-case example:

```
from settings import settingsclass, Hidden, Encrypted, RandomString, RandomInt

@settingsclass
class WebConfig:
    class login:
        min_passw_len: int = 12 # Integer with default value of 12
        debug_passw: Encrypted[RandomString[16]] = "" # Generates a 16 character encrypted string
        console_colored_output: Hidden[bool] = True # The value is not automatically printed 

    class agent:
        api_key: Encrypted[str] = "" # The default value is emptystring, but the user's input is automatically encrypted
        seed: RandomInt[0, 12345] = 0 # Generates a random integer between 0 and 12345

config = WebConfig("webconfig.ini") # if the file does not exist, it is created. Otherwise values stored inside are used over the above defined default values

print(config) # Show the whole config file in a readable format

def foo(x: int):  # Placeholder for user function
    print(f"Value {x} with type {type(x)}")

foo(config.agent.seed)  # the variable is guaranteed to be in int
config.agent.seed = 11 # Values can be set as usual, values are not shared across instances

```

# Why not an existing solution?

The most common recommendations for storing settings file are the following, but each have their disadvantages
1. Using [configparser](https://docs.python.org/3/library/configparser.html)
    - Basic concept
       - Stores values inside an ini file on disk
       - Uses a two-tier dictionary-like object in memory
    - Advantages:
        - Simple and readable even for non-programmers
        - Can be easily read from arbitrary file that matches format
        - Easy to save modified version
    - Disadvantages:
        - Lacks type hinting and type checking
        - Missing values must be try-except-ed
        - No support for optional settings
        - No support for encryption
        - No auto-completion hints from IDE
2. Using a .py file
    - Basic Concept
        - Write normal python code that only has values
    - Advantages
        - Types are easily visible
        - Can include additional calculation or processing
        - Easy to import
    - Disadvantages
       - Requires python knowledge, cannot be easily given to non-programmers
       - Can include arbitrary code, therefore extremely unsafe 
       - Variants with different values need to be saved manually
       - Difficult to have default and custom values separately
       - Keeping secret keys hidden can be challenging

3. Environmental variables:
    - Basic Concept:
        - Default values defined inside code, custom values set read from enviroment
    - Advantages:
        - Easy to set values when working inside containers
    - Disadvantages:
        - Setting values is difficult for non-developers
        - Lacks type hinting and type checking
        - No auto-completion hints from IDE
        - Difficult to debug
        - Variable names may conflict with other programs

## This libary
- Basic Concept:
    - The settings templates defined inside python code, with a non-developer friendly ini file for custom values
- Advantages:
    - Easy-to-understand standard ini file for non-developers and developers alike
    - Types can be hinted and types are enforced when loading files (even from .ini files)
    - Support for randomly generated string, int and float
    - Support hidden/advanced settings
    - Support for automatic encryption of user added or default values
    - Auto-completion support due to dataclass backbone
    - Warnings on type mismatches 
        - e.g. bool in code, but "5" in code 
        - **reverse also true, e.g. str in code but "False" in config**
    - Easy to save new variant, even durind execution time
    - Config file can be hot-swapped or modified during runtime and re-read (file watching is importer's responsibility)
    - Support for environmental variables with user-defined prefix (also type cast automatically)
    - Safe against arbitrary content (warning message is displayed with the default value taking over)
    - Basically no boilerplate

- Disadvantages:
    - No support for single level config (e.g. config.color must be converted to config.general.color or config.ui.color etc.)
    - No support for file watching out-of-the-box
    - Only supports .ini (JSON support planned)



# Requirements
Python 3.11+  
Only standard library dependedncies


# Full Feature list with usage examples


## Decorator

`@dataclass(env_prefix: str = "", common_encryption_key: type[str | Callable[[Any], str] | None] = None, salt: bytes = None)`

Use cases: 
1. No parameters  
The contents of the class are saved under "congfig.ini" in the current directory. Encryption keys are saved in the library's local folder. 
```
@dataclass
class Settings:
    [...]
```
2. Specific arguments  
Without specifying a parameter all instantiations will look at the same webconfig.ini file. **If a folder `my_folder` is specified, the class will look for `my_folder/config.ini`**  
Specifying an encryption key will mean that all subsequent instantiations of the class will use that key unless otherwise specified.
Since the `_salt` parameter is specified, copying the file over to an other machine and using "my_encrpytion_key" will result in a correctly read settings file.
```
@dataclass(file_path = "webconfig.ini", common_encryption_key = "my_encryption_key", _salt=b'\x87\x14~\x88\xf8\xfd\xb3&\xe2\xd4\xd9|@\xfb\x80\x9e')
class Settings:
    [...]
```
3. Ram only settings/user custom file type
```
@dataclass(None)
class Settings:
    [...]
```

The file can also be saved later manually using 
```
conf = Settings(None)
conf.save_to_file("now_im_ready.ini")

```

## Constructor

All arguments of the decorator can also be overriden by the constructor. To avoid accidental setting in regards to encryption, the decorator uses `common_encryption_key` while the constructor uses encryption_key. Other parameters have identical names.


## Variable types

### Random String
`RandomString[max_length, min_length=-1, /, random_function: Callable = secrets.token_urlsafe]`

Generates a random string between the specified lengths. If max is not specified, the  string will have a fixed length equal to the specified min length. Optionally a the `random_function` can also be specified which will be called as `random_function(max_length)[:true_length]`. The types can also be called directly to test them e.g. `RandomString(5)` will return e.g. `Ku_nR`. Uses `secrets.token_urlsafe`  
**The default value sapcified by user is ignored**

### RandomInt[min_value, max_value, /, random_function] / RandomFloat[~]
`RandomInt[min_value: int, max_value: int, random_function: Callable = random.randint]`  
`RandomFloat[min_value: float, max_value: float, random_function: Callable = random.random]`  
Generates a number between the two limits. Optionally a function can be specified, that should accept the two limits as parameters  
**The default value sapcified by user is ignored**

### Hidden[type]

The parameter specified will not be output to the file when specified, but will be read both from environmental variables and the specified files when available.

### Encryted[type]
Encryption is based on AES128 (256 is slower with no practical benefits).  
By default both the key and salt are randomly generated and saved inside the library directory. The IV is included within the encrypted string's field.  　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　
This can be overwritten by specifying the `encryption_key` per object or `common_encryption_key` at the class definition level.
This can be either a string or a funciton handle that will be called as is.   　　
Salt is generated and saved per environment, ensuring that a config file cannot be copy-pasted from one environment to an other, providing an other layer of protection over the key. For enviroments where the directory is not user-writeable the salt can be also be specified in binary string form. Per class specification is not supported, as it is not the intended use-case.    
A full specification example would be:  

```
@settingsclass(encryption_key="123X456", _salt=b"\x86\xce'?\xbc\x1eA\xd3&\x84\x82\xb4\xa3\x99\x10P")
class Settings:
    class program:
        password: Encrypted[str] = "will be encrypted on save"
    
s = Settings(encryption_key="abcdefgh") # this takes percendence over the encryption_key defined in the decorator
```  

Supports any type that can be cast to string

## Useful functions

### Loading from an ini file
 `update_from(self, config: configparser.ConfigParser, secrets_only: False) -> list[str]`  

 configparser handle should be prepared by the user, including case sensitivity settings etc. Returns a list of fields that should have been encrypted but were not

### Saving to an ini file
`save_to_file(self, path)`  
Saves to contents (including encryptino) to the specified path

# Example

A common use case scenario with print statements can be found inside [demo.py](demo.py)

The generated ini file should look similar to the following. Encrypted keys will differ.

```
[login]
min_passw_len = 12
backdoor_pint = ?ENCbef0e2e3a58995f50af7b2807a49779ca43cdfc59521a7528222fb4897db0d75

[agent]
api = google.com/api
seed = ?ENC7d2ee77afc4d0c51971adf2fdc853e437a78361a6ba55cfcb20d63d5a6599186
temperature = 0.10883235127062094
```