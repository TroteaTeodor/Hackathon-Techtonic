# Categories Jev sorts items into: key -> description. Jev picks the key whose
# description fits best, so keep descriptions short and non-overlapping.
CATEGORIES: dict[str, str] = {
    "task": "Something that needs to be done, an action item or to-do.",
    "bug": "A problem, defect, or something broken that needs fixing.",
    "idea": "A suggestion, feature idea, or proposal for something new.",
    "question": "Something someone wants answered or clarified.",
    "note": "Information to remember or reference, with no action needed.",
}
