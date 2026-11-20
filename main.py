"""Start the Kreatics Compiler Studio:   python main.py"""
import sys


def main():
    try:
        from kreatics.gui.app import KreaticsApp
        app = KreaticsApp()
    except ImportError as exc:
        sys.exit(f"Tkinter is missing ({exc}). On Linux install it with: sudo apt install python3-tk")
    app.mainloop()


if __name__ == "__main__":
    main()
