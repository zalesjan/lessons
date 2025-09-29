# utils/data.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MethodStep:
    title: str
    description: str
    durationMin: Optional[int] = None

@dataclass
class Method:
    id: str
    name: str
    summary: str = ""
    useFor: List[str] = None
    time: str = ""
    materials: List[str] = None
    steps: List[MethodStep] = None
    tips: List[str] = None
    videoUrl: Optional[str] = None

methods: List[Method] = [
    Method(
        id="jigsaw",
        name="Jigsaw",
        summary="Students master a sub-topic in expert groups, then re-form to teach one another.",
        useFor=["Complex topics", "Peer teaching", "Accountability"],
        time="30–60 min",
        materials=["Handouts", "Timer"],
        steps=[
            MethodStep("Form expert groups", "Assign sub-topics to each group."),
            MethodStep("Deepen expertise", "Read/discuss, prepare to teach.", 10),
            MethodStep("Re-group to jigsaw teams", "Each expert teaches their piece.", 15),
            MethodStep("Synthesis", "Teams build a shared summary."),
        ],
        tips=["Timebox tightly", "Provide note templates for novices"],
        videoUrl="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    ),
    Method(
        id="bus-stops",
        name="Bus Stops",
        summary="Teams rotate through station prompts, adding ideas and building on prior notes.",
        useFor=["Brainstorming", "Surfacing prior knowledge", "Idea elaboration"],
        time="20–40 min",
        materials=["Flipcharts", "Markers", "Tape"],
        steps=[
            MethodStep("Set stations", "Place prompts around the room."),
            MethodStep("Timed rotations", "Teams rotate & contribute at each stop.", 12),
            MethodStep("Gallery walk", "Read all sheets; note patterns or surprises."),
        ],
        tips=["Use clear, open prompts", "Encourage building—not repeating"],
        videoUrl="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    ),
    Method(
        id="line",
        name="Line (Human Continuum)",
        summary="Students place themselves along agree↔disagree and justify; they may move as arguments persuade.",
        useFor=["Argumentation", "Perspective taking", "Controversial issues"],
        time="15–30 min",
        materials=["Open space", "Statement(s)"],
        steps=[
            MethodStep("Pose statement", "E.g., “AI improves learning outcomes.”"),
            MethodStep("Line up", "Students choose a point & explain why.", 10),
            MethodStep("Shift & reflect", "Invite movement if persuaded by evidence."),
        ],
        tips=["Set discussion norms", "Invite counter-claims respectfully"],
        videoUrl="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    ),
]
