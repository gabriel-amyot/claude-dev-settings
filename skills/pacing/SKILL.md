---
name: pacing
description: Show weekly usage pacing for 6-day work week to help maximize daily usage without overspending
model: haiku
---

# Pacing Skill

Display current weekly usage compared to expected usage based on a 6-day work week schedule.

**Usage:** `/pacing`

## Objective

Help the user pace their weekly Claude Code usage across a 6-day work week (Mon-Sat) to maximize daily usage without exceeding the weekly limit. At the end of day 3, they should be at 50% usage.

## Algorithm

### Step 1: Get Current Usage Data

Read the usage cache file at `~/.claude/usage-cache.json` which is automatically updated at session start.

The cache file contains:
- `usage_percent`: Current week usage as a number (e.g., 24)
- `reset_info`: When the weekly limit resets (e.g., "Feb 21 at 10am America/Toronto")
- `last_updated`: Timestamp of when cache was last updated
- `raw_output`: Raw output from `claude usage` command

**If cache file doesn't exist or is stale:**
- Ask user to restart their Claude Code session (which will trigger the cache update hook)
- Or ask user to manually provide current usage percentage and reset date/time

Extract the following information:
- **Current week usage percentage** (from `usage_percent` field)
- **Reset date and time** (from `reset_info` field)
- **Current date and time** (system date)

### Step 2: Calculate Work Week Progress

**IMPORTANT:** The cycle reset date determines Day 1 of the work week. The first day of the cycle is the same weekday as when it resets.

Given:
- Reset date and time (e.g., "Feb 22 at 10am" = Saturday 10am)
- Current date and time
- 6-day work week (starts from reset day)

Calculate:
1. **Parse reset date** to determine the reset day of week (e.g., Saturday)
2. **Calculate days elapsed** since the cycle started (today's date - most recent reset date)
3. **Current work day** (1-6, where Day 1 = reset day):
   - Example: If reset is Saturday, then Sat=1, Sun=2, Mon=3, Tue=4, Wed=5, Thu=6
4. **Expected usage** at end of current work day:
   - Day 1 end: 16.67% (1/6)
   - Day 2 end: 33.33% (2/6)
   - Day 3 end: 50.00% (3/6)
   - Day 4 end: 66.67% (4/6)
   - Day 5 end: 83.33% (5/6)
   - Day 6 end: 100.00% (6/6)

5. **Expected usage by end of TODAY**: Calculate based on current work day

**Example:**
- Reset: "Feb 22 at 10am" (Saturday)
- Today: Feb 24 (Monday) 2pm
- Days since reset: 2 days
- Current work day: Day 3 (Sat=1, Sun=2, Mon=3)
- Expected by end of today: 50.0%

### Step 3: Calculate Pacing Status

Compare actual vs expected:
- **Variance** = Actual Usage - Expected Usage
- **Status**:
  - If variance > +10%: "AHEAD" (may want to slow down)
  - If variance between -5% and +10%: "ON TRACK" (good pacing)
  - If variance < -5%: "BEHIND" (can use more)

### Step 4: Display Pacing Report

Output format:

```
📊 Weekly Usage Pacing (6-day work week)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current week usage:
  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░       24.0% used

Work day: [Day X of 6] (Monday/Tuesday/Wednesday/Thursday/Friday/Saturday)
Resets: [Reset date and time]

Pacing Analysis:
  Expected by end of today:  XX.X%
  Actual usage:              XX.X%
  Variance:                  ±X.X% [STATUS]

  [Progress bar showing actual vs expected]
  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░  Actual
  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░░░  Expected

Recommendation:
  [Contextual message based on status]
  - If AHEAD: "You're ahead of pace. Consider saving capacity for later in the week."
  - If ON TRACK: "Perfect pacing! Continue with your current usage rate."
  - IF BEHIND: "You have room to use more today. You can increase usage by X% to stay on track."

Days remaining: X days until reset
```

## Important Notes

- **Flexible work week**: The 6-day work week starts on the same day of the week as the reset (e.g., if reset is Saturday, work week is Sat-Thu)
- **Reset timing**: If the reset happens mid-day (e.g., 10am), account for partial day calculations
- **7th day (rest day)**: The day before reset is the rest day (excluded from work day calculations)
- **Rounding**: Display percentages with 1 decimal place for clarity
- **Cache staleness**: If cache is more than 4 hours old, warn user and suggest restarting session

## Edge Cases

1. **New week (Day 1, no usage yet)**:
   - Expected: 0% (start of day) to 16.67% (end of day)
   - Show encouragement to start using capacity

2. **End of week (Day 6)**:
   - Expected: ~100%
   - If usage is low, encourage using remaining capacity

3. **Rest day (7th day before reset)**:
   - Show that it's a rest day
   - Display Day 1's target (16.67%) for tomorrow
   - Show hours/minutes until reset

4. **Past reset time but still same day**:
   - If reset just happened, treat as new week Day 1

5. **Cache file missing or stale**:
   - If `~/.claude/usage-cache.json` doesn't exist, ask user to restart session
   - If `last_updated` is more than 4 hours old, warn and suggest refresh
