import logging
from habmoti import InterfaceFromEnvironment


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.info("Starting the analyzer...")
    logging.warning("Starting the analyzer...")

    InterfaceFromEnvironment().exec()


if __name__ == "__main__":
    main()
