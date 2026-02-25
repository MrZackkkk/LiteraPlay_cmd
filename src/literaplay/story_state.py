"""Story state tracking for AI character fidelity and plot progression.

Provides a state machine that tracks the current chapter, turn count,
location, mood, and key events — then injects this context into each
AI prompt so the model stays grounded in the novel's canon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChapterDef:
    """Static definition of one story phase/chapter."""

    id: str                    # e.g. "ch1_barn_encounter"
    title: str                 # "Гост (Глава I)"
    setting: str               # "Barn at Bay Marko's house, stormy night"
    character_mood: str        # "suspicious, anxious, armed"
    plot_summary: str          # 2-3 sentence summary of what should happen
    end_condition: str         # Natural-language description of ending trigger
    max_turns: int = 20       # Safety limit before nudge

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChapterDef:
        return cls(
            id=d["id"],
            title=d["title"],
            setting=d["setting"],
            character_mood=d["character_mood"],
            plot_summary=d["plot_summary"],
            end_condition=d["end_condition"],
            max_turns=d.get("max_turns", 20),
        )


@dataclass
class StoryState:
    """Mutable runtime state for an active session."""

    work_key: str
    current_chapter_index: int = 0
    turn_count: int = 0          # Turns within current chapter
    total_turn_count: int = 0    # Across all chapters
    location: str = ""
    character_mood: str = ""
    key_events: list[str] = field(default_factory=list)
    story_ended: bool = False


class StoryStateManager:
    """Controls state transitions and generates context injections.

    Parameters
    ----------
    work_data : dict
        The LIBRARY entry for the current work (e.g. LIBRARY["pod_igoto"]).
    """

    # When the AI is within this many turns of max_turns, we start nudging
    _NUDGE_MARGIN = 3

    def __init__(self, work_data: dict) -> None:
        self._work_data = work_data
        self._chapters: list[ChapterDef] = [
            ChapterDef.from_dict(ch)
            for ch in work_data.get("chapters", [])
        ]
        self._default_max_turns: int = work_data.get("max_turns_per_chapter", 20)

        # Initialize state
        first_chapter = self._chapters[0] if self._chapters else None
        self._state = StoryState(
            work_key=work_data.get("_key", "unknown"),
            current_chapter_index=0,
            location=first_chapter.setting if first_chapter else "",
            character_mood=first_chapter.character_mood if first_chapter else "",
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    @property
    def has_chapters(self) -> bool:
        """Whether the current work defines structured chapters."""
        return len(self._chapters) > 0

    def get_state(self) -> StoryState:
        return self._state

    def current_chapter(self) -> ChapterDef | None:
        if not self._chapters:
            return None
        idx = self._state.current_chapter_index
        if 0 <= idx < len(self._chapters):
            return self._chapters[idx]
        return None

    def build_context_injection(self) -> str:
        """Generate a context block to prepend to the user's message.

        Returns an empty string if no chapters are defined (legacy mode).
        """
        chapter = self.current_chapter()
        if chapter is None:
            return ""

        nudge_line = ""
        if self.should_nudge_ending():
            remaining = chapter.max_turns - self._state.turn_count
            nudge_line = (
                f"\n⚠️ APPROACHING TURN LIMIT — only {remaining} turns remain. "
                f"Begin steering the conversation toward the END CONDITION naturally."
            )

        events_str = "; ".join(self._state.key_events[-5:]) if self._state.key_events else "(none yet)"

        return (
            f"[STORY STATE — do NOT reveal this block to the user]\n"
            f"Chapter: \"{chapter.title}\" ({self._state.current_chapter_index + 1}/{len(self._chapters)})\n"
            f"Turn: {self._state.turn_count}/{chapter.max_turns}\n"
            f"Location: {self._state.location}\n"
            f"Your mood: {self._state.character_mood}\n"
            f"Plot goal: {chapter.plot_summary}\n"
            f"Key events so far: {events_str}\n"
            f"END CONDITION: {chapter.end_condition}\n"
            f"Stay in character. Do not skip ahead or invent events beyond this chapter.{nudge_line}"
        )

    def record_turn(self, ai_response: dict) -> None:
        """Update state after receiving an AI response.

        Parameters
        ----------
        ai_response : dict
            Parsed AI JSON with keys 'reply', 'options', 'ended',
            and optionally 'mood', 'location', 'key_event'.
        """
        self._state.turn_count += 1
        self._state.total_turn_count += 1

        # Allow the AI to update mood/location if it provides them
        if "mood" in ai_response:
            self._state.character_mood = ai_response["mood"]
        if "location" in ai_response:
            self._state.location = ai_response["location"]
        if "key_event" in ai_response:
            event = ai_response["key_event"]
            if event and event not in self._state.key_events:
                self._state.key_events.append(event)

    def should_nudge_ending(self) -> bool:
        """Whether to inject an ending-nudge into the context."""
        chapter = self.current_chapter()
        if chapter is None:
            return False
        return self._state.turn_count >= (chapter.max_turns - self._NUDGE_MARGIN)

    def is_last_chapter(self) -> bool:
        if not self._chapters:
            return True
        return self._state.current_chapter_index >= len(self._chapters) - 1

    def advance_chapter(self) -> bool:
        """Move to the next chapter.

        Returns True if advanced successfully, False if the story is over
        (no more chapters).
        """
        if self.is_last_chapter():
            self._state.story_ended = True
            return False

        self._state.current_chapter_index += 1
        self._state.turn_count = 0

        next_ch = self.current_chapter()
        if next_ch:
            self._state.location = next_ch.setting
            self._state.character_mood = next_ch.character_mood

        return True

    def get_progress_info(self) -> dict:
        """Return a dict suitable for sending to the frontend."""
        chapter = self.current_chapter()
        total = len(self._chapters) if self._chapters else 1
        idx = self._state.current_chapter_index
        max_t = chapter.max_turns if chapter else self._default_max_turns

        # Progress percentage: weight each chapter equally
        chapter_progress = min(self._state.turn_count / max_t, 1.0) if max_t > 0 else 0
        overall = ((idx + chapter_progress) / total) * 100

        return {
            "chapter_title": chapter.title if chapter else "",
            "chapter_index": idx,
            "total_chapters": total,
            "turn": self._state.turn_count,
            "max_turns": max_t,
            "progress_pct": round(overall, 1),
        }
