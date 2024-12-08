# Timebox

A simple command-line timeboxing utility for Things 3, with an optional menu bar interface.

## Features
- Shows all of today's tasks from Things 3 that have time tags
- Groups tasks by project
- Shows total time allocated for today
- Menu bar interface for timing tasks

## Usage

1. In Things 3, add time tags to your tasks:
   - "30min" or "30m"
   - "45min" or "45m"
   - etc.

2. Run the script:
```bash
python main.py
```

This will:
1. Show your tasks in the terminal
2. Create a menu bar icon (🥊) for timing tasks

## Installation

```bash
# Clone the repository
git clone https://github.com/walteh/timebox.git
cd timebox

# Install dependencies
pip install -e .

# Run
python main.py
```
