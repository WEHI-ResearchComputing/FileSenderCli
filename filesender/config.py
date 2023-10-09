
from click_configfile import ConfigFileReader, Param, SectionSchema, matches_section

class ConfigSectionSchema:
    @matches_section("system")
    class System(SectionSchema):
        base_url = Param(default="[base_url]")
        default_transfer_days_valid = Param(type=int, default=10)
    class User(SectionSchema):
        username = Param()
        apikey = Param()

class ConfigFileProcessor(ConfigFileReader):
    config_files = ["filesender.py.ini"]
    config_section_schemas = [
        ConfigSectionSchema.System,
        ConfigSectionSchema.User,
    ]
