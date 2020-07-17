
from taciturn.config import get_config
import pprint

print("Loading config ...")
c = get_config()
print("Config loaded!")
pprint.pprint(c)