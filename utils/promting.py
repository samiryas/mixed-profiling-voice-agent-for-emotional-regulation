from Introduction.models import BIG5_CHOICES, Constants, Player
import asyncio
import json
from jinja2 import Environment, FileSystemLoader
import os
from pydantic import BaseModel
from sqlalchemy.inspection import inspect

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = Environment(
    loader=FileSystemLoader(BASE_DIR)
)

def tojson_filter(obj):
    if isinstance(obj, BaseModel):
        return obj.model_dump_json()
    else:
        return json.dumps(obj, indent=2)

# Registriere den Filter in der Umgebung
env.filters['tojson'] = tojson_filter

def renderPrompt(path:str,data):
    template = env.get_template(path)
    return template.render(**data)
