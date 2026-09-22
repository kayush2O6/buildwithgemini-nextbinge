# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Domain tools for NextBinge entertainment concierge backed by Cloud Firestore."""

import base64
import logging
import os
import re
from typing import Any, Dict, List, Optional
from google.cloud import firestore
import httpx
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# NOTE: The project ID is intentionally hardcoded as a string.
# On Agent Platform, google.auth.default() and GOOGLE_CLOUD_PROJECT resolve to the project number,
# which breaks Firestore after deployment.
PROJECT_ID = "qwiklabs-gcp-03-f18f2b72d55a"
COLLECTION_NAME = "titles"
BUCKET_NAME = "nextbinge-media"

_db_instance: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    """Lazy loader for Firestore client with hardcoded project ID."""
    global _db_instance
    if _db_instance is None:
        _db_instance = firestore.Client(project=PROJECT_ID)
    return _db_instance


# Local fallback catalog for tests and offline resilience
CATALOG = [
    {
        "id": "severance",
        "title": "Severance",
        "year": 2022,
        "format": "series",
        "genres": ["Sci-Fi", "Thriller", "Mystery"],
        "episode_duration_mins": 50,
        "episode_count": 9,
        "duration_mins": 450,
        "total_runtime_mins": 450,
        "mood_tags": ["mind-bending", "dystopian", "tense", "eerie", "corporate"],
        "synopsis": "Mark leads a team of office workers whose memories have been surgically divided between their work and personal lives.",
        "creator": "Dan Erickson",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "black-mirror",
        "title": "Black Mirror",
        "year": 2011,
        "format": "series",
        "genres": ["Sci-Fi", "Thriller", "Anthology"],
        "episode_duration_mins": 55,
        "episode_count": 27,
        "duration_mins": 1400,
        "total_runtime_mins": 1400,
        "mood_tags": ["mind-bending", "dark", "satirical", "speculative", "thought-provoking"],
        "synopsis": "An anthology series exploring a twisted, high-tech multiverse where humanity's greatest innovations and darkest instincts collide.",
        "creator": "Charlie Brooker",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "dark",
        "title": "Dark",
        "year": 2017,
        "format": "series",
        "genres": ["Sci-Fi", "Mystery", "Thriller", "Drama"],
        "episode_duration_mins": 55,
        "episode_count": 26,
        "duration_mins": 1430,
        "total_runtime_mins": 1430,
        "mood_tags": ["mind-bending", "atmospheric", "complex", "brooding", "time-travel"],
        "synopsis": "A family saga with a supernatural twist set in a German town where two children disappear, exposing the double lives of four families.",
        "creator": "Baran bo Odar",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "arrival",
        "title": "Arrival",
        "year": 2016,
        "format": "movie",
        "genres": ["Sci-Fi", "Drama", "Mystery"],
        "episode_duration_mins": 116,
        "episode_count": 1,
        "duration_mins": 116,
        "total_runtime_mins": 116,
        "mood_tags": ["mind-bending", "emotional", "linguistics", "hopeful", "awe-inspiring"],
        "synopsis": "A linguist works with the military to communicate with alien lifeforms after mysterious spacecraft appear around the world.",
        "creator": "Denis Villeneuve",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "the-bear",
        "title": "The Bear",
        "year": 2022,
        "format": "series",
        "genres": ["Comedy", "Drama"],
        "episode_duration_mins": 30,
        "episode_count": 28,
        "duration_mins": 840,
        "total_runtime_mins": 840,
        "mood_tags": ["intense", "fast-paced", "heartfelt", "culinary", "bingeable"],
        "synopsis": "A young fine-dining chef returns home to Chicago to run his family's Italian beef sandwich shop after a tragic loss.",
        "creator": "Christopher Storer",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "chernobyl",
        "title": "Chernobyl",
        "year": 2019,
        "format": "miniseries",
        "genres": ["Drama", "History", "Thriller"],
        "episode_duration_mins": 60,
        "episode_count": 5,
        "duration_mins": 300,
        "total_runtime_mins": 300,
        "mood_tags": ["gripping", "grim", "suspenseful", "masterpiece", "bingeable"],
        "synopsis": "In April 1986, an explosion at the Chernobyl nuclear power plant becomes one of the world's worst man-made catastrophes.",
        "creator": "Craig Mazin",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "the-queens-gambit",
        "title": "The Queen's Gambit",
        "year": 2020,
        "format": "miniseries",
        "genres": ["Drama", "History"],
        "episode_duration_mins": 55,
        "episode_count": 7,
        "duration_mins": 385,
        "total_runtime_mins": 385,
        "mood_tags": ["stylish", "compelling", "satisfying", "bingeable", "triumphant"],
        "synopsis": "Orphaned at the tender age of nine, introverted prodigy Beth Harmon discovers and masters the game of chess in 1960s USA.",
        "creator": "Scott Frank",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "ex-machina",
        "title": "Ex Machina",
        "year": 2014,
        "format": "movie",
        "genres": ["Sci-Fi", "Drama", "Thriller"],
        "episode_duration_mins": 108,
        "episode_count": 1,
        "duration_mins": 108,
        "total_runtime_mins": 108,
        "mood_tags": ["cerebral", "sleek", "tense", "AI", "philosophical"],
        "synopsis": "A programmer is invited by his company's CEO to administer a Turing test to an intelligent humanoid robot.",
        "creator": "Alex Garland",
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "inception",
        "title": "Inception",
        "year": 2010,
        "format": "movie",
        "genres": ["Sci-Fi", "Action", "Thriller"],
        "episode_duration_mins": 148,
        "episode_count": 1,
        "duration_mins": 148,
        "total_runtime_mins": 148,
        "mood_tags": ["mind-bending", "heist", "cerebral", "complex", "subconscious"],
        "synopsis": "A skilled thief who steals corporate secrets through dream-sharing technology is tasked with the reverse: planting an idea into the mind of a C.E.O.",
        "creator": "Christopher Nolan",
        "lead_studio": "Warner Bros",
        "story_archetype": "Pursuit",
        "rotten_tomatoes": 86,
        "audience_score": 93,
        "world_gross": 825.5,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "the-dark-knight",
        "title": "The Dark Knight",
        "year": 2008,
        "format": "movie",
        "genres": ["Action", "Crime", "Thriller", "Drama"],
        "episode_duration_mins": 152,
        "episode_count": 1,
        "duration_mins": 152,
        "total_runtime_mins": 152,
        "mood_tags": ["dark", "gripping", "masterpiece", "chaos", "psychological"],
        "synopsis": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
        "creator": "Christopher Nolan",
        "lead_studio": "Warner Bros",
        "story_archetype": "Rivalry",
        "rotten_tomatoes": 94,
        "audience_score": 96,
        "world_gross": 1004.6,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "toy-story-3",
        "title": "Toy Story 3",
        "year": 2010,
        "format": "movie",
        "genres": ["Animation", "Adventure", "Comedy", "Family"],
        "episode_duration_mins": 103,
        "episode_count": 1,
        "duration_mins": 103,
        "total_runtime_mins": 103,
        "mood_tags": ["heartfelt", "nostalgic", "family-friendly", "emotional", "quest"],
        "synopsis": "The toys are mistakenly delivered to a day-care center right before Andy leaves for college, and Woody must convince the toys that they were not abandoned and to return home.",
        "creator": "Lee Unkrich",
        "lead_studio": "Disney",
        "story_archetype": "Quest",
        "rotten_tomatoes": 99,
        "audience_score": 91,
        "world_gross": 1063.2,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "up",
        "title": "Up",
        "year": 2009,
        "format": "movie",
        "genres": ["Animation", "Adventure", "Comedy", "Drama"],
        "episode_duration_mins": 96,
        "episode_count": 1,
        "duration_mins": 96,
        "total_runtime_mins": 96,
        "mood_tags": ["uplifting", "heartwarming", "poignant", "adventurous", "quest"],
        "synopsis": "78-year-old Carl Fredricksen travels to Paradise Falls in his house equipped with balloons, inadvertently taking young Wilderness Explorer Russell along.",
        "creator": "Pete Docter",
        "lead_studio": "Disney",
        "story_archetype": "Quest",
        "rotten_tomatoes": 98,
        "audience_score": 86,
        "world_gross": 731.3,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "the-kings-speech",
        "title": "The King's Speech",
        "year": 2010,
        "format": "movie",
        "genres": ["Biography", "Drama", "History"],
        "episode_duration_mins": 118,
        "episode_count": 1,
        "duration_mins": 118,
        "total_runtime_mins": 118,
        "mood_tags": ["inspiring", "underdog", "triumphant", "historical", "masterpiece"],
        "synopsis": "The story of King George VI, his unexpected accession to the British throne, and the speech therapist who helped the unsure monarch overcome his stammer.",
        "creator": "Tom Hooper",
        "lead_studio": "Independent",
        "story_archetype": "Underdog",
        "rotten_tomatoes": 95,
        "audience_score": 93,
        "world_gross": 414.2,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "juno",
        "title": "Juno",
        "year": 2007,
        "format": "movie",
        "genres": ["Comedy", "Drama"],
        "episode_duration_mins": 96,
        "episode_count": 1,
        "duration_mins": 96,
        "total_runtime_mins": 96,
        "mood_tags": ["witty", "quirky", "coming-of-age", "heartfelt", "indie"],
        "synopsis": "Faced with an unplanned pregnancy, an offbeat high schooler makes a selfless decision regarding the unborn child and embarks on a poignant maturation journey.",
        "creator": "Jason Reitman",
        "lead_studio": "Fox",
        "story_archetype": "Maturation",
        "rotten_tomatoes": 94,
        "audience_score": 89,
        "world_gross": 231.4,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "superbad",
        "title": "Superbad",
        "year": 2007,
        "format": "movie",
        "genres": ["Comedy"],
        "episode_duration_mins": 113,
        "episode_count": 1,
        "duration_mins": 113,
        "total_runtime_mins": 113,
        "mood_tags": ["hilarious", "coming-of-age", "irreverent", "wild", "friendship"],
        "synopsis": "Two co-dependent high school seniors are forced to deal with separation anxiety after their plan to stage a booze-soaked party goes wildly awry.",
        "creator": "Greg Mottola",
        "lead_studio": "Sony",
        "story_archetype": "Comedy",
        "rotten_tomatoes": 88,
        "audience_score": 87,
        "world_gross": 169.9,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "the-hurt-locker",
        "title": "The Hurt Locker",
        "year": 2009,
        "format": "movie",
        "genres": ["Drama", "Thriller", "War"],
        "episode_duration_mins": 131,
        "episode_count": 1,
        "duration_mins": 131,
        "total_runtime_mins": 131,
        "mood_tags": ["intense", "suspenseful", "visceral", "gritty", "acclaimed"],
        "synopsis": "During the Iraq War, a sergeant assigned to an Army bomb squad is put at odds with his squad mates due to his maverick way of handling work.",
        "creator": "Kathryn Bigelow",
        "lead_studio": "Independent",
        "story_archetype": "Pursuit",
        "rotten_tomatoes": 97,
        "audience_score": 83,
        "world_gross": 49.2,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "avatar",
        "title": "Avatar",
        "year": 2009,
        "format": "movie",
        "genres": ["Action", "Adventure", "Sci-Fi", "Fantasy"],
        "episode_duration_mins": 162,
        "episode_count": 1,
        "duration_mins": 162,
        "total_runtime_mins": 162,
        "mood_tags": ["spectacular", "visual-masterpiece", "epic", "alien-world", "blockbuster"],
        "synopsis": "A paraplegic Marine dispatched to the lush alien moon of Pandora on a unique mission becomes torn between following his orders and protecting the world he feels is his home.",
        "creator": "James Cameron",
        "lead_studio": "Fox",
        "story_archetype": "Transformation",
        "rotten_tomatoes": 83,
        "audience_score": 92,
        "world_gross": 2781.5,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "transformers",
        "title": "Transformers",
        "year": 2007,
        "format": "movie",
        "genres": ["Action", "Sci-Fi", "Adventure"],
        "episode_duration_mins": 144,
        "episode_count": 1,
        "duration_mins": 144,
        "total_runtime_mins": 144,
        "mood_tags": ["explosive", "popcorn", "action-spectacle", "blockbuster", "robots"],
        "synopsis": "An ancient struggle between two Cybertronian warrior clans, the heroic Autobots and the villainous Decepticons, comes to Earth with high stakes.",
        "creator": "Michael Bay",
        "lead_studio": "Paramount",
        "story_archetype": "Monster Force",
        "rotten_tomatoes": 57,
        "audience_score": 89,
        "world_gross": 709.7,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "ratatouille",
        "title": "Ratatouille",
        "year": 2007,
        "format": "movie",
        "genres": ["Animation", "Comedy", "Family"],
        "episode_duration_mins": 111,
        "episode_count": 1,
        "duration_mins": 111,
        "total_runtime_mins": 111,
        "mood_tags": ["charming", "culinary", "heartwarming", "family-friendly", "underdog"],
        "synopsis": "A rat who can cook makes an unusual alliance with a young kitchen worker at a famous Paris restaurant to pursue his culinary passion.",
        "creator": "Brad Bird",
        "lead_studio": "Disney",
        "story_archetype": "Transformation",
        "rotten_tomatoes": 97,
        "audience_score": 84,
        "world_gross": 623.7,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
    {
        "id": "warrior",
        "title": "Warrior",
        "year": 2011,
        "format": "movie",
        "genres": ["Action", "Drama", "Sport"],
        "episode_duration_mins": 140,
        "episode_count": 1,
        "duration_mins": 140,
        "total_runtime_mins": 140,
        "mood_tags": ["intense", "emotional", "underdog", "grit", "brotherhood"],
        "synopsis": "The youngest son of an alcoholic former boxer returns home to train for a mixed martial arts tournament, putting him on a collision course with his estranged older brother.",
        "creator": "Gavin O'Connor",
        "lead_studio": "Lionsgate",
        "story_archetype": "Underdog",
        "rotten_tomatoes": 83,
        "audience_score": 93,
        "world_gross": 23.1,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    },
]

_WATCHED_TITLES: Dict[str, Dict[str, Any]] = {}


def _fetch_all_titles() -> List[Dict[str, Any]]:
    """Retrieve all titles from Firestore collection, falling back to local catalog if needed."""
    try:
        db = _get_db()
        docs = db.collection(COLLECTION_NAME).stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            if "id" not in d:
                d["id"] = doc.id
            results.append(d)
        if results:
            return results
    except Exception as e:
        logger.warning("Could not query Firestore collection %s: %s", COLLECTION_NAME, e)

    return [dict(item) for item in CATALOG]


def search_titles(
    query: Optional[str] = None,
    genre: Optional[str] = None,
    format: Optional[str] = None,
    max_duration_mins: Optional[int] = None,
    mood: Optional[str] = None,
    exclude_watched: bool = True,
) -> Dict[str, Any]:
    """Search movies and TV series in Cloud Firestore matching genre, format, time limits, and mood tags.

    Args:
        query: Free-text keyword search across title, synopsis, creator, and tags.
        genre: Genre filter (e.g. 'sci-fi', 'thriller', 'comedy', 'drama', 'crime').
        format: Format filter ('movie', 'series', 'miniseries').
        max_duration_mins: Maximum duration in minutes. For series, compares against episode_duration_mins; for movies, total runtime.
        mood: Mood or vibe filter (e.g. 'mind-bending', 'dark', 'bingeable', 'philosophical').
        exclude_watched: If True, filters out items marked as watched.

    Returns:
        Dict with status, count, and list of matching titles with detailed metadata.
    """
    raw_titles = _fetch_all_titles()
    matches = []

    for item in raw_titles:
        title_key = item.get("title", "").strip().lower()

        # Normalization
        duration = item.get("duration_mins", item.get("total_runtime_mins", 0))
        item["duration_mins"] = duration
        item["total_runtime_mins"] = duration
        if "episode_duration_mins" not in item:
            item["episode_duration_mins"] = duration if item.get("format") == "movie" else 45

        # Check watched status
        is_watched = item.get("watched", False) or (title_key in _WATCHED_TITLES)
        if exclude_watched and is_watched:
            continue

        # Format filter
        item_format = item.get("format", "").lower()
        if format and item_format != format.lower():
            continue

        # Genre filter
        genres = [g.lower() for g in item.get("genres", [])]
        if genre:
            genre_clean = genre.lower().strip()
            if genre_clean in genres:
                matched_genre = True
            elif any(genre_clean in g or g in genre_clean for g in genres):
                matched_genre = True
            else:
                tokens = [t.strip() for t in genre_clean.replace(",", " ").split() if len(t.strip()) > 2]
                matched_genre = any(any(t == g or t in g for t in tokens) for g in genres)
            if not matched_genre:
                continue

        # Mood filter
        mood_tags = [m.lower() for m in item.get("mood_tags", [])]
        if mood and not any(mood.lower() in m for m in mood_tags):
            continue

        # Max duration filter
        if max_duration_mins is not None:
            unit_duration = (
                item["episode_duration_mins"]
                if item_format in ("series", "miniseries")
                else item["duration_mins"]
            )
            if unit_duration > max_duration_mins:
                continue

        # Free-text query filter
        if query:
            q = query.lower()
            text_corpus = (
                f"{item.get('title', '')} {item.get('synopsis', '')} {item.get('creator', '')} "
                f"{item.get('lead_studio', '')} {item.get('story_archetype', '')} "
                f"{' '.join(item.get('genres', []))} {' '.join(item.get('mood_tags', []))}"
            ).lower()
            if q not in text_corpus:
                continue

        matches.append(item)

    return {
        "status": "success",
        "count": len(matches),
        "results": matches,
    }


def mark_as_watched(
    title: str,
    rating: Optional[float] = None,
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """Mark a movie or TV series as watched in Cloud Firestore and record viewer rating and feedback.

    Args:
        title: The exact or approximate title of the movie or show.
        rating: Optional rating score from 1.0 to 10.0.
        feedback: Optional notes or impressions (e.g. 'loved the plot twist', 'found it too slow').

    Returns:
        Dict with status, title, recorded_rating, and total watched count.
    """
    clean_title = title.strip()
    key = clean_title.lower()
    _WATCHED_TITLES[key] = {
        "title": clean_title,
        "rating": rating,
        "feedback": feedback,
    }

    firestore_updated = False
    try:
        db = _get_db()
        coll = db.collection(COLLECTION_NAME)
        for doc in coll.stream():
            data = doc.to_dict()
            if data.get("title", "").strip().lower() == key or doc.id.lower() == key:
                doc.reference.update({
                    "watched": True,
                    "user_rating": rating,
                    "user_feedback": feedback,
                })
                firestore_updated = True
                break
    except Exception as e:
        logger.warning("Could not update Firestore document for '%s': %s", clean_title, e)

    return {
        "status": "success",
        "message": f"Recorded '{clean_title}' as watched.",
        "title": clean_title,
        "rating": rating,
        "feedback": feedback,
        "firestore_updated": firestore_updated,
        "total_watched_count": len(_WATCHED_TITLES),
    }


def add_title_to_catalog(
    title: str,
    format: str,
    genres: List[str],
    synopsis: str,
    duration_mins: int = 120,
    episode_duration_mins: int = 45,
    episode_count: int = 1,
    mood_tags: Optional[List[str]] = None,
    creator: str = "",
    year: int = 2024,
) -> Dict[str, Any]:
    """Add a new movie or TV series to the Firestore entertainment catalog.

    Args:
        title: Title of the movie or show.
        format: Format ('movie', 'series', 'miniseries').
        genres: List of genre strings (e.g. ['Sci-Fi', 'Thriller']).
        synopsis: Short synopsis or overview.
        duration_mins: Total runtime in minutes for movies, or full season runtime.
        episode_duration_mins: Runtime per episode.
        episode_count: Number of episodes (1 for single movies).
        mood_tags: Optional list of vibe tags (e.g. ['mind-bending', 'dark']).
        creator: Director, showrunner, or creator.
        year: Release year.

    Returns:
        Dict with status, message, and added title details.
    """
    clean_title = title.strip()
    slug = clean_title.lower().replace(" ", "-").replace(":", "").replace("'", "")
    doc_data = {
        "id": slug,
        "title": clean_title,
        "format": format.lower(),
        "genres": genres,
        "mood_tags": mood_tags or [],
        "duration_mins": duration_mins,
        "total_runtime_mins": duration_mins,
        "episode_duration_mins": episode_duration_mins,
        "episode_count": episode_count,
        "synopsis": synopsis,
        "creator": creator,
        "year": year,
        "watched": False,
        "user_rating": None,
        "user_feedback": None,
    }

    try:
        db = _get_db()
        db.collection(COLLECTION_NAME).document(slug).set(doc_data)
        return {
            "status": "success",
            "message": f"Successfully added '{clean_title}' to Firestore collection '{COLLECTION_NAME}'.",
            "title": doc_data,
        }
    except Exception as e:
        logger.error("Failed to add '%s' to Firestore: %s", clean_title, e)
        return {
            "status": "error",
            "message": f"Failed to add '{clean_title}' to Firestore: {str(e)}",
        }


def calculate_time_fit(
    available_minutes: int,
    title: str,
    episodes_to_watch: int = 1,
) -> Dict[str, Any]:
    """Calculate whether a movie or a batch of episodes fits within an available time slot.

    Args:
        available_minutes: Total minutes the viewer has available.
        title: Name of the movie or show.
        episodes_to_watch: Number of episodes the user wants to watch (default 1; ignored for single movies).

    Returns:
        Dict with fits (bool), required_minutes, available_minutes, difference_minutes, and advice.
    """
    if available_minutes <= 0:
        return {
            "status": "error",
            "message": "Available minutes must be greater than zero.",
        }

    raw_titles = _fetch_all_titles()
    matched = next(
        (item for item in raw_titles if item.get("title", "").strip().lower() == title.strip().lower()),
        None,
    )

    if not matched:
        required_mins = 45 * episodes_to_watch
    else:
        if matched.get("format") == "movie":
            required_mins = matched.get("duration_mins", matched.get("total_runtime_mins", 120))
            episodes_to_watch = 1
        else:
            per_ep = matched.get("episode_duration_mins", 45)
            required_mins = per_ep * episodes_to_watch

    diff = available_minutes - required_mins
    fits = diff >= 0

    if fits:
        advice = (
            f"Fits comfortably with {diff} minutes to spare!"
            if diff > 0
            else "Fits exactly to the minute!"
        )
    else:
        advice = (
            f"Exceeds available time by {abs(diff)} minutes. "
            "Consider watching fewer episodes or selecting a shorter title."
        )

    return {
        "status": "success",
        "title": matched["title"] if matched else title,
        "fits": fits,
        "required_minutes": required_mins,
        "available_minutes": available_minutes,
        "difference_minutes": diff,
        "episodes": episodes_to_watch,
        "advice": advice,
    }


def fetch_live_title_details(title: str) -> Dict[str, Any]:
    """Fetch live real-world streaming/broadcast platform, episode runtime, ratings, and official poster art.

    Args:
        title: Name of the TV show or movie to look up (e.g. 'Fallout', 'Succession', 'Severance').

    Returns:
        Dict with status, title, year, genres, episode_runtime_mins, platform, rating, poster_url, summary, and show_status.
    """
    clean_title = title.strip()
    if not clean_title:
        return {"status": "error", "message": "Title cannot be empty."}

    try:
        url = f"https://api.tvmaze.com/singlesearch/shows?q={clean_title}"
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 404:
            return {
                "status": "not_found",
                "message": f"Could not find live details for '{clean_title}'.",
            }
        resp.raise_for_status()
        data = resp.json()

        raw_summary = data.get("summary") or ""
        clean_summary = re.sub(r"<[^>]+>", "", raw_summary).strip()

        images = data.get("image") or {}
        poster_url = images.get("original") or images.get("medium")

        platform = (
            (data.get("webChannel") or {}).get("name")
            or (data.get("network") or {}).get("name")
            or "Unknown"
        )

        rating_info = data.get("rating") or {}
        user_score = rating_info.get("average")

        premiered = data.get("premiered") or ""
        release_year = (
            int(premiered[:4])
            if len(premiered) >= 4 and premiered[:4].isdigit()
            else None
        )

        return {
            "status": "success",
            "title": data.get("name", clean_title),
            "year": release_year,
            "genres": data.get("genres", []),
            "episode_runtime_mins": data.get("averageRuntime") or data.get("runtime") or 45,
            "platform": platform,
            "rating": user_score,
            "poster_url": poster_url,
            "summary": clean_summary,
            "show_status": data.get("status", "Unknown"),
        }
    except Exception as e:
        logger.warning("Error fetching live show details for '%s': %s", clean_title, e)
        return {
            "status": "error",
            "message": f"Failed to fetch live show details for '{clean_title}': {str(e)}",
        }


def search_entertainment_guide(query: str) -> str:
    """Search the NextBinge entertainment knowledge guide for deep analyses, lore, themes, episode breakdowns, and science behind movies and series.

    Use this tool when users ask in-depth questions about a film or TV show's plot,
    themes, scientific concepts (like time travel in Dark or linguistic relativity in Arrival),
    reactor physics in Chernobyl, behind-the-scenes lore, or episode-specific explanations.

    Args:
        query: Search query, film/show title, concept, or question (e.g. '33-year cycle in Dark', 'ending of Arrival', 'RBMK reactor flaw in Chernobyl').

    Returns:
        Curated reference passages from the master entertainment guide.
    """
    clean_query = query.strip()
    if not clean_query:
        return "Please provide a search query or title to look up in the entertainment guide."

    corpus_name = os.getenv(
        "RAG_CORPUS_NAME",
        "projects/539437831919/locations/us-central1/ragCorpora/2522077363978633216",
    )
    location = os.getenv("RAG_LOCATION", "us-central1")

    try:
        import vertexai
        from vertexai.preview import rag

        vertexai.init(project=PROJECT_ID, location=location)
        resp = rag.retrieval_query(
            text=clean_query,
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=4),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        if not passages:
            return f"No relevant entertainment guide passages found for '{clean_query}'."

        return "\n\n---\n\n".join(passages)
    except Exception as e:
        logger.warning("RAG retrieval query failed for '%s': %s", clean_query, e)
        return f"Entertainment guide retrieval unavailable: {e}"


async def generate_title_poster(
    title: str,
    visual_description: str = "",
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generate high-quality concept art or movie/series poster for an entertainment title using Gemini 3.1 Flash-Lite Image in the global region.

    Saves the image as a session artifact via tool_context (so it renders in the Playground's Artifacts panel)
    and uploads the image bytes directly to public Cloud Storage, returning the public HTTPS URL.

    Args:
        title: Title of the film, series, or entertainment concept to generate art for (e.g. 'Severance', 'Dark', 'Interstellar').
        visual_description: Optional aesthetic directions, mood, lighting, color palette, or scene details (e.g. 'moody blue office labyrinth with eerie fluorescent lights').
        tool_context: Execution context for saving the artifact in the session.

    Returns:
        The public HTTPS URL of the uploaded image (https://storage.googleapis.com/nextbinge-media/posters/<filename>).
    """
    clean_title = title.strip()
    if not clean_title:
        return "Please provide a title to generate poster artwork for."

    full_prompt = f"Cinematic movie or series poster and key visual art for '{clean_title}'."
    if visual_description and visual_description.strip():
        full_prompt += f" Visual aesthetic and mood: {visual_description.strip()}."
    full_prompt += " Highly detailed, theatrical composition, dramatic cinematic lighting, professional movie poster quality."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return f"Failed to generate poster art for '{clean_title}': model returned no image content."

        ext = "png" if "png" in mime_type else "jpg"
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_title.lower()).strip("_") or "artwork"
        filename = f"{safe_slug}_poster.{ext}"

        # 1. Save artifact to tool_context so it appears in Playground's Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                await tool_context.save_artifact(filename=filename, artifact=artifact_part)
                logger.info("Saved image artifact '%s' to tool_context", filename)
            except Exception as e:
                logger.warning("Could not save artifact in tool_context: %s", e)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        from google.cloud import storage

        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        object_name = f"posters/{filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"
        logger.info("Uploaded generated poster for '%s' to %s", clean_title, public_url)
        return public_url

    except Exception as e:
        logger.error("Error generating title poster for '%s': %s", clean_title, e)
        return f"Image generation failed for '{clean_title}': {e}"


async def generate_title_video(
    title: str,
    scene_description: str = "",
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generate a short cinematic teaser video for a movie or TV series using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the video as a session artifact via tool_context (so it renders in the Playground's Artifacts panel)
    and uploads the video bytes directly to the public Cloud Storage bucket, returning the public HTTPS URL.

    Args:
        title: Title of the film, series, or entertainment concept to generate a video clip for (e.g. 'Severance', 'Dark', 'Arrival').
        scene_description: Optional directions for scene action, mood, camera movement, or visual tone (e.g. 'slow tracking shot down a sterile white office corridor with flickering fluorescent lights').
        tool_context: Execution context for saving the artifact in the session.

    Returns:
        The public HTTPS URL of the uploaded video (https://storage.googleapis.com/nextbinge-media/videos/<filename>).
    """
    clean_title = title.strip()
    if not clean_title:
        return "Please provide a title to generate video for."

    scene_text = scene_description.strip() if scene_description and scene_description.strip() else "atmospheric cinematic scenery and iconic setting"
    full_prompt = (
        f"A short cinematic visual teaser trailer video for '{clean_title}'. "
        f"Atmosphere and visual details: {scene_text}. "
        "High visual quality, smooth motion, elegant cinematography, safe for all audiences, architectural and environmental beauty, no violence, no gore."
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=full_prompt,
            response_format={"type": "video"},
        )

        output_video = getattr(interaction, "output_video", None)
        if not output_video or not getattr(output_video, "data", None):
            return f"Failed to generate video for '{clean_title}': model returned no video content."

        raw_data = output_video.data
        if isinstance(raw_data, str):
            video_bytes = base64.b64decode(raw_data)
        else:
            video_bytes = bytes(raw_data)

        mime_type = getattr(output_video, "mime_type", None) or "video/mp4"
        ext = "mp4"

        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_title.lower()).strip("_") or "teaser"
        filename = f"{safe_slug}_teaser.{ext}"

        # 1. Save artifact to tool_context so it appears in Playground's Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                await tool_context.save_artifact(filename=filename, artifact=artifact_part)
                logger.info("Saved video artifact '%s' to tool_context", filename)
            except Exception as e:
                logger.warning("Could not save video artifact in tool_context: %s", e)

        # 2. Upload video bytes directly to public Cloud Storage bucket
        from google.cloud import storage

        bucket_name = "nextbinge-media"
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        object_name = f"videos/{filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        logger.info("Uploaded generated video for '%s' to %s", clean_title, public_url)
        return public_url

    except Exception as e:
        logger.error("Error generating video for '%s': %s", clean_title, e)
        return f"Video generation failed for '{clean_title}': {e}"




