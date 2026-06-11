from ..habmoti import Habmoti


class InterfaceCli:
    def __init__(self, habmoti: "Habmoti"):
        self._habmoti = habmoti

    def exec(self) -> None:
        print("Welcome to the HABMOT-I CLI!")
        print("Type 'help' for a list of commands, or 'quit' to quit.")
        while True:
            command = input("> ").strip().lower()
            if command == "quit":
                print("Exiting the CLI. Goodbye!")
                break
            elif command == "help":
                print("Available commands:")
                print("  help - Show this help message")
                print("  quit - Exit the CLI")
                # Add more commands here as needed
            else:
                print(f"Unknown command: {command}. Type 'help' for a list of commands.")
