#!/usr/bin/env python

import asyncio
import tracemalloc
import traceback
import sys
import logging
from aider.main import main
from aider.gui import gui_main
from aider.io import InputOutput

# Configuration du logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_main():
    if '--gui' in sys.argv:
        logger.debug("GUI argument detected")
        io = InputOutput(pretty=True, yes=True)
        if check_streamlit_install(io):
            logger.debug("Streamlit is installed, launching GUI")
            return await gui_main(sys.argv)
        else:
            logger.debug("Streamlit is not installed")
            return 1
    else:
        logger.debug("Running CLI version")
        return await main(sys.argv[1:])

def main_wrapper():
    try:
        tracemalloc.start()
        logger.debug(f"Command line arguments: {sys.argv}")
        
        return asyncio.run(run_main())
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return 1
    finally:
        tracemalloc.stop()

def check_streamlit_install(io):
    try:
        import streamlit
        return True
    except ImportError:
        io.tool_error("Streamlit is not installed. Please install it to use the GUI feature.")
        io.tool_output("You can install it by running: pip install streamlit")
        return False

if __name__ == "__main__":
    sys.exit(main_wrapper())