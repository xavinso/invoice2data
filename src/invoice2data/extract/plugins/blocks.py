"""
Plugin to extract blocks from an invoice.
"""

import re
import logging
from .. import parsers

logger = logging.getLogger(__name__)

DEFAULT_OPTIONS = {"field_separator": r"\s+", "line_separator": r"\n"}
PARSERS_MAPPING = {"lines": parsers.lines, "regex": parsers.regex, "static": parsers.static}

def extract(self, content, output):
    """Try to extract blocks from an invoice"""

    # First apply default options.
    plugin_settings = DEFAULT_OPTIONS.copy()
    plugin_settings.update(self['blocks'])
    blocks = plugin_settings

    # Validate settings
    assert "start" in blocks, "Blocks start regex missing"
    assert "end" in blocks, "Blocks end regex missing"
    assert "block" in blocks, "Blocks end regex missing"

    start = re.search(blocks["start"], content)
    end = re.search(blocks["end"], content)

    if not start or not end:
        logger.warning("no blocks body found - start %s, end %s", start, end)
        return

    blocks_body = content[start.end() : end.start()]
    logger.debug(f"Block regex pattern = {blocks['block']}")

    blocks_output = []

    for block in re.findall(blocks['block'], blocks_body):
        if isinstance(block, tuple):
            block = block[0]

        logger.debug("START block content ========================")
        logger.debug(type(block))
        logger.debug("END block content ==========================")
        blocks_result = {}
        for k, v in blocks["fields"].items():
            if isinstance(v, dict):
                if "parser" in v:
                    if v["parser"] in PARSERS_MAPPING:
                        parser = PARSERS_MAPPING[v["parser"]]
                        value = parser.parse(self, v, block)
                        if value is not None:
                            blocks_result[k] = value
                        else:
                            logger.error("Failed to parse field %s with parser %s", k, v["parser"])
                    else:
                        logger.warning("Field %s has unknown parser %s set", k, v["parser"])
                else:
                    logger.warning("Field %s doesn't have parser specified", k)
            elif k.startswith("static_"):
                logger.debug("field=%s | static value=%s", k, v)
                blocks_result[k.replace("static_", "")] = v
            else:
                # Legacy syntax support (backward compatibility)
                logger.debug("field=%s | regexp=%s", k, v)
                
                result = None
                if k.startswith("sum_amount") and type(v) is list:
                    k = k[4:]
                    result = parsers.regex.parse(self, {"regex": v, "type": "float", "group": "sum"}, block,
                                                 True)
                elif k.startswith("date") or k.endswith("date"):
                    result = parsers.regex.parse(self, {"regex": v, "type": "date"}, block, True)
                elif k.startswith("amount"):
                    result = parsers.regex.parse(self, {"regex": v, "type": "float"}, block, True)
                else:
                    result = parsers.regex.parse(self, {"regex": v}, block, True)
                    # print(k, v)
                    # print(result)

                if result is None:
                    logger.warning("regexp for field %s didn't match", k)
                else:
                    blocks_result[k] = result

        blocks_output.append(blocks_result)

    output['blocks'] = blocks_output
