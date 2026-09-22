#!/usr/bin/env python3
"""Script to configure Vertex AI Memory Bank to extract and remember all user genres."""

import os
import sys
from dotenv import load_dotenv
import vertexai

load_dotenv()

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-f18f2b72d55a")
LOCATION = os.environ.get("MEMORY_BANK_LOCATION", "us-east1")
MEMORY_BANK_ID = os.environ.get("GOOGLE_CLOUD_MEMORY_BANK_ID", "1205497951623839744")


def configure_memory_bank(project: str, location: str, memory_bank_id: str):
    client = vertexai.Client(project=project, location=location)
    mb_name = f"projects/{project}/locations/{location}/reasoningEngines/{memory_bank_id}"

    config = {
        "context_spec": {
            "memory_bank_config": {
                "customization_configs": [
                    {
                        "memory_topics": [
                            {
                                "managed_memory_topic": {
                                    "managed_topic_enum": "USER_PERSONAL_INFO"
                                }
                            },
                            {
                                "managed_memory_topic": {
                                    "managed_topic_enum": "USER_PREFERENCES"
                                }
                            },
                            {
                                "managed_memory_topic": {
                                    "managed_topic_enum": "KEY_CONVERSATION_DETAILS"
                                }
                            },
                            {
                                "managed_memory_topic": {
                                    "managed_topic_enum": "EXPLICIT_INSTRUCTIONS"
                                }
                            },
                            {
                                "custom_memory_topic": {
                                    "label": "user_genres",
                                    "description": (
                                        "All movie, television, and narrative genres, subgenres, and tropes "
                                        "that the user expresses interest in, likes, dislikes, requests, enjoys, "
                                        "or watches (such as sci-fi, psychological thriller, murder mystery, "
                                        "cyber-noir, comedy, dark comedy, drama, period drama, crime, romance, "
                                        "fantasy, documentary, horror, action, animation, anthology, etc.). "
                                        "Ensure every genre preference and mentioned genre is captured."
                                    ),
                                }
                            },
                        ],
                        "generate_memories_examples": [
                            {
                                "conversation_source": {
                                    "events": [
                                        {
                                            "content": {
                                                "role": "user",
                                                "parts": [
                                                    {
                                                        "text": (
                                                            "I love mind-bending sci-fi thrillers and dystopian mysteries, "
                                                            "but I dislike romantic comedies."
                                                        )
                                                    }
                                                ],
                                            }
                                        },
                                        {
                                            "content": {
                                                "role": "model",
                                                "parts": [
                                                    {
                                                        "text": "Noted! I will recommend sci-fi and dystopian thrillers and avoid romantic comedies."
                                                    }
                                                ],
                                            }
                                        },
                                    ]
                                },
                                "generated_memories": [
                                    {
                                        "fact": "The user loves mind-bending sci-fi thrillers and dystopian mysteries."
                                    },
                                    {
                                        "fact": "The user dislikes romantic comedies."
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }

    print(f"Configuring Memory Bank {mb_name} with user_genres topic...")
    res = client.agent_engines.update(name=mb_name, config=config)
    print("Memory Bank configured successfully!")
    return res


if __name__ == "__main__":
    configure_memory_bank(PROJECT, LOCATION, MEMORY_BANK_ID)
