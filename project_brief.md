# My agent: NextUp
One-liner: A conversational agent that helps viewers discover what to watch with a catalog of movies and TV series tailored to their available time slots and evolving taste preferences.

Tool coverage:
- Memory: User taste profile (genres, tone, favorite directors/actors), available viewing time slots, and watch history (evolving recommendations as items are marked "watched")
- Tools: Search movies and TV series (filtering by genre, duration, format), mark titles as watched, and record viewer feedback/ratings
- Catalog/UI: Rich media cards rendering title, poster/thumbnail, genre tags, duration/episode count, brief synopsis, and recommendation rationale
- Image gen: Cinematic moodboard images capturing the visual aesthetic, lighting, and vibe of the suggested watch
- Sandbox: Duration calculations to verify whether a movie or episode bundle fits comfortably into the user's available time slot

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): A2UI (media cards), Image gen (vibe moodboards), Code sandbox (time-slot fit calculator)
First eval question: "I have 45 minutes to unwind tonight and love mind-bending sci-fi thrillers, but I've already seen Severance. What should I watch?"
Second eval question: "I have a long weekend coming, help me pick something to binge watch that I can finish in 3 day."
