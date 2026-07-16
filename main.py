#!/usr/bin/env python3
"""Interview question learning app with progressive cloze recall."""

from interview_learner.gui import IntroWindow


def main() -> None:
    app = IntroWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
