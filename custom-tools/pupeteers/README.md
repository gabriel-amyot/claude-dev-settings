# Claude Auto-Resumer

This script allows you to pause your work with Claude (e.g., due to rate limits) and automatically resume it after a set period, ensuring your computer stays awake during the wait.

## Usage

### 1. Stop Current Session
First, stop your current Claude session by pressing `Ctrl + C` in the terminal. Claude automatically saves your context.

### 2. Run the Resume Script
To run the script and keep your Mac awake (preventing sleep mode), use the `caffeinate` command:

```bash
# Default: Wait 2 hours
caffeinate -i ./resume_claude.sh

# Wait 3 hours
caffeinate -i ./resume_claude.sh 3

# Wait 30 minutes (0.5 hours)
caffeinate -i ./resume_claude.sh 0.5
```

### 3. Options

| Argument | Description |
| :--- | :--- |
| `hours` | Optional. Number of hours to wait. Defaults to `2`. |
| `-h`, `--help` | Show the help message. |

## How it Works

1. The script waits for the specified duration.
2. While waiting, `caffeinate` prevents the system from sleeping.
3. Once the time is up, it automatically relaunches `claude` with a prompt to continue exactly where you left off.
