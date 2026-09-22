#!/usr/bin/env python3
"""Seed script to populate Cloud Firestore with initial entertainment catalog titles.

NOTE: The project ID is intentionally hardcoded as a string.
On Agent Platform, google.auth.default() and GOOGLE_CLOUD_PROJECT resolve to the project number,
which breaks Firestore after deployment.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-f18f2b72d55a"
COLLECTION_NAME = "titles"

SEEDED_TITLES = [
    {
        "id": "severance",
        "title": "Severance",
        "format": "series",
        "genres": ["Sci-Fi", "Thriller", "Mystery"],
        "mood_tags": ["mind-bending", "dystopian", "tense", "workplace", "cerebral"],
        "duration_mins": 450,
        "episode_duration_mins": 50,
        "episode_count": 9,
        "synopsis": "Mark leads a team of office workers whose memories have been surgically divided between their work and personal lives. When a mysterious colleague appears outside of work, it begins a journey to discover the truth about their jobs.",
        "creator": "Dan Erickson",
        "year": 2022,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "black-mirror",
        "title": "Black Mirror",
        "format": "series",
        "genres": ["Sci-Fi", "Thriller", "Anthology"],
        "mood_tags": ["mind-bending", "dark", "dystopian", "technological", "provocative"],
        "duration_mins": 1400,
        "episode_duration_mins": 55,
        "episode_count": 27,
        "synopsis": "An anthology series exploring a twisted, high-tech multiverse where humanity's greatest innovations and darkest instincts collide.",
        "creator": "Charlie Brooker",
        "year": 2011,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "dark",
        "title": "Dark",
        "format": "series",
        "genres": ["Sci-Fi", "Thriller", "Mystery", "Drama"],
        "mood_tags": ["mind-bending", "complex", "time-travel", "dark", "atmospheric"],
        "duration_mins": 1430,
        "episode_duration_mins": 55,
        "episode_count": 26,
        "synopsis": "A family saga with a supernatural twist, set in a German town where the disappearance of two young children exposes the relationships among four families across three generations.",
        "creator": "Baran bo Odar, Jantje Friese",
        "year": 2017,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "arrival",
        "title": "Arrival",
        "format": "movie",
        "genres": ["Sci-Fi", "Drama", "Mystery"],
        "mood_tags": ["mind-bending", "philosophical", "emotional", "cerebral", "atmospheric"],
        "duration_mins": 116,
        "episode_duration_mins": 116,
        "episode_count": 1,
        "synopsis": "A linguist works with the military to communicate with alien lifeforms after twelve mysterious spacecraft appear around the world.",
        "creator": "Denis Villeneuve",
        "year": 2016,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "interstellar",
        "title": "Interstellar",
        "format": "movie",
        "genres": ["Sci-Fi", "Drama", "Adventure"],
        "mood_tags": ["epic", "emotional", "visual", "scientific", "mind-bending"],
        "duration_mins": 169,
        "episode_duration_mins": 169,
        "episode_count": 1,
        "synopsis": "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot is tasked to pilot a spacecraft, along with a team of researchers, to find a new planet for humans.",
        "creator": "Christopher Nolan",
        "year": 2014,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "the-bear",
        "title": "The Bear",
        "format": "series",
        "genres": ["Comedy", "Drama"],
        "mood_tags": ["intense", "fast-paced", "heartfelt", "culinary", "bingeable"],
        "duration_mins": 840,
        "episode_duration_mins": 30,
        "episode_count": 28,
        "synopsis": "A young fine-dining chef returns home to Chicago to run his family's Italian beef sandwich shop after a tragic loss.",
        "creator": "Christopher Storer",
        "year": 2022,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "shogun",
        "title": "Shōgun",
        "format": "miniseries",
        "genres": ["Drama", "Action", "History"],
        "mood_tags": ["epic", "political", "immersive", "dramatic", "visual"],
        "duration_mins": 600,
        "episode_duration_mins": 60,
        "episode_count": 10,
        "synopsis": "When a mysterious European ship is found marooned in a nearby fishing village, Lord Yoshii Toranaga discovers secrets that could tip the scales of power in feudal Japan.",
        "creator": "Rachel Kondo, Justin Marks",
        "year": 2024,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "glass-onion",
        "title": "Glass Onion: A Knives Out Mystery",
        "format": "movie",
        "genres": ["Comedy", "Crime", "Mystery"],
        "mood_tags": ["clever", "entertaining", "whodunit", "witty", "escapist"],
        "duration_mins": 139,
        "episode_duration_mins": 139,
        "episode_count": 1,
        "synopsis": "Master detective Benoit Blanc travels to Greece to peel back the layers of a mystery involving a tech billionaire and his eclectic crew of friends.",
        "creator": "Rian Johnson",
        "year": 2022,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "chernobyl",
        "title": "Chernobyl",
        "format": "miniseries",
        "genres": ["Drama", "History", "Thriller"],
        "mood_tags": ["gripping", "dark", "historical", "haunting", "tense"],
        "duration_mins": 300,
        "episode_duration_mins": 60,
        "episode_count": 5,
        "synopsis": "In April 1986, an explosion at the Chernobyl nuclear power plant in the USSR becomes one of the world's worst man-made catastrophes.",
        "creator": "Craig Mazin",
        "year": 2019,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "only-murders-in-the-building",
        "title": "Only Murders in the Building",
        "format": "series",
        "genres": ["Comedy", "Crime", "Mystery"],
        "mood_tags": ["cozy", "witty", "charming", "bingeable", "podcast"],
        "duration_mins": 1050,
        "episode_duration_mins": 35,
        "episode_count": 30,
        "synopsis": "Three strangers who share an obsession with true crime podcasts suddenly find themselves wrapped up in one when a gruesome death occurs inside their Upper West Side apartment building.",
        "creator": "Steve Martin, John Hoffman",
        "year": 2021,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
]


def seed_database():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(COLLECTION_NAME)

    print(f"Seeding {len(SEEDED_TITLES)} items into collection '{COLLECTION_NAME}'...")
    batch = db.batch()
    for item in SEEDED_TITLES:
        doc_id = item["id"]
        doc_ref = collection_ref.document(doc_id)
        batch.set(doc_ref, item)

    batch.commit()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
