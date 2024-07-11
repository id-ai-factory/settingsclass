# %%

# The code has several sections with chaning variables and input/output files
# As such, it is recommended to run the file in sections while looking at
# the object values and file contents

# %% Import
from settingsclass import (
    settingsclass,
    Hidden,
    Encrypted,
    RandomFloat,
    RandomInt,
    RandomString,
)


# %% Checking the environment

# IF the test is run multiple times, the results will not match the exaplanation,
# since there is an overwrite step included
import os

if os.path.exists("config.ini"):
    raise NotImplementedError(
        "Please delete the existing config.ini to avoid confusing print statements"
    )

# %% Define the class


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
        # This should be a long password (at least 14 characters)
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


# %%
# By default the path is "config.ini" in the working directory
config = WebConfig()

# Printing the whole object will show it split into sections
print(f"Complete class:\n{config}")
print("----+++----")

# Printing just a section will also display the parent class name (WebConfig in this case)
# Encrypted data are decrypted and shown
print(config.agent)
print("=====")


# check that the types are enforced when loading from disk
def foo(x: int):  # Placeholder for user function
    print(f"Value {x} with type {type(x)}")


foo(config.agent.seed)

print("+++++")
# %% Modify contents and save to disk

config.console.machine_id = "TIG1"
config.console.maximum_message_per_second = 1

# This by itself not modify the original file in itself, only the object in memory
# We can verify this by loading the file again
# This also shows that the values are not shared between objects, i.e. they are not static
config_reloaded = WebConfig()


def check_values(conf_obj) -> str:
    return (
        f"{conf_obj.console.machine_id}; {conf_obj.console.maximum_message_per_second}"
    )


print(
    f"Modified config values = {check_values(config)}\n"
    f"New values: {check_values(config_reloaded)}"
)

# To save to a file we can call the save_to_file(self, path=None) method,
# where the path is the output ini file path.
# If it is not provided, the path of the loaded file is used (not
# necessarily config.ini)
# Note: this method may not give any hints, due to dynamic binding
config.save_to_file()

# Let's also save the previous version to disk as a comparison

config_reloaded.save_to_file("config_bk.ini")

print("**********")

# %% Enforced variable type checks

# Since this is python, variable types will not be checked, when setting values
# but can cause issues if the value is saved to disk then re-read

config.agent.seed = "abcd"
config.save_to_file()

# re-read from disk
config = WebConfig()

# A warning message should pop up with about not being able to cast the type
# If we check the value, we can see that a newly generated random value is set
print(config.agent.seed)

print("-----------")

# %% Non-enforced checks

# settingsclass also checks for possible accidental type definitions

config.console.language = 3
config.console.machine_id = False

config.save_to_file()


# A warning message will alert us, that while both values are defined as strings,
# One of them looks like an int, the other looks like a boolean
config = WebConfig()

# If this is intented, we can ignore the message as the values are unaffected
lang = config.console.language
m_id = config.console.machine_id
print(f"Lang = {lang} of type {type(lang)}")
print(f"Password = {m_id} of type {type(lang)}")
