import logging
from linux_arctis_manager.gui_gtk.app import main as run_gtk

def main():
    logging.basicConfig(level=logging.INFO)
    run_gtk()

if __name__ == "__main__":
    main()
