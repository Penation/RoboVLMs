import os
from pathlib import Path

import numpy as np

os.environ["PYOPENGL_PLATFORM"] = "osmesa"
os.environ["MESA_GL_VERSION_OVERRIDE"] = "4.1"

# CALVIN pulls in older urdfpy/networkx versions that still reference removed numpy aliases.
for alias, value in {
    "bool": bool,
    "float": float,
    "int": int,
    "object": object,
    "str": str,
}.items():
    if alias not in np.__dict__:
        setattr(np, alias, value)

import pyrender

from calvin_env.envs.play_table_env import get_env

CALVIN_CAM_OBS_SPACE = {
    "rgb_obs": ["rgb_static", "rgb_gripper"],
    "depth_obs": ["depth_static", "depth_gripper"],
}

ROOT = Path(__file__).resolve().parents[2]
DATASET_CANDIDATES = [
    ROOT / "dataset" / "calvin_data" / "calvin_debug_dataset" / "validation",
    ROOT / "calvin" / "dataset" / "calvin_debug_dataset" / "validation",
]

for dataset_path in DATASET_CANDIDATES:
    if dataset_path.exists():
        env = get_env(
            dataset_path.as_posix(),
            obs_space=CALVIN_CAM_OBS_SPACE,
            show_gui=False,
        )
        print(env.get_obs())
        break
else:
    raise FileNotFoundError(
        f"Unable to find CALVIN debug dataset. Checked: {DATASET_CANDIDATES}"
    )
