#!/usr/bin/env python3
from pathlib import Path
import argparse


def replace_once(text: str, old: str, new: str, *, path: Path, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"{path}: expected {label!r} not found")
    return text.replace(old, new, 1)


def patch_calvin_agent_utils(calvin_root: Path) -> None:
    path = calvin_root / "calvin_models" / "calvin_agent" / "utils" / "utils.py"
    text = path.read_text()
    text = replace_once(
        text,
        "import cv2\n",
        "try:\n    import cv2\nexcept ImportError:\n    cv2 = None\n",
        path=path,
        label="cv2 import",
    )
    text = replace_once(
        text,
        "def add_text(img, lang_text):\n    height, width, _ = img.shape\n",
        "def add_text(img, lang_text):\n    if cv2 is None:\n        return\n    height, width, _ = img.shape\n",
        path=path,
        label="add_text body",
    )
    path.write_text(text)


def patch_calvin_eval_utils(calvin_root: Path) -> None:
    path = calvin_root / "calvin_models" / "calvin_agent" / "evaluation" / "utils.py"
    text = path.read_text()
    text = replace_once(
        text,
        "from pydoc import locate\n\nfrom calvin_agent.models.mcil import MCIL\n",
        "from pydoc import locate\nimport hashlib\n\nfrom calvin_agent.models.mcil import MCIL\n",
        path=path,
        label="hashlib import",
    )
    text = replace_once(
        text,
        "import cv2\n",
        "try:\n    import cv2\nexcept ImportError:\n    cv2 = None\n",
        path=path,
        label="cv2 import",
    )
    text = replace_once(
        text,
        "import pyhash\n",
        "try:\n    import pyhash\nexcept ImportError:\n    pyhash = None\n",
        path=path,
        label="pyhash import",
    )
    text = replace_once(
        text,
        "hasher = pyhash.fnv1_32()\n",
        "hasher = pyhash.fnv1_32() if pyhash is not None else (lambda value: int(hashlib.md5(str(value).encode('utf-8')).hexdigest()[:8], 16))\n",
        path=path,
        label="hasher definition",
    )
    text = replace_once(
        text,
        "def join_vis_lang(img, lang_text):\n    \"\"\"Takes as input an image and a language instruction and visualizes them with cv2\"\"\"\n",
        "def join_vis_lang(img, lang_text):\n    \"\"\"Takes as input an image and a language instruction and visualizes them with cv2\"\"\"\n    if cv2 is None:\n        return\n",
        path=path,
        label="join_vis_lang guard",
    )
    text = replace_once(
        text,
        "def imshow_tensor(window, img_tensor, wait=0, resize=True, keypoints=None, text=None):\n",
        "def imshow_tensor(window, img_tensor, wait=0, resize=True, keypoints=None, text=None):\n    if cv2 is None:\n        return\n",
        path=path,
        label="imshow_tensor guard",
    )
    path.write_text(text)


def patch_play_table_env(calvin_root: Path) -> None:
    path = calvin_root / "calvin_env" / "calvin_env" / "envs" / "play_table_env.py"
    text = path.read_text()
    text = replace_once(
        text,
        "import cv2\n",
        "try:\n    import cv2\nexcept ImportError:\n    cv2 = None\n",
        path=path,
        label="cv2 import",
    )
    text = replace_once(
        text,
        "    def render(self, mode=\"human\"):\n        \"\"\"render is gym compatibility function\"\"\"\n        rgb_obs, depth_obs = self.get_camera_obs()\n",
        "    def render(self, mode=\"human\"):\n        \"\"\"render is gym compatibility function\"\"\"\n        rgb_obs, depth_obs = self.get_camera_obs()\n        if mode == \"human\" and cv2 is None:\n            raise RuntimeError(\"cv2 is required for GUI rendering but is not installed\")\n",
        path=path,
        label="render guard",
    )
    text = replace_once(
        text,
        "    if not hydra.core.global_hydra.GlobalHydra.instance().is_initialized():\n"
        "        hydra.initialize(\".\")\n"
        "    env = hydra.utils.instantiate(render_conf.env, show_gui=show_gui, use_vr=False, use_scene_info=True)\n",
        "    render_conf.env.use_egl = kwargs.get(\"use_egl\", False)\n"
        "    if not hydra.core.global_hydra.GlobalHydra.instance().is_initialized():\n"
        "        hydra.initialize(\".\")\n"
        "    env = hydra.utils.instantiate(\n"
        "        render_conf.env,\n"
        "        show_gui=show_gui,\n"
        "        use_vr=False,\n"
        "        use_scene_info=True,\n"
        "        use_egl=kwargs.get(\"use_egl\", False),\n"
        "    )\n",
        path=path,
        label="get_env use_egl override",
    )
    path.write_text(text)


def patch_cameras_for_tiny_renderer(calvin_root: Path) -> None:
    camera_files = [
        calvin_root / "calvin_env" / "calvin_env" / "camera" / "static_camera.py",
        calvin_root / "calvin_env" / "calvin_env" / "camera" / "gripper_camera.py",
    ]
    for path in camera_files:
        text = path.read_text()
        text = replace_once(
            text,
            "        image = p.getCameraImage(\n"
            "            width=self.width,\n"
            "            height=self.height,\n"
            "            viewMatrix=self.viewMatrix,\n"
            "            projectionMatrix=self.projectionMatrix,\n"
            "            physicsClientId=self.cid,\n"
            "        )\n",
            "        image = p.getCameraImage(\n"
            "            width=self.width,\n"
            "            height=self.height,\n"
            "            viewMatrix=self.viewMatrix,\n"
            "            projectionMatrix=self.projectionMatrix,\n"
            "            renderer=p.ER_TINY_RENDERER,\n"
            "            physicsClientId=self.cid,\n"
            "        )\n",
            path=path,
            label="tiny renderer static camera",
        ) if path.name == "static_camera.py" else replace_once(
            text,
            "        image = p.getCameraImage(\n"
            "            width=self.width,\n"
            "            height=self.height,\n"
            "            viewMatrix=self.view_matrix,\n"
            "            projectionMatrix=self.projection_matrix,\n"
            "            physicsClientId=self.cid,\n"
            "        )\n",
            "        image = p.getCameraImage(\n"
            "            width=self.width,\n"
            "            height=self.height,\n"
            "            viewMatrix=self.view_matrix,\n"
            "            projectionMatrix=self.projection_matrix,\n"
            "            renderer=p.ER_TINY_RENDERER,\n"
            "            physicsClientId=self.cid,\n"
            "        )\n",
            path=path,
            label="tiny renderer gripper camera",
        )
        path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch CALVIN for headless AMLT evaluation.")
    parser.add_argument("--calvin-root", type=Path, required=True)
    args = parser.parse_args()

    calvin_root = args.calvin_root.resolve()
    patch_calvin_agent_utils(calvin_root)
    patch_calvin_eval_utils(calvin_root)
    patch_play_table_env(calvin_root)
    patch_cameras_for_tiny_renderer(calvin_root)
    print(f"Patched CALVIN compatibility files under {calvin_root}")


if __name__ == "__main__":
    main()
