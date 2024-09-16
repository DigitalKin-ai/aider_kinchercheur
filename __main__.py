#!/usr/bin/env python

import asyncio
import tracemalloc
import traceback
import sys
import logging
from aider.main import main
from aider.io import InputOutput

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_main():
    logger.info("Starting run_main function")
    if '--gui' in sys.argv:
        logger.debug("GUI argument detected")
        try:
            from aider.gui import gui_main
        except ImportError:
            logger.error("GUI mode requested but PySimpleGUI is not installed.")
            print("Error: PySimpleGUI is not installed. Please install it to use the GUI feature.")
            print("You can install it by running: pip install PySimpleGUI")
            return 1
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
    logger.info("Starting main_wrapper function")
    try:
        tracemalloc.start()
        logger.debug(f"Command line arguments: {sys.argv}")
        
        result = asyncio.run(run_main())
        logger.info(f"run_main completed with result: {result}")
        return result
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return 1
    finally:
        tracemalloc.stop()
        logger.info("main_wrapper function completed")

def check_streamlit_install(io):
    logger.info("Checking Streamlit installation")
    try:
        import streamlit
        logger.info("Streamlit is installed")
        return True
    except ImportError:
        logger.warning("Streamlit is not installed")
        io.tool_error("Streamlit is not installed. Please install it to use the GUI feature.")
        io.tool_output("You can install it by running: pip install streamlit")
        return False

if __name__ == "__main__":
    logger.info("Script started")
    exit_code = main_wrapper()
    logger.info(f"Script completed with exit code: {exit_code}")
    sys.exit(exit_code)
