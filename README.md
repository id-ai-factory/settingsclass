[![Python Tests](https://github.com/id-ai-labo/settingsclass/actions/workflows/tests.yml/badge.svg)](https://github.com/id-ai-labo/settingsclass/actions/workflows/tests.yml)
[![Tests Status](./tests/reports/coverage-badge.svg?dummy=8484744)](./tests/reports/www/index.html)  


# settingsclass  

[日本語の説明](README_JA.md)

An easy-to-use but feature-rich solution to storing settings in python.   

This library provides a decorator to mark your own custom classes, where variables become setting values. If you have used [dataclass](https://docs.python.org/3/library/dataclasses.html) before, this library should feel familiar. It also includes synchronization with an external ini file and support for runtime-generated values, e.g. random strings for synchronizing settings with an ini file using a [configparser](https://docs.python.org/3/library/configparser.html) backend.   

Developed by [ID AI Factory Co., Ltd.](https://www.ai-factory.co.jp)

---

# Quick-start example (1/2)
In this example only key concepts are presented and assumes you like tinkering more than explanations.  
**If you are unfamiliar with dataclass or configparser, or would like a more detailed explanation skip to example 2**

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

# Save to or read from "config.ini". Custom path can also be passed
config = WebConfig()

# Hinting a type as RandomInt, RandomFloat and RandomString will generate
# will cause the class instantiation to generate a primitive within specified limits
# The default value after [=] is ignored
m_id = config.console.machine_id 
print(f'{m_id} w/ {type(m_id)}) # prints a four character <string> e.g. 4G_b

# Instance variables type hinted with Encrypted[type] return objects of their 
# encapsulated types, but are encrypted when saving to disk
dbp = config.console.debug_pin
print(f'{dbp} w/ {type(dbp)}) # prints a 4 digit int e.g. "4521 w/ <class 'int'>"

# The config.ini file will have the value encrypted similar to:
# debug_pin = ?ENC22e6de0f80d81f54fbae752d27cd5663e693758554d3520466e7c90423fd3997

# A new custom value can also be specified in the ini file, it is encrypted the
# next time config = WebConfig() is called


# Hidden[type] variable also generate values of their encapsulated types,
# and are not saved/read from  the config file, unless already present
co = config.console.colored_output
print(f'{co} w/ {type(co)}) # prints "True w/ <class 'bool'>"

# ---
# Modified instances can be saved to an arbitrary path
# The default value is the path it was read from
# Variable types are not enforced when modifying  the class instance, 
# only when reading from disk. It is python after all
config.agent.seed = "foo"
config.save_to_file("config2.ini")

config2 = WebConfig("config2.ini") # prints a type mismatch warning for agent/seed
print(config2.agent.seed) # prints a random number e.g. "4281.154" with type Float

```

# Detailed Use-Case Example (2/2)

Let's say you are developing a chat application with login that will be deployed on a server and wish to have some settings that can be set depending on the environment. Saving and reading to a configuration file that non-python experts can also understand is most likely ideal.  

### Class definition
To improve readability, we will define two sections: one for console-related settings and one to set the chat agent.  


*The code for the explanation below can also be found [here](demo.py)*
<details>
<summary><i>A note on naming convention</i></summary>
The appropriate choice during definition seems to be <code>class Settings</code>/<code>class Section</code> (with a capital), however in during usage it will be called under the same name. Hence, it is an object during most of its usage, therefore the suggested usage is <code>class Settings</code>/<code>class section</code> (internal lowercase). I did consider changing the case of the name during runtime, but I decided that that would be more confusing, especially when using <code>ClassNamesOfMultipleWords</code> -> <code>class_names_of_multiple_words</code>
</details>


```
from settingsclass import settingsclass, RandomString, RandomInt, RandomFloat, Hidden, Encrypted

@settingsclass
class WebConfig:
    class console:
        # We would like to support multiple languages.
        # This uses language codes, as such it will be stored as a string
        # By default it should be english
        language: str = "en"
        # =>  A string value with the default value of "en" will be initialized

        # We also want our machine in the cloud to be easily identifiable in the common log db
        # Therefore, we add a short string that is set when deploying the machine
        # In case it is forgotten, it will be set to a 4 character string 
        machine_id: RandomString[4] = ""
        # => A random string with a fixed length of 4 characters

        # We would like to enable admin access for system-critical information
        # This should be a long password (14~20 characters)
        # The generator uses python's secrets library to ensure that it is cryptographically safe
        backdoor_password: Encrypted[RandomString[14, 20]] = ""
        # => Generates a 14 to 20 character encrypted string
        # If the user wants to prepare a custom password to be used per-machine,
        # they can edit the config file with the desired value. When the code is run 
        # for the first time after modification, the value is encrypted, and the original file
        # is overwritten

        # For low-security areas, a quick access 4 digit pin will suffice
        debug_pin: Encrypted[RandomInt[1000, 9999]] = 0
        # => Generates a 4 digit integer

        # Having too many messages printed to console can cause slow down execution,
        # therefore a limit is set, that may be modified later based on the environment
        maximum_message_per_second: int = 5
        # => an integer with a default value of 5

        # Depending on the environment, having colored console output may result in
        # seeing the ANSI escape codes to be shown as character codes instead of modifying
        # the displayed text, so an option to turn it off may be useful.
        # This is rarely the case however, so having this option always visible may hinder readability
        colored_output: Hidden[bool] = True
        # => The object instance will have a boolean instance of True, but it is not 
        # saved to disk. It is only read from or written to disk, 
        # if the config file already contained the section and variable 

    class agent:
        # The API key should be encrypted, but there is no possible default value, 
        # so it is set to emptystring
        api_key: Encrypted[str] = ""
        # => only an emptystring is saved at first, but when the ini file is modified,
        # it will be overwritten with the encrypted value

        # The seed to be used for some random elements should be settable for reproducibility,
        # but otherwise any value is acceptable. It does not need to be regenerated on program restart
        seed: RandomFloat[0, 12345] = 0
        # => Generates a random float between 0 and 12345
```


## Disk I/O and variable types
Next, we want to match it with a .ini file, so that we can set custom values later.  
The config file name is not relevant in this instance, so we will leave it at the default value (config.ini).

``` 
config = WebConfig()
```
Done! If we check the contents of the generated file, it will be similar to this:

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

We would like the to have a more easily readable `machine_id`, and the `api_key` is empty at the moment, so we modify the two values in the config.ini file.

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

If we re-run `config = WebConfig()`, we can observe that our api_key has been encrypted. The already encrypted values have not changed.

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

We can also print the whole class, or a one of the sections. The data will be decrypted in plain text form, therefore care needs to be taken data during logging. If we would only like to see the contents of a section we can use

```
print(f"Complete class:\n{config}")
print("----+++----")
print(f"A section only:\n{config.agent}")
```

which will result in 
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

The variable type is guaranteed for both simple types and randomized values and can be treated like any other variable.  
We can check that by executing the following code.

```
def print_val_and_type(x: int):  # Placeholder for user function
    print(f"Value {x} with type {type(x)}")

print_val_and_type(config.agent.seed)  
```

This should print a float value followed by the confirmed float type.

`Value 8881.079 with type <class 'float'>`

*The precision of the floats can be set by using the precision parameter `RandomFloat[0, 2, precision=5]`*

### Manual saving

Continuing the scenario, let's say that we have a webpage where the admin can change the machine id. 
We would like to save to disk as to use the same value after the program restarts.  
We can do this using the `settingsclass` member function `save_to_file`.

For this example, the admin has changed the value to TIG1. The relevant code would have the same affect as below:
```
config.console.machine_id = "TIG1"
```

Executing the code above only modifies the object in memory, it is not automatically synced with the ini file. The save function needs to be called manually.

```
# Make a backup file before overwriting
config.save_to_file("config_bk.ini")

# Overwrite the original file
config.save_to_file()
``` 

Both the ini file and the python object should reflect our change.  
As the above code demonstrates `save_to_file` can be called without a parameter, in which case the original file will be overwritten.

Let's check the changed values between the two files:
```
old_value = config.console.machine_id # int, therefore copy etc. is not needed

# re-read from disk
config = WebConfig()
verify_value = config.console.machine_id 

# read the backup value
config_bk = WebConfig("config_bk.ini")

# print the 3 values
print(f"Memory = {old_value}")
print(f"Re-read = {config.console.machine_id}")
print(f"Backup = {config_bk.console.machine_id}")
```

## Type checking

In the previous section we have set a string value to a variable that has been type hinted as string. Let's see a scenario, where the type is accidentally mistaken and a string value is set to a variable that has been type hinted as int.  
```
config.agent.seed = "abcd"
config.save_to_file()
```

Since this is python, type checks are not performed on variable assignments. They are, however, checked when reading the values from disk. To verify this, we will read the file contents once again from disk.
```
config = WebConfig()
```

A warning message should pop up with about not being able to cast the type along the following lines.
```
2024-XX-YY HH:MM:SS.MSS | WARNING  | settingsclass.settingsclass:_set_members:753 - Could not convert <abcd> to type <class 'float'> for parameter <seed> in section <agent>
```

If we check the value that is actually set, we can see that it is a newly generated random value.
```
print(config.agent.seed)
```
This will output e.g. `11392.713`

The opposite case, type hinting a variable as a string, but meaning to use an int is also a possibility. Since in this case, it is possible that it is intentional, a warning is shown, but the value itself is not changed.

To simulate this, we set the following to values. We actually wanted to define language as an index in the list of available languages and have the machine id shown or hidden. An other possibility is the one modifying the config.ini file has mistaken what the values represent. The result is the same in both cases and we can see what happens by running the following code. The same would happen if we modified the values in the ini file.

```
config.console.language = 3
config.console.machine_id = False

config.save_to_file()
```

To trigger the warning, we read the file from disk. 
```
config = WebConfig()

lang = config.console.language
m_id = config.console.machine_id
print(f"Lang = {lang} of type {type(lang)}")
print(f"Password = {m_id} of type {type(lang)}")
```

The output of the code will be two warnings about potential type mismatches, but ultimately the type and value of the variables will be unaffected 
```
2024-XX-YY HH:MM:SS.MSS | WARNING  | settingsclass.settingsclass:warn_confusing_types:576 - The parameter <console> in section <language> with value 3 of the settings file is a string but looks like a int
2024-XX-YY HH:MM:SS.MSS | WARNING  | settingsclass.settingsclass:warn_confusing_types:560 - The parameter <console> in section <machine_id> with value False of the settings file is a string but looks like a bool
Lang = 3 of type <class 'str'>
Password = False of type <class 'str'>
```

## Advanced settings
In specific use cases, you may want to use some of the more advanced settings such as using a custom encryption algorithm or setting the precision of RandomFloat's. Please see section [Full Feature list](#full-feature-list)

# Why not an existing solution?

The most common recommendations for storing settings file are the following, but each have their disadvantages
1. Using [configparser](https://docs.python.org/3/library/configparser.html)
    - Basic concept
       - Stores values inside an ini file on disk
       - Uses a two-tier dictionary-like object in memory
    - Advantages:
        - Simple and readable even for non-programmers
        - Can be read from the common ini format
        - Easy to save modified version
    - Disadvantages:
        - Lacks type hinting and type checking
        - Missing values must be try-except'ed
        - No support for optional/advanced settings
        - No support for encryption
        - No auto-completion hints from IDE
2. Using a .py file
    - Basic Concept
        - Write normal python code that only stores data
    - Advantages
        - Types are easily visible
        - Can include additional calculation or processing
        - Easy to import
    - Disadvantages
       - Requires python knowledge, cannot be easily given to non-programmers
       - Can include arbitrary code, making it extremely unsafe 
       - Variants with different values need to be saved manually
       - Difficult to have default and custom values separately
       - Keeping secret keys hidden can be challenging

3. Environmental variables
    - Basic Concept:
        - Default values defined inside code, custom values read from the environment
    - Advantages:
        - Easy to set values when working inside containers
    - Disadvantages:
        - Setting values is difficult for non-developers
        - Lacks type hinting and type checking
        - No auto-completion hints from IDE
        - Difficult to debug
        - Variable names may conflict with other programs

## This library
- Basic Concept:
    - The settings template defined inside python code, with a non-developer friendly ini file for custom values
- Advantages:
    - Easy-to-understand standard ini file for non-developers and developers alike
    - Support for environmental variables with user-defined prefix (also type cast automatically)
    - Types can be hinted and types are enforced when loading (ini) files
    - Support for randomly generated string, int and float at runtime
    - Support hidden/advanced settings
    - Support for automatic encryption of user added or default values
    - Auto-completion support due to dataclass backbone
    - Warnings on type mismatches 
        - e.g. bool in var definition, but "5" in code 
        - **reverse also true, e.g. str hint in code but "False" in config**
    - Easy to save new variant after modification
    - Safe against arbitrary content (warning message is displayed and the default value is used instead)
    - Basically no need for boilerplate code
- Disadvantages:
    - No support for single level config (e.g. config.color must be converted to config.general.color or config.ui.color etc.)
    - No support for file change watching out-of-the-box
    - Only supports .ini (JSON support planned)


# Installation 

`pip install settingsclass`

If you wish to build from source, use 

`python -m build`

## Requirements

Python 3.11+  
- loguru
- pycryptodome

# Full Feature list


## Decorator

Settings provided to the decorator will be shared across class instances. Settings provided at object instantiation take precedence. 

`@settingsclass(env_prefix: str = "", common_encryption_key: type[str | Callable[[Any], str] | None] = None, salt: bytes = None)`

### Use cases: 
1. No arguments  
The contents of the class are saved under "config.ini" in the current directory. Encryption keys are saved in the library's local folder. 
```
@settingsclass
class Settings:
    [...]
```
--- 
2. Specific arguments  
Without specifying a parameter all instantiations will look at the same webconfig.ini file. **If a folder `my_folder` is specified, the class will look for `my_folder/config.ini`**  
Specifying an encryption key will mean that all subsequent instantiations of the class will use that key unless otherwise specified.
Since the `_salt` parameter is specified, copying the file over to an other machine and using "my_encryption_key" will result in a correctly read settings file.
```
@settingsclass(file_path = "webconfig.ini", common_encryption_key = "my_encryption_key", _salt=b'\x87\x14~\x88\xf8\xfd\xb3&\xe2\xd4\xd9|@\xfb\x80\x9e')
class Settings:
    [...]
```
--- 
3. In-memory only settings/user custom file type
```
@settingsclass(None)
class Settings:
    [...]
```

The file can also be saved later manually using 
```
conf = Settings(None)
conf.save_to_file("now_im_ready.ini")

```

## Constructor

All arguments of the decorator can also be overridden by the constructor. To avoid accidental setting in regards to encryption, the decorator uses `common_encryption_key` while the constructor uses encryption_key. Other parameters have identical names.


## Variable types

### Random String
`RandomString[max_length, min_length=-1, /, random_function: Callable = secrets.token_urlsafe]`

Generates a random string between the specified lengths. If `max` is not specified, the  string will have a fixed length equal to the specified min length. Optionally a the `random_function` can also be specified which will be called as `random_function(max_length)[:true_length]`. The types can also be called directly to test them e.g. `RandomString(5)` will return e.g. `Ku_nR`. Uses `secrets.token_urlsafe`  
**The default value specified by user is ignored.**

### RandomInt[min_value, max_value, /, random_function] / RandomFloat[~]
`RandomInt[min_value: int, max_value: int, random_function: Callable = random.randint]`  
`RandomFloat[min_value: float, max_value: float, precision: int = 3, random_function: Callable = random.random]`  

Generates a number between the two limits. Optionally a function can be specified, that should accept the two limits as parameters. For floats, the precision can also be specified.  
**The default value specified by user is ignored**

### Hidden[type]

The parameter specified will not be written to the file when specified, but will be read both from environmental variables and the specified files when available.

### Encrypted[type]
Encryption is based on AES128 (256 is slower with no practical benefits).  
By default both the key and salt are randomly generated and saved inside the library directory. The IV is included within the encrypted string's field.  
This can be overwritten by specifying the `encryption_key` per object or `common_encryption_key` at the class definition level.
This can be either a string or a function handle that will be called as is.  
Salt is generated and saved per environment, ensuring that a config file cannot be copy-pasted from one environment to an other, providing an other layer of protection over the encryption key. For environments where the directory is not user-writeable the salt can be also be specified in binary string form. Per class specification is not supported, as it is not the intended use-case.    
An example of a full specification would be:  

```
@settingsclass(encryption_key="123X456", _salt=b"\x86\xce'?\xbc\x1eA\xd3&\x84\x82\xb4\xa3\x99\x10P")
class Settings:
    class program:
        password: Encrypted[str] = "will be encrypted on save"
    
s = Settings(encryption_key="abcdefgh") # this takes precedence over the encryption_key defined in the decorator
```  

Supports any type that can be cast to string

## Useful functions


### Saving to an ini file
`save_to_file(self, path=None)`  
Saves to contents (including encryption) to the specified path. If the path is left as None, the file path used to load the file is used

### Loading from an ini file
`update_from(self, config: configparser.ConfigParser, secrets_only: False) -> list[str]`  

configparser handle should be prepared by the user, including case sensitivity settings etc. Returns a list of fields that should have been encrypted but were not. For automatic encryption please use the constructor


