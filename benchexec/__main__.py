import sys
sys.dont_write_bytecode = True # prevent creation of .pyc files

from . import main
sys.exit(main())