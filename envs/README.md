# RoboVLMs Conda Environment Pack

This folder contains a GitHub-friendly export of the `robovlms` conda environment.

## Files

- `robovlms.from-history.yml`  
  Minimal environment spec (best starting point, cross-machine friendly).

- `robovlms.full.yml`  
  Full resolved conda + pip environment snapshot.

- `robovlms.amlt.yml`  
  AMLT-oriented locked snapshot (derived from `full`, with local-only packages removed).

- `robovlms.explicit-linux-64.txt`  
  Exact linux-64 conda package URLs (`@EXPLICIT` lock-style file).

- `robovlms.pip-freeze.txt`  
  Full `pip freeze` output from the environment.

## Recommended restore commands

### Option A (recommended)

```bash
conda env create -n robovlms -f envs/robovlms.from-history.yml
conda activate robovlms
pip install -r envs/robovlms.pip-freeze.txt
```

### Option B (full one-shot snapshot)

```bash
conda env create -n robovlms -f envs/robovlms.full.yml
```

### Option C (AMLT recommended)

```bash
conda env create -n robovlms -f envs/robovlms.amlt.yml
```

### Option D (strict linux-64 lock)

```bash
conda create -n robovlms --file envs/robovlms.explicit-linux-64.txt
conda activate robovlms
pip install -r envs/robovlms.pip-freeze.txt
```

## Notes

- `explicit-linux-64` is platform-specific and intended for linux-64 only.
- `pip-freeze` may include editable/git dependencies; keep it as a provenance record.
