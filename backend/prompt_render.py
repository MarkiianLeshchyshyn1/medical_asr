from pathlib import Path

from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent / "prompts"),
    autoescape=False
)

def render_system_prompt(language: str) -> str:
    template = env.get_template("medical_card/system_prompt.jinja")
    return template.render(language=language)

def render_user_prompt(transcript: str) -> str:
    template = env.get_template("medical_card/user_prompt.jinja")
    return template.render(transcript=transcript)


def render_dialogue_labeling_system_prompt() -> str:
    template = env.get_template("dialogue_labeling/system_prompt.jinja")
    return template.render()


def render_dialogue_labeling_user_prompt(numbered_transcript: str) -> str:
    template = env.get_template("dialogue_labeling/user_prompt.jinja")
    return template.render(numbered_transcript=numbered_transcript)
