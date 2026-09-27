import random
from typing import Tuple

PENALTY_TASKS_BY_TIER = {
    "LIGHT": [
        "Drop and do 40 strict pushups immediately with zero breaks.",
        "Take a 3-minute cold shower right now to reset your dopamine baseline.",
        "Write a 200-word post-mortem dissecting the exact moment you chose procrastination over your goal.",
        "Perform a 15-minute uninterrupted meditation session staring at a blank wall with no phone."
    ],
    "MEDIUM": [
        "100 burpees broken into sets of 25. Log the time.",
        "24-hour total ban on YouTube, Netflix, gaming, and entertainment media.",
        "Wake up at 5:30 AM tomorrow and complete 90 minutes of uninterrupted focused deep work before breakfast.",
        "Clean your entire workspace and physical room to surgical perfection before opening your computer again."
    ],
    "SEVERE": [
        "Full 36-hour digital dopamine detox: zero social media, zero algorithmic feeds, zero streaming.",
        "Run 5 kilometers outdoors regardless of the weather.",
        "Write a 1,000-word detailed essay on 'Why Potential Without Discipline is Merely Regret' and save it to your root workspace.",
        "Donate 2 hours of direct volunteering or manual chores without touching a screen."
    ],
    "CATASTROPHIC": [
        "STRIKE 3 CODE RED: 48-hour social media blackout + 200 pushups + draft an accountability confession letter to your primary peer.",
        "CRITICAL DISCIPLINE BANKRUPTCY: Complete a 10km run + 3-day media fasting + total workspace wipe down.",
        "MAXIMUM ACCOUNTABILITY PENALTY: Re-commit to all missed goals with double criteria for the next 30 days. No entertainment until first goal is verified."
    ]
}

ROAST_TEMPLATES = [
    "You set the bar yourself, looked at it for 30 days, and still found an excuse to crawl under it. Your future self is actively facepalming right now.",
    "Another month, another collection of well-crafted excuses. The gap between who you claim to be and what you actually execute is widening.",
    "If excuses burned calories, you'd be shredded. You gave 100% of your energy to rationalizing failure instead of finishing the work.",
    "You wrote down this goal with high motivation 4 weeks ago, then treated it like an optional suggestion. Discipline isn't a feeling, it's a contract you just breached.",
    "The world is full of people who 'almost' did what they promised. Congratulations on joining their ranks this month.",
    "Your evidence submission was either missing, paper-thin, or an insult to the word 'effort'. Look in the mirror: that's your only bottleneck.",
    "You didn't fail because the goal was too hard. You failed because you prioritized fleeting comfort over lasting achievement."
]

def generate_roast_and_penalty(goal_title: str, criteria: str, evidence: str, strikes: int) -> Tuple[str, str, str]:
    """
    Returns (severity, roast_text, penalty_task)
    """
    if strikes >= 2:  # About to be strike 3 or beyond
        severity = "CATASTROPHIC"
    elif strikes == 1:
        severity = "SEVERE"
    elif not evidence or len(evidence.strip()) < 10:
        severity = "MEDIUM"
    else:
        severity = "LIGHT"

    base_roast = random.choice(ROAST_TEMPLATES)
    custom_roast = (
        f"🚨 [GOAL FAILED: '{goal_title}'] 🚨\n"
        f"Criteria demanded: '{criteria}'\n"
        f"What you brought: '{evidence if evidence else 'ABSOLUTELY NOTHING'}'\n\n"
        f"🔥 THE VERDICT:\n{base_roast}"
    )

    if strikes >= 2:
        custom_roast += f"\n\n⚠️ CRITICAL WARNING: You now have {strikes + 1} STRIKES. You are on the verge of total accountability bankruptcy."

    penalty_task = random.choice(PENALTY_TASKS_BY_TIER[severity])
    return severity, custom_roast, penalty_task
