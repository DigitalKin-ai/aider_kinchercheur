#!/usr/bin/env python

import os
import sys
import asyncio
import PySimpleGUI as sg
from aider.coders import Coder
from aider.io import InputOutput
from aider import __version__, models, utils
from aider.args import get_parser

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

class CaptureIO(InputOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = []

    def tool_output(self, msg, log_only=False):
        if not log_only:
            self.output.append(msg)
        super().tool_output(msg, log_only=log_only)

    def tool_error(self, msg):
        self.output.append(msg)
        super().tool_error(msg)

    def get_output(self):
        output = self.output
        self.output = []
        return output

async def get_coder():
    from aider.main import main as cli_main
    coder = await cli_main(return_coder=True)
    if not isinstance(coder, Coder):
        raise ValueError(coder)
    if not coder.repo:
        raise ValueError("GUI can currently only be used inside a git repo")

    io = CaptureIO(
        pretty=False,
        yes=True,
        dry_run=coder.io.dry_run,
        encoding=coder.io.encoding,
    )
    coder.commands.io = io

    for line in coder.get_announcements():
        coder.io.tool_output(line)

    return coder

class GUI:
    def __init__(self):
        self.coder = None
        self.window = None

    async def initialize(self):
        self.coder = await get_coder()
        self.create_window()

    def create_window(self):
        layout = [
            [sg.Text("Kins - Autonomous multi-agents AI on your computer", font=("Helvetica", 20))],
            [sg.Multiline(size=(80, 20), key="-OUTPUT-", disabled=True)],
            [sg.Input(key="-INPUT-", size=(70, 1)), sg.Button("Send", bind_return_key=True)],
            [sg.Button("Clear"), sg.Button("Exit")]
        ]
        self.window = sg.Window("Kins", layout, finalize=True)

    async def run(self):
        while True:
            event, values = self.window.read(timeout=100)
            if event == sg.WINDOW_CLOSED or event == "Exit":
                break
            elif event == "Send":
                user_input = values["-INPUT-"]
                if user_input:
                    self.window["-INPUT-"].update("")
                    await self.process_input(user_input)
            elif event == "Clear":
                self.window["-OUTPUT-"].update("")

        self.window.close()

    async def process_input(self, user_input):
        self.window["-OUTPUT-"].print(f"User: {user_input}")
        response = await self.coder.run_stream(user_input)
        self.window["-OUTPUT-"].print(f"Assistant: {response}")

        # Display any captured output
        output = self.coder.commands.io.get_output()
        if output:
            self.window["-OUTPUT-"].print("\n".join(output))

async def gui_main(argv=None):
    gui = GUI()
    await gui.initialize()
    await gui.run()
    return 0

if __name__ == "__main__":
    import sys
    asyncio.run(gui_main(sys.argv[1:]))
