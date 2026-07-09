"""Per-model lighting colour/effect code maps for SetZoneColour writes.

The colour byte sent in a SetZoneColour (action 5, cmd 0x01F5) write is the
vendor's per-model ``LightColour.Value`` — a small 0-based index — NOT the
global ``Colours`` enum ordinal (0-67) that the controller reports back in
light STATE. The two numbering schemes are independent; this module only
covers the SEND side. Maps are transcribed from the decompiled
``LightColour`` struct, keyed by the ``Lighting.Models`` enum int.
"""

from __future__ import annotations

PER_MODEL_LIGHT_COLOURS: dict[int, dict[str, int]] = {
    0: {  # AstralPool SLX/FLX
        "Blue": 0, "Magenta": 1, "Red": 2, "Orange": 3, "Green": 4, "Aqua": 5,
        "White": 6, "Custom Colour": 7, "Custom Pattern": 8, "Rainbow": 9,
        "Ocean": 10, "Disco": 11,
    },
    1: {  # AstralPool Delta
        "Blue": 0, "Purple": 1, "Red": 2, "Orange": 3, "Yellow": 4, "Green": 5,
        "White": 6, "Custom Colour 1": 7, "Custom Colour 2": 8, "Disco": 9,
        "Smooth": 10, "Fade": 11,
    },
    2: {  # Hayward ColorLogic / CrystalLogic
        "Voodoo Lounge": 0, "Deep Blue Sea": 1, "Royal Blue": 2,
        "Afternoon Skies": 3, "Aqua Green": 4, "Emerald": 5, "White": 6,
        "Warm Red": 7, "Flamingo": 8, "Vivid Violet": 9, "Sangria": 10,
        "Twilight": 11, "Tranquillity": 12, "Gemstone": 13, "USA": 14,
        "Mardi Gras": 15, "Cool Cabaret": 16,
    },
    3: {  # Pentair IntelliBrite 5G
        "SAm": 0, "Party": 1, "Romance": 2, "Caribbean": 3, "American": 4,
        "California Sunset": 5, "Royal": 6, "Blue": 7, "Green": 8, "Red": 9,
        "White": 10, "Magenta": 11,
    },
    4: {  # JJ Electronics ColorSplash XG
        "Peruvian Paradise": 0, "Super Nova": 1, "Northern Lights": 2,
        "Tidal Wave": 3, "Patriot Dream": 4, "Desert Skies": 5, "Nova": 6,
        "Blue": 7, "Green": 8, "Red": 9, "White": 10, "Pink": 11,
    },
    5: {  # Spa Electrics
        "Blue": 0, "Magenta": 1, "Red": 2, "Lime": 3, "Green": 4, "Aqua": 5,
        "Cool White": 6, "Warm White": 7, "Slow Blend": 8, "Fast Blend": 9,
    },
    6: {  # LumiPower
        "Alpine White": 0, "Sky Blue": 1, "Cobalt Blue": 2, "Caribbean Blue": 3,
        "Spring Green": 4, "Emerald Green": 5, "Emerald Rose": 6, "Magenta": 7,
        "Violet": 8, "Slow Colour Splash": 9, "Fast Colour Splash": 10,
        "America the Beautiful": 11, "Fat Tuesday": 12, "Disco": 13,
    },
}


def available_light_colours(model: int | None) -> list[str]:
    """Return the colour/effect names valid for a lighting model."""
    if model is None:
        return []
    return list(PER_MODEL_LIGHT_COLOURS.get(model, {}).keys())


def resolve_light_colour(model: int | None, name: str) -> int | None:
    """Map a colour/effect name to its per-model wire value (case-insensitive).

    Returns None if the model is unknown or the name is not valid for it.
    """
    if model is None:
        return None
    table = PER_MODEL_LIGHT_COLOURS.get(model)
    if not table:
        return None
    if name in table:
        return table[name]
    lowered = name.strip().lower()
    for key, value in table.items():
        if key.lower() == lowered:
            return value
    return None
