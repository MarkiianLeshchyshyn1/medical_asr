from pathlib import Path

from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent / "promts"),
    autoescape=False
)

def render_system_prompt(language: str) -> str:
    template = env.get_template("system_prompt.jinja")
    return template.render(language=language)

def render_user_prompt(transcript: str) -> str:
    template = env.get_template("user_prompt.jinja")
    return template.render(transcript=transcript)
