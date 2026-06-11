from ..habmoti import Habmoti


class InterfaceCli:
    def __init__(self):
        self._habmoti = Habmoti

    def exec(self) -> None:
        print("Welcome to the HABMOT-I CLI!")
        print("Type 'help' for a list of commands, or 'quit' to quit.")
        while True:
            command = input("> ").strip().lower()
            if command == "quit":
                print("Exiting the CLI. Goodbye!")
                break
            elif command == "start":
                self._habmoti.start()
                print("HABMOT-I started.")
            elif command == "help":
                print("Available commands:")
                print("  help - Show this help message")
                print("  start - Start the HABMOT-I system")
                print("  quit - Exit the CLI")
                # Add more commands here as needed
            else:
                print(f"Unknown command: {command}. Type 'help' for a list of commands.")
