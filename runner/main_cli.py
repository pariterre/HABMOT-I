import os

from habmoti import InterfaceCli


def main():
    config_filepath = os.environ.get("HABMOTI_CONFIG_FILE")
    InterfaceCli().exec_from_config(config_filepath) if config_filepath else InterfaceCli().exec()


if __name__ == "__main__":
    main()
