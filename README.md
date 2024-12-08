![Header](header.png)

# Timebox – macOS Menubar App

A simple menubar app for macOS that adds Timeboxing and Pomodoro workflow support to Things 3.

## Usage

1. In Things 3, add time tags to your tasks (e.g., "30min", "45min", "1min", etc.)
2. Move tasks to Today
3. Run Timebox
4. Click the 🥊 icon in your menu bar to see your tasks and start timing them

The app will show you:
- Total time scheduled for today
- List of all tasks with time tags
- Quick-select buttons for common time intervals

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/timebox.git
cd timebox
```

2. Install dependencies:
```bash
make install
```

3. Build the app:
```bash
make build
```

4. Run the app:
- For development: `make run`
- For production: Open `dist/Timebox.app`

## Troubleshooting

If you get a security warning when opening the app:
1. Go to System Settings > Privacy & Security
2. Click "Open Anyway" for Timebox.app

Or run in terminal:
```bash
xattr -cr "dist/Timebox.app"
```

---

See also:

- [mk1123/timebox](https://github.com/mk1123/timebox)
- [visini/pomodoro](https://github.com/visini/pomodoro)
