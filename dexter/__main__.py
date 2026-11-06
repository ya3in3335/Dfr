"""Allow ``python -m dexter`` as an alternative to ``python run.py``."""
from run import main

if __name__ == "__main__":
    raise SystemExit(main())
