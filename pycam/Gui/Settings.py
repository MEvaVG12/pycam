import ConfigParser
import StringIO
import sys
import os

GET_INDEX = 0
SET_INDEX = 1
VALUE_INDEX = 2

class Settings:
    
    def __init__(self):
        self.items = {}
        self.values = {}

    def add_item(self, key, get_func=None, set_func=None):
        self.items[key] = [None, None, None]
        self.define_get_func(key, get_func)
        self.define_set_func(key, set_func)
        self.items[key][VALUE_INDEX] = None

    def define_get_func(self, key, get_func=None):
        if not self.items.has_key(key):
            return
        if get_func is None:
            get_func = lambda: self.items[key][VALUE_INDEX]
        self.items[key][GET_INDEX] = get_func

    def define_set_func(self, key, set_func=None):
        if not self.items.has_key(key):
            return
        def default_set_func(value):
            self.items[key][VALUE_INDEX] = value
        if set_func is None:
            set_func = default_set_func
        self.items[key][SET_INDEX] = set_func

    def get(self, key, default=None):
        if self.items.has_key(key):
            return self.items[key][GET_INDEX]()
        else:
            return default

    def set(self, key, value):
        if not self.items.has_key(key):
            self.add_item(key)
        self.items[key][SET_INDEX](value)
        self.items[key][VALUE_INDEX] = value

    def __str__(self):
        result = {}
        for key in self.items.keys():
            result[key] = self.get(key)
        return str(result)


class SettingsManager:

    DEFAULT_CONFIG = """
[ToolDefault]
torus_radius: 0.25
feedrate: 1000
speed: 200

[Tool0]
name: Cylindrical (3 inch)
shape: CylindricalCutter
tool_radius: 3

[Tool1]
name: Spherical (0.1 inch)
shape: SphericalCutter
tool_radius: 1

[Tool2]
name: Toroidal (2 inch)
shape: ToroidalCutter
tool_radius: 2
torus_radius: 0.2

[ProcessDefault]
path_direction: x
safety_height: 5
step_down: 1

[Process0]
name: Rough
path_generator: PushCutter
path_postprocessor: PolygonCutter
material_allowance: 0.5
step_down: 0.8
overlap: 0

[Process1]
name: Semi-finish
path_generator: PushCutter
path_postprocessor: ContourCutter
material_allowance: 0.2
step_down: 0.5
overlap: 20

[Process2]
name: Finish
path_generator: DropCutter
path_postprocessor: ZigZagCutter
material_allowance: 0.0
overlap: 60

[TaskDefault]
enabled: 1

[Task0]
tool: 0
process: 0

[Task1]
tool: 2
process: 1

[Task2]
tool: 1
process: 2
"""

    SETTING_TYPES = {
            "name": str,
            "shape": str,
            "tool_radius": float,
            "torus_radius": float,
            "speed": float,
            "feedrate": float,
            "path_direction": str,
            "path_generator": str,
            "path_postprocessor": str,
            "safety_height": float,
            "material_allowance": float,
            "overlap": float,
            "step_down": float,
            "tool": object,
            "process": object,
            "enabled": bool,
            "minx": float,
            "miny": float,
            "minz": float,
            "maxx": float,
            "maxy": float,
            "maxz": float,
    }

    CATEGORY_KEYS = {
            "tool": ("name", "shape", "tool_radius", "torus_radius", "feedrate", "speed"),
            "process": ("name", "path_generator", "path_postprocessor", "path_direction",
                    "safety_height", "material_allowance", "overlap", "step_down"),
            "task": ("tool", "process", "enabled"),
    }

    SECTION_PREFIXES = {
        "tool": "Tool",
        "process": "Process",
        "task": "Task",
    }

    def __init__(self):
        self.config = None
        self._cache = {}
        self.reset()

    def reset(self, config_text=None):
        self._cache = {}
        self.config = ConfigParser.SafeConfigParser()
        if config_text is None:
            config_text = StringIO.StringIO(self.DEFAULT_CONFIG)
        else:
            config_text = StringIO.StringIO(config_text)
        self.config.readfp(config_text)

    def load_file(self, filename):
        try:
            self.config.read([filename])
        except ConfigParser.ParsingError, err_msg:
            print >> sys.stderr, "Failed to parse config file '%s': %s" % (filename, err_msg)
            return False
        return True

    def load_from_string(self, config_text):
        input_text = StringIO.StringIO(config_text)
        try:
            self.reset(input_text)
        except ConfigParser.ParsingError, err_msg:
            print >> sys.stderr, "Failed to parse config data: %s" % str(err_msg)
            return False
        return True

    def write_to_file(self, filename):
        try:
            fi = open(filename, "w")
            self.config.write(fi)
            fi.close()
        except IOError, err_msg:
            print >> sys.stderr, "Failed to write configuration to file (%s): %s" % (filename, err_msg)
            return False
        return True

    def get_tools(self):
        return self._get_category_items("tool")

    def get_processes(self):
        return self._get_category_items("process")

    def get_tasks(self):
        return self._get_category_items("task")

    def _get_category_items(self, type_name):
        if not self._cache.has_key(type_name):
            item_list = []
            index = 0
            prefix = self.SECTION_PREFIXES[type_name]
            current_section_name = "%s%d" % (prefix, index)
            while current_section_name in self.config.sections():
                item = {}
                for key in self.CATEGORY_KEYS[type_name]:
                    value_type = self.SETTING_TYPES[key]
                    try:
                        value_raw = self.config.get(current_section_name, key)
                    except ConfigParser.NoOptionError:
                        try:
                            value_raw = self.config.get(prefix + "Default", key)
                        except ConfigParser.NoOptionError:
                            value_raw = None
                    if not value_raw is None:
                        try:
                            if value_type == object:
                                # try to get the referenced object
                                value = self._get_category_items(key)[int(value_raw)]
                            else:
                                # just do a simple type cast
                                value = value_type(value_raw)
                        except (ValueError, IndexError):
                            value = None
                        if not value is None:
                            item[key] = value
                item_list.append(item)
                index += 1
                current_section_name = "%s%d" % (prefix, index)
            self._cache[type_name] = item_list
        return self._cache[type_name][:]

