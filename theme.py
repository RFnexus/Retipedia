import settings

ACCENTS = {
    "default": {"link": "33f", "nav": "0af", "cite": "5bf", "header": "09f", "bright": "0ff"},
    "blue":    {"link": "33f", "nav": "0af", "cite": "5bf", "header": "09f", "bright": "0ff"},
    "red":     {"link": "f44", "nav": "f66", "cite": "f99", "header": "f33", "bright": "f77"},
    "orange":  {"link": "f93", "nav": "fa5", "cite": "fc9", "header": "f83", "bright": "fb6"},
    "green":   {"link": "3d3", "nav": "5e5", "cite": "9e9", "header": "2c2", "bright": "6f6"},
}

_name = str(getattr(settings, "accent_color", "default") or "default").lower()
_palette = ACCENTS.get(_name, ACCENTS["default"])

LINK = _palette["link"]
NAV = _palette["nav"]
CITE = _palette["cite"]
HEADER = _palette["header"]
BRIGHT = _palette["bright"]
