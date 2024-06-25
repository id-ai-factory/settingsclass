from settings import settingsclass, Hidden, Encrypted, RandomFloat, RandomString


# Use the locally created encrpyion key and salt
@settingsclass
class WebConfig:
    class login:
        # int with default value of 12
        min_passw_len: int = 12
        # The encrypted value wil be saved to disk.
        # If a user modifies this, it will be encrypted and the origin file will be overwritten
        backdoor_pint: Encrypted[int] = 1795
        # Most consoles support color characters, therefore this setting can be usually hidden
        # Depending on the deployment environment, it may be necessary to override
        color_console: Hidden[bool] = True

    class agent:
        # Fixed string parameter
        api: str = "google.com/api"
        # The seed should be a random 5 character string. Default value des not matter
        seed: Encrypted[RandomString[5]] = ""
        # The temperature of the agent should be low, but variable. Default value des not matter
        temperature: RandomFloat[0, 0.3] = 0


# Set the file to "webconfig.ini"
config = WebConfig("webconfig.ini")

# Printing the whole object will show it split into sections
print(config)
print("-----")

# Printing just a section will aslo display the parent class name (WebConfig in this case)
print(config.login)
print("=====")


# It can be verified that the types are in fact enforced
print(f"{config.login.backdoor_pint} w/ {type(config.login.backdoor_pint)}")
print(f"{config.login.color_console} w/ {type(config.login.color_console)}")
print(f"{config.agent.temperature} w/ {type(config.agent.temperature)}")

# Specifying a different file will result in a slightly different output due to encryption iv
# Specifically, backdoor_pint and seed will have different values
conf2 = WebConfig("web2.ini")
# The member can be set just as usual
conf2.login.backdoor_pint = 887
# It can be verified that the values are in fact not static
print(f"Conf1 = {config.login.backdoor_pint} Conf2 = {conf2.login.backdoor_pint}")
