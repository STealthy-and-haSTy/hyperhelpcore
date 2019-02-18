import sublime

from .validictory import validate
from .validictory import SchemaError, ValidationError

from .common import log


###----------------------------------------------------------------------------


# The schema to validate that a help file entry in the "help_files" key of the
# help index is properly formattted.
_help_file_schema = {
    "type": "object",
    "required": True,

    # Any key is allowed, but all must have values which are arrays. The first
    # item in the array must be a string and the remainder must be topic
    # dictionaries.
    "additionalProperties": {
        "type": "array",
        "items": [ { "type": "string", "required": True } ],

        "additionalItems": {
            "type": "object",
            "properties": {
                "topic":   { "type": "string", "required": True  },
                "caption": { "type": "string", "required": False },
                "aliases": {
                    "type": "array",
                    "items": { "type": "string", "required": True },
                    "required": False
                }
            },
            "additionalProperties": False
        }
    }
}

# The schema to validate that the help table of contents in the "help_contents"
# key of the help index is properly formattted.
#
# NOTE: This recursively references itself in the children element. See the
# following line of code.
_help_contents_schema = {
    "type": "array",
    "required": False,

    # Items must be topic dictionaries or strings. Topic dictionaries require
    # a topic key but may also contain a caption key and a children key which
    # is an array that is recursively identical to this one.
    #
    # Values that are strings are expanded to be topic dictionaries with no
    # children and an inherited caption.
    "items": {
        "type": [
            {"type": "string", "required": True },
            {
                "type": "object",
                "required": True,
                "properties": {
                    "topic":   { "type": "string", "required": True },
                    "caption": { "type": "string", "required": False },

                    # This is recursive; see below
                    "children": "_help_contents_schema"
                },
                "additionalProperties": False
            }
        ]
    }
}

# The second type of item is a dictionary with a property that has the same
# format as the top level key.
_help_contents_schema["items"]["type"][1]["properties"]["children"] = _help_contents_schema

# The schema to validate that the list of external resources in the "externals"
# key of the help index is properly formatted.
_externals_schema = {
    "type": "object",
    "required": False,

    # Any key is allowed, but all must have values which are arrays. The first
    # item in the array must be a string and the remainder must be topic
    # dictionaries.
    "additionalProperties": {
        "type": "array",
        "items": [ { "type": "string", "required": True } ],

        "additionalItems": {
            "type": "object",
            "properties": {
                "topic":   { "type": "string", "required": True  },
                "caption": { "type": "string", "required": False },
                "aliases": {
                    "type": "array",
                    "items": { "type": "string", "required": True },
                    "required": False
                }
            },
            "additionalProperties": False
        }
    }
}

# The overall schema used to validate a hyperhelp index file.
_index_schema = {
    "type": "object",
    "properties": {
        "package":         { "type": "string", "required": True },
        "description":     { "type": "string", "required": False },
        "doc_root":        { "type": "string", "required": False },
        "default_caption": { "type": "string", "required": False },

        "help_files":    _help_file_schema,
        "help_contents": _help_contents_schema,
        "externals":     _externals_schema
    },
    "additionalProperties": False
}


###----------------------------------------------------------------------------


def validate_index(content, index_res):
    """
    Given a raw JSON string that represents a help index for a package, perform
    validation on it to ensure that it's valid JSON and also that it conforms
    to the appropriate index file help schema.

    Return a decoded dict object on success or None on failure.
    """
    def validate_fail(message, *args):
        log("Error validating index in '%s': %s", index_res, message % args)

    try:
        log("Loading help index from '%s'", index_res)
        raw_dict = sublime.decode_value(content)
    except:
        return validate_fail("Invalid JSON detected; unable to decode")

    try:
        validate(raw_dict, _index_schema)
        return raw_dict

    # The schema provided is itself broken.
    except SchemaError as error:
        return validate_fail("Invalid schema detected: %s", error)

    # One of the fields failed to validate. This generates extremely messy
    # output, but this can be fixed later.
    except ValidationError as error:
        return validate_fail("in %s: %s", error.fieldname, error)

    # Seems like validictory has a bug in which if you tell it to verify an
    # array has contents but the array is empty, it blows up. This can happen
    # if the array that provides the contents of a help file is empty, for
    # example.
    except Exception as error:
        return validate_fail("%s", error)


###----------------------------------------------------------------------------
