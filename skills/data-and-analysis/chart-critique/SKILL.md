---
name: chart-critique
description: Critiques a chart or dashboard for misleading scales, wrong chart types, clutter, and unclear takeaways, then proposes a redesign. Use when a user shares a chart, plot code, or dashboard for feedback.
---

# Detailed Instructions

A chart should answer one question at a glance, honestly. Judge it by whether a reader gets the
right takeaway in five seconds, and fix what stops that.

## Overview

Most chart problems are not about taste: a truncated y-axis that turns a 2% change into a cliff,
a pie with nine slices, a dual axis that implies correlation, a title that says "Revenue" instead
of what happened to revenue. This skill checks a chart for honesty, fit, and clarity, and returns
a specific redesign (and code, when the chart came from code).

## Workflow Rules

1. **State the question** the chart is meant to answer. If it is unclear, that is finding #1.
2. **Honesty checks:**
   - Bar and area charts start at zero; line charts may not, but the axis range must be labeled.
   - No dual y-axes that make unrelated series look correlated.
   - Consistent intervals on the time axis; partial periods marked (the current month is not a dip).
   - Areas and bubbles scaled by area, not radius; no 3D.
   - Percentages state their base; small samples are labeled.
3. **Fit:** the chart type matches the question —
   change over time → line; compare categories → sorted horizontal bar; part of whole with 2–4
   parts → stacked bar (or pie at most); distribution → histogram or box plot; relationship →
   scatter.
4. **Clarity:** a title that states the takeaway ("Signups fell 18% after the pricing change");
   direct labels instead of a legend when possible; no more than ~5 colors, with one highlight
   color for what matters; gridlines light or gone; readable units ($1.2M, not 1200000).
5. **Accessibility:** color is not the only encoding; contrast is sufficient; colorblind-safe palette.
6. **Report** findings ranked by impact (misleading first), then the redesign: chart type,
   encodings, title, annotations.
7. If the chart was produced by code (matplotlib, plotly, Vega, ggplot), provide the revised code.

## Anti-Patterns (What NOT to do)

* Do not critique style before checking whether the chart misleads.
* Do not recommend a fancier chart type when a sorted bar or line is clearer.
* Do not leave a descriptive title ("Revenue by month") when the chart has a clear finding.
* Do not change the underlying numbers or aggregation without saying so.
* Do not judge colors alone; check the message.

## Examples

**User:** "Thoughts on this chart for the board deck?" *(bar chart "Monthly Revenue", Jan–Nov, y-axis 980k–1.06M, 11 colors, legend at right, November is month-to-date)*

**Expected output:**

```text
Question it should answer: is revenue growing, and did anything change recently?

## Findings (most serious first)
1. Misleading — y-axis starts at $980k on a bar chart. A 6% rise from Jan to Oct looks several times larger.
   Start bars at zero, or switch to a line chart with a labeled axis.
2. Misleading — November is month-to-date (21 days) and reads as a 30% drop. Mark it as partial
   or show it as a dashed projection.
3. Fit — monthly revenue over time is a trend question; a line shows it better than 11 bars.
4. Clarity — 11 colors encode nothing (one per month). Use one color.
5. Clarity — title "Monthly Revenue" states no takeaway.

## Redesign
- Line chart, Jan–Oct solid; November as a dashed projection from 21 days of data, labeled as such.
- Title: "Revenue up 6% since January; November on track for a record month"
- Single color; direct label on the last full month ($1.05M); light horizontal gridlines only.
- Axis: $0.9M–$1.1M, clearly labeled (line charts don't need a zero baseline, but the range must be visible).

## Revised matplotlib
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(months[:-1], revenue[:-1], color="#2563EB", linewidth=2)
nov_projected = revenue[-1] / 21 * 30          # MTD scaled to the full month
ax.plot(months[-2:], [revenue[-2], nov_projected], color="#2563EB", linewidth=2, linestyle="--")
ax.annotate("Projected (21 of 30 days)", (months[-1], nov_projected), textcoords="offset points", xytext=(0, 8), ha="center")
ax.set_ylim(0.9e6, 1.1e6)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Revenue up 6% since January; November on track for a record month", loc="left")
```
