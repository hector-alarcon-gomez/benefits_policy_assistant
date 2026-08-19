ANSWER_TOOL = {
    "name": "report_answer",
    "description": "Return the structured answer to the employee question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": (
                    "The answer, grounded only in the provided policy excerpts. "
                    "If answer_type is 'declined', this MUST be: "
                    "'I don't know — this is not covered in the handbook.' "
                    "Use [] for policies when none are cited."
                ),
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "answer_type": {
                        "type": "string",
                        "enum": ["answered", "partial", "declined"],
                    },
                    "policies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "POL-NNN IDs cited. Empty array [] when no policies are cited.",
                    },
                    "constraints": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["conflict", "incomplete", "compound_eligibility", "derived", "other"],
                        },
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "retrieval_sufficient": {"type": "boolean"},
                },
                "required": ["answer_type", "policies", "constraints", "confidence", "retrieval_sufficient"],
            },
        },
        "required": ["answer", "metadata"],
    },
}
