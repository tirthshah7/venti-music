import os
import sys

# repo root, so `web.app...` imports resolve
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
