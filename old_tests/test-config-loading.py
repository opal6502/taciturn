
from taciturn.config import load_config
import pprint

print("Loading config ...")
c = load_config()
print("Config loaded!")
pprint.pprint(c)