#!/usr/bin/env python

import asyncio
import tracemalloc
import traceback
import sys
from aider.main import main
from aider.gui import gui_main
from aider.io import InputOutput

async def async_main():
    try:
        tracemalloc.start()
        
        print("Debug: Command line arguments:", sys.argv)  # Debug print
        
        # Check if --gui argument is present
        if '--gui' in sys.argv:
            print("Debug: GUI argument detected")  # Debug print
            io = InputOutput(pretty=True, yes=True)
            if check_streamlit_install(io):
                print("Debug: Streamlit is installed, launching GUI")  # Debug print
                # Run the GUI
                return await gui_main(sys.argv)
            else:
                print("Debug: Streamlit is not installed")  # Debug print
                return 1
        else:
            print("Debug: Running CLI version")  # Debug print
            # Run the regular CLI version
            return await main(sys.argv[1:])
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Error details: {traceback.format_exc()}")
        return 1

def check_streamlit_install(io):
    try:
        import streamlit
        return True
    except ImportError:
        io.tool_error("Streamlit is not installed. Please install it to use the GUI feature.")
        io.tool_output("You can install it by running: pip install streamlit")
        return False

if __name__ == "__main__":
    sys.exit(asyncio.run(async_main()))