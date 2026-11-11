"""Generate the raw tables and the truth into data/ (~30 s)."""

import json
import time

from ccf.world.generate import build

if __name__ == "__main__":
    t = time.time()
    print(json.dumps({"rows": build(), "seconds": round(time.time() - t, 1)}))
