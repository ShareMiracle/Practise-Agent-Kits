import json

# def single_day_schedule_to_prompt(
#     day,
#     day_schedule,
#     conference,
#     year,
#     city=None
# ):
#     lines = []

#     for time_range, events in day_schedule.items():
#         for ev in events:
#             lines.append(f"{time_range}")
#             lines.append(ev["title"])
#             if "type" in ev:
#                 lines.append(ev["type"])
#             if "location" in ev:
#                 lines.append(ev["location"])
#             lines.append("")

#     schedule_text = "\n".join(lines)
#     city_text = f", held in {city}" if city else ""

#     prompt = f"""
# A clean, modern academic conference daily schedule poster.

# Conference: {conference} {year}{city_text}
# Date: {day}

# Vertical timeline layout.
# White background with soft blue and gray accents.
# Rounded cards aligned to a timeline.

# Schedule:
# {schedule_text}

# Design style:
# minimal, professional, academic conference poster
# clear typography, balanced spacing
# Notion or Apple Keynote style
# high resolution, no cartoon style
# """
#     return prompt

def single_day_schedule_to_prompt(
    day,
    day_schedule,
    conference,
    year,
    city=None
):
    lines = []

    for time_range, events in day_schedule.items():
        for ev in events:
            lines.append(time_range)
            lines.append(ev["title"])
            if "type" in ev:
                lines.append(ev["type"])
            if "location" in ev:
                lines.append(ev["location"])
            lines.append("")

    schedule_text = "\n".join(lines)
    city_text = f", held in {city}" if city else ""

    prompt = f"""
A clean, modern academic conference daily schedule poster.

IMPORTANT:
All schedule text below is machine-generated factual information.
You MUST render the schedule text EXACTLY as provided.
DO NOT paraphrase, remove, summarize, translate, correct, or modify any words.
DO NOT change titles, times, capitalization, or wording.

Conference: {conference} {year}{city_text}
Date: {day}

Layout:
Vertical timeline layout.
White background with soft blue and gray accents.
Rounded cards aligned to a timeline.
Time on the left. Title, location and type on the right. 

===== SCHEDULE (VERBATIM TEXT, DO NOT MODIFY) =====
{schedule_text}
===== END OF SCHEDULE =====

Design style:
minimal, professional, academic conference poster
clear typography, balanced spacing
high resolution
NO creative rewriting of text
"""
    return prompt
