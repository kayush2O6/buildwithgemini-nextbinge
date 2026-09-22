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

import pytest
from app.tools import (
    add_title_to_catalog,
    calculate_time_fit,
    fetch_live_title_details,
    generate_title_poster,
    generate_title_video,
    mark_as_watched,
    search_entertainment_guide,
    search_titles,
    _WATCHED_TITLES,
)


@pytest.fixture(autouse=True)
def clean_watched_titles():
    _WATCHED_TITLES.clear()
    yield
    _WATCHED_TITLES.clear()


def test_search_titles_genre():
    res = search_titles(genre="sci-fi")
    assert res["status"] == "success"
    assert res["count"] > 0
    assert all("sci-fi" in [g.lower() for g in item["genres"]] for item in res["results"])


def test_search_titles_duration():
    res = search_titles(max_duration_mins=45)
    assert res["status"] == "success"
    for item in res["results"]:
        duration = (
            item["episode_duration_mins"]
            if item.get("format") in ("series", "miniseries")
            else item.get("duration_mins", item.get("total_runtime_mins", 0))
        )
        assert duration <= 45


def test_search_titles_query():
    res = search_titles(query="alien")
    assert res["status"] == "success"
    assert any(item["title"] == "Arrival" for item in res["results"])


def test_mark_as_watched_and_exclude():
    res = mark_as_watched("Severance", rating=9.5, feedback="Incredible mystery")
    assert res["status"] == "success"
    assert res["total_watched_count"] == 1

    # Now searching with exclude_watched=True should exclude Severance
    search_res = search_titles(genre="sci-fi", exclude_watched=True)
    assert not any(item["title"] == "Severance" for item in search_res["results"])


def test_add_title_to_catalog():
    res = add_title_to_catalog(
        title="Dune: Part Two",
        format="movie",
        genres=["Sci-Fi", "Adventure", "Drama"],
        synopsis="Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.",
        duration_mins=166,
        mood_tags=["epic", "cinematic", "visual"],
        creator="Denis Villeneuve",
        year=2024,
    )
    assert res["status"] == "success"
    assert res["title"]["title"] == "Dune: Part Two"

    # Verify searchable in catalog
    search_res = search_titles(query="Dune")
    assert search_res["status"] == "success"
    assert any(item["title"] == "Dune: Part Two" for item in search_res["results"])


def test_calculate_time_fit_success():
    res = calculate_time_fit(available_minutes=150, title="Arrival")
    assert res["status"] == "success"
    assert res["fits"] is True
    assert res["difference_minutes"] == 34  # 150 - 116


def test_calculate_time_fit_exceeded():
    res = calculate_time_fit(available_minutes=30, title="Chernobyl")
    assert res["status"] == "success"
    assert res["fits"] is False
    assert res["difference_minutes"] < 0


def test_fetch_live_title_details():
    res = fetch_live_title_details("Fallout")
    assert res["status"] == "success"
    assert "Fallout" in res["title"]
    assert "Action" in res["genres"] or "Science-Fiction" in res["genres"] or "Drama" in res["genres"]
    assert res["poster_url"] is not None
    assert res["poster_url"].startswith("http")


def test_fetch_live_title_details_not_found():
    res = fetch_live_title_details("xyzabc123nonexistentnevermade9999")
    assert res["status"] == "not_found"


def test_search_entertainment_guide_empty():
    res = search_entertainment_guide("")
    assert "Please provide a search query" in res


def test_search_entertainment_guide_success():
    res = search_entertainment_guide("Dark 33-year cycle time travel")
    assert isinstance(res, str)
    assert len(res) > 20
    assert "Dark" in res or "Cycle" in res or "Winden" in res or "loop" in res.lower()


@pytest.mark.asyncio
async def test_generate_title_poster_empty():
    res = await generate_title_poster("")
    assert "Please provide a title" in res


@pytest.mark.asyncio
async def test_generate_title_poster_mocked(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from google.genai import types

    fake_bytes = b"fake-poster-image-data-bytes"
    mock_part = MagicMock()
    mock_part.inline_data.data = fake_bytes
    mock_part.inline_data.mime_type = "image/jpeg"

    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]

    mock_models = MagicMock()
    mock_models.generate_content.return_value = mock_response

    mock_client = MagicMock()
    mock_client.models = mock_models

    monkeypatch.setattr("google.genai.Client", lambda **kwargs: mock_client)

    # Mock storage client
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    monkeypatch.setattr("google.cloud.storage.Client", lambda **kwargs: mock_storage_client)

    # Mock ToolContext
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock(return_value=1)

    url = await generate_title_poster(
        title="Severance",
        visual_description="eerie luminescent blue office labyrinth",
        tool_context=mock_tool_context,
    )

    assert url == "https://storage.googleapis.com/nextbinge-media/posters/severance_poster.jpg"
    mock_blob.upload_from_string.assert_called_once_with(fake_bytes, content_type="image/jpeg")
    mock_tool_context.save_artifact.assert_called_once()
    assert mock_tool_context.save_artifact.call_args[1]["filename"] == "severance_poster.jpg"


@pytest.mark.asyncio
async def test_generate_title_video_empty():
    res = await generate_title_video("")
    assert "Please provide a title" in res


@pytest.mark.asyncio
async def test_generate_title_video_mocked(monkeypatch):
    import base64
    from unittest.mock import AsyncMock, MagicMock

    fake_video_bytes = b"fake-video-mp4-data-bytes"
    mock_output_video = MagicMock()
    mock_output_video.data = base64.b64encode(fake_video_bytes).decode("utf-8")
    mock_output_video.mime_type = "video/mp4"

    mock_interaction = MagicMock()
    mock_interaction.output_video = mock_output_video

    mock_interactions = MagicMock()
    mock_interactions.create.return_value = mock_interaction

    mock_client = MagicMock()
    mock_client.interactions = mock_interactions

    monkeypatch.setattr("google.genai.Client", lambda **kwargs: mock_client)

    # Mock storage client
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    monkeypatch.setattr("google.cloud.storage.Client", lambda **kwargs: mock_storage_client)

    # Mock ToolContext
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock(return_value=1)

    url = await generate_title_video(
        title="Severance",
        scene_description="slow tracking shot down a sterile white office corridor",
        tool_context=mock_tool_context,
    )

    assert url == "https://storage.googleapis.com/nextbinge-media/videos/severance_teaser.mp4"
    mock_interactions.create.assert_called_once()
    assert mock_interactions.create.call_args[1]["model"] == "gemini-omni-flash-preview"
    assert mock_interactions.create.call_args[1]["response_format"] == {"type": "video"}
    mock_blob.upload_from_string.assert_called_once_with(fake_video_bytes, content_type="video/mp4")
    mock_tool_context.save_artifact.assert_called_once()
    assert mock_tool_context.save_artifact.call_args[1]["filename"] == "severance_teaser.mp4"




