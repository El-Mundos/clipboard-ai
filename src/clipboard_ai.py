#!/usr/bin/env python3
"""
Unified entry point for clipboard-ai
Handles both daemon and client mode based on how it's called
"""
import sys
import os

# Determine mode based on argv[0] or first argument
binary_name = os.path.basename(sys.argv[0])

if binary_name == 'clipboard-ai-daemon' or '--daemon' in sys.argv:
    # Run as daemon
    if '--daemon' in sys.argv:
        sys.argv.remove('--daemon')
    from daemon import main
    sys.exit(main())
else:
    # Run as client (default)
    from client import main
    sys.exit(main())
