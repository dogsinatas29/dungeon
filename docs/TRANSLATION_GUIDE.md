# Translation Guide (번역 가이드)

Dungeon Crawler welcomes contributions from the community! This guide explains how to add a new language or improve existing translations.
(이 가이드는 새로운 언어를 추가하거나 기존 번역을 개선하는 방법을 설명합니다.)

## Overview (개요)
The game uses a dual system for localization:
1.  **Code-based Strings**: Stored in `dungeon/localization.py`.
2.  **Data-based Strings**: Stored in CSV files within `dungeon/data/<lang>/`.

---

## Step 1: Modifying `dungeon/localization.py`

This file contains the main dictionary `TRANSLATIONS`.

1.  Open `dungeon/localization.py`.
2.  Find the `TRANSLATIONS` dictionary.
3.  Add a new key for your language code (e.g., `"ja"` for Japanese, `"fr"` for French).
4.  Copy the content from `"en"` or `"ko"` key and translate the values.

**Example:**
```python
TRANSLATIONS = {
    "en": {
        "Hello": "Hello",
        "Firebolt": "Firebolt",
    },
    "ja": {
        "Hello": "こんにちは",
        "Firebolt": "ファイアボルト",
    }
}
```

---

## Step 2: Translating Data Files (CSV)

Large text blocks (like Boss dialogues) are stored in external files.

1.  Navigate to `dungeon/data/`.
2.  Create a folder for your language code (e.g., `dungeon/data/ja/`).
3.  Copy `boss_dialogues.csv` from `dungeon/data/` (or `dungeon/data/en/`) into your new folder.
4.  Open the copied CSV file and translate the **Dialogue** column. **DO NOT change the BossID, Trigger, or Value columns.**

---

## Step 3: Registering the New Language

To make the new language selectable in the game:

1.  Open `dungeon/ui.py`.
2.  Find the `ConsoleUI.show_language_selection` method.
3.  Add your language to the `print` statements (e.g., `print("3. Japanese")`).
4.  Open `Start.py`.
5.  Find the input handling logic in `main_menu`.
6.  Add a condition to set `config.LANGUAGE` to your new code (e.g., `"ja"`) when the user selects the new option.

---

## Contributing
If you have created a new translation, please submit a Pull Request on GitHub!
