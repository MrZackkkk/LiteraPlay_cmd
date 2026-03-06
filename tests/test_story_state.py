import unittest

from literaplay.story_state import ChapterDef, StoryState, StoryStateManager

_SAMPLE_CHAPTERS = [
    {
        "id": "ch1_test",
        "title": "Chapter One",
        "setting": "A dark room",
        "character_mood": "nervous",
        "plot_summary": "The hero enters the room.",
        "end_condition": "The hero leaves the room.",
        "max_turns": 5,
    },
    {
        "id": "ch2_test",
        "title": "Chapter Two",
        "setting": "A bright garden",
        "character_mood": "calm",
        "plot_summary": "The hero walks in the garden.",
        "end_condition": "The hero sits on the bench.",
        "max_turns": 10,
    },
]

_SAMPLE_WORK = {
    "_key": "test_work",
    "title": "Test Work",
    "character": "Hero",
    "prompt": "You are Hero.",
    "chapters": _SAMPLE_CHAPTERS,
    "max_turns_per_chapter": 5,
}


class TestChapterDef(unittest.TestCase):
    def test_from_dict(self):
        ch = ChapterDef.from_dict(_SAMPLE_CHAPTERS[0])
        self.assertEqual(ch.id, "ch1_test")
        self.assertEqual(ch.max_turns, 5)

    def test_from_dict_default_max_turns(self):
        d = dict(_SAMPLE_CHAPTERS[0])
        del d["max_turns"]
        ch = ChapterDef.from_dict(d)
        self.assertEqual(ch.max_turns, 20)


class TestStoryStateManager(unittest.TestCase):
    def setUp(self):
        self.manager = StoryStateManager(_SAMPLE_WORK)

    def test_initial_state(self):
        state = self.manager.get_state()
        self.assertEqual(state.current_chapter_index, 0)
        self.assertEqual(state.turn_count, 0)
        self.assertEqual(state.location, "A dark room")
        self.assertEqual(state.character_mood, "nervous")
        self.assertFalse(state.story_ended)

    def test_has_chapters(self):
        self.assertTrue(self.manager.has_chapters)

    def test_has_chapters_false(self):
        mgr = StoryStateManager({"_key": "x", "title": "x"})
        self.assertFalse(mgr.has_chapters)

    def test_current_chapter(self):
        ch = self.manager.current_chapter()
        self.assertIsNotNone(ch)
        self.assertEqual(ch.id, "ch1_test")

    def test_build_context_injection_not_empty(self):
        ctx = self.manager.build_context_injection()
        self.assertIn("Chapter One", ctx)
        self.assertIn("1/2", ctx)
        self.assertIn("Turn: 0/5", ctx)

    def test_build_context_injection_empty_without_chapters(self):
        mgr = StoryStateManager({"_key": "x"})
        self.assertEqual(mgr.build_context_injection(), "")

    def test_record_turn_increments(self):
        self.manager.record_turn({"reply": "hello", "options": []})
        state = self.manager.get_state()
        self.assertEqual(state.turn_count, 1)
        self.assertEqual(state.total_turn_count, 1)

    def test_record_turn_updates_mood_location_event(self):
        self.manager.record_turn(
            {
                "reply": "hi",
                "options": [],
                "mood": "happy",
                "location": "outside",
                "key_event": "met a friend",
            }
        )
        state = self.manager.get_state()
        self.assertEqual(state.character_mood, "happy")
        self.assertEqual(state.location, "outside")
        self.assertIn("met a friend", state.key_events)

    def test_should_nudge_ending(self):
        # max_turns = 5, nudge margin = 3 → nudge at turn >= 2
        self.manager.record_turn({"reply": "a"})
        self.manager.record_turn({"reply": "b"})
        self.assertTrue(self.manager.should_nudge_ending())

    def test_should_not_nudge_early(self):
        self.manager.record_turn({"reply": "a"})
        self.assertFalse(self.manager.should_nudge_ending())

    def test_nudge_appears_in_context(self):
        for _ in range(3):
            self.manager.record_turn({"reply": "a"})
        ctx = self.manager.build_context_injection()
        self.assertIn("APPROACHING TURN LIMIT", ctx)

    def test_advance_chapter_success(self):
        result = self.manager.advance_chapter()
        self.assertTrue(result)
        state = self.manager.get_state()
        self.assertEqual(state.current_chapter_index, 1)
        self.assertEqual(state.turn_count, 0)
        self.assertEqual(state.location, "A bright garden")

    def test_advance_chapter_last(self):
        self.manager.advance_chapter()
        # Now at last chapter
        result = self.manager.advance_chapter()
        self.assertFalse(result)
        self.assertTrue(self.manager.get_state().story_ended)

    def test_is_last_chapter(self):
        self.assertFalse(self.manager.is_last_chapter())
        self.manager.advance_chapter()
        self.assertTrue(self.manager.is_last_chapter())

    def test_get_progress_info(self):
        info = self.manager.get_progress_info()
        self.assertEqual(info["chapter_title"], "Chapter One")
        self.assertEqual(info["chapter_index"], 0)
        self.assertEqual(info["total_chapters"], 2)
        self.assertEqual(info["turn"], 0)
        self.assertEqual(info["max_turns"], 5)
        self.assertAlmostEqual(info["progress_pct"], 0.0, places=1)

    def test_progress_increases_with_turns(self):
        for _ in range(5):
            self.manager.record_turn({"reply": "a"})
        info = self.manager.get_progress_info()
        self.assertGreater(info["progress_pct"], 0)


class TestNewStateFields(unittest.TestCase):
    def setUp(self):
        self.manager = StoryStateManager(_SAMPLE_WORK)

    # --- default values ---

    def test_new_fields_default_values(self):
        state = self.manager.get_state()
        self.assertEqual(state.trust_level, 0)
        self.assertEqual(state.tension, "")
        self.assertEqual(state.characters_present, [])
        self.assertEqual(state.active_props, [])
        self.assertEqual(state.recent_turns, [])

    # --- trust_level ---

    def test_record_turn_sets_trust_level(self):
        self.manager.record_turn({"reply": "hi", "trust_level": 2})
        self.assertEqual(self.manager.get_state().trust_level, 2)

    def test_record_turn_clamps_trust_level_high(self):
        self.manager.record_turn({"reply": "hi", "trust_level": 99})
        self.assertEqual(self.manager.get_state().trust_level, 3)

    def test_record_turn_clamps_trust_level_low(self):
        self.manager.record_turn({"reply": "hi", "trust_level": -99})
        self.assertEqual(self.manager.get_state().trust_level, -3)

    def test_record_turn_ignores_non_int_trust_level(self):
        self.manager.record_turn({"reply": "hi", "trust_level": "high"})
        self.assertEqual(self.manager.get_state().trust_level, 0)

    # --- tension ---

    def test_record_turn_sets_tension(self):
        self.manager.record_turn({"reply": "hi", "tension": "armed standoff"})
        self.assertEqual(self.manager.get_state().tension, "armed standoff")

    def test_record_turn_overwrites_tension(self):
        self.manager.record_turn({"reply": "a", "tension": "first"})
        self.manager.record_turn({"reply": "b", "tension": "second"})
        self.assertEqual(self.manager.get_state().tension, "second")

    # --- characters_present ---

    def test_record_turn_sets_characters_present(self):
        self.manager.record_turn({"reply": "hi", "characters_present": ["Марко", "Иван"]})
        self.assertEqual(self.manager.get_state().characters_present, ["Марко", "Иван"])

    def test_record_turn_overwrites_characters_present(self):
        self.manager.record_turn({"reply": "a", "characters_present": ["A", "B"]})
        self.manager.record_turn({"reply": "b", "characters_present": ["C"]})
        self.assertEqual(self.manager.get_state().characters_present, ["C"])

    # --- active_props ---

    def test_record_turn_accumulates_active_props(self):
        self.manager.record_turn({"reply": "a", "active_props": ["пищов"]})
        self.manager.record_turn({"reply": "b", "active_props": ["фенер"]})
        self.assertIn("пищов", self.manager.get_state().active_props)
        self.assertIn("фенер", self.manager.get_state().active_props)

    def test_record_turn_deduplicates_active_props(self):
        self.manager.record_turn({"reply": "a", "active_props": ["пищов"]})
        self.manager.record_turn({"reply": "b", "active_props": ["пищов", "фенер"]})
        self.assertEqual(self.manager.get_state().active_props.count("пищов"), 1)

    def test_record_turn_caps_active_props_at_10(self):
        for i in range(12):
            self.manager.record_turn({"reply": "x", "active_props": [f"prop_{i}"]})
        self.assertLessEqual(len(self.manager.get_state().active_props), 10)

    # --- recent_turns ---

    def test_record_turn_adds_to_recent_turns(self):
        self.manager.record_turn({"reply": "hello world"})
        self.assertEqual(len(self.manager.get_state().recent_turns), 1)

    def test_record_turn_recent_turns_max_3(self):
        for i in range(5):
            self.manager.record_turn({"reply": f"message {i}"})
        self.assertEqual(len(self.manager.get_state().recent_turns), 3)

    def test_record_turn_recent_turns_fifo(self):
        for i in range(4):
            self.manager.record_turn({"reply": f"msg{i}"})
        # Only the last 3 should remain
        state = self.manager.get_state()
        self.assertNotIn("msg0", state.recent_turns[0])
        self.assertEqual(len(state.recent_turns), 3)

    def test_record_turn_key_event_goes_to_recent_turns(self):
        self.manager.record_turn({"reply": "some reply", "key_event": "hero revealed"})
        self.assertIn("hero revealed", self.manager.get_state().recent_turns)

    def test_record_turn_list_reply_uses_first_text_for_recent_turns(self):
        reply = [{"character": "Марко", "text": "Кой е там?"}]
        self.manager.record_turn({"reply": reply})
        self.assertIn("Кой е там?", self.manager.get_state().recent_turns[0])

    # --- advance_chapter resets / carries ---

    def test_advance_chapter_resets_characters_present(self):
        self.manager.record_turn({"reply": "a", "characters_present": ["A", "B"]})
        self.manager.advance_chapter()
        self.assertEqual(self.manager.get_state().characters_present, [])

    def test_advance_chapter_resets_recent_turns(self):
        self.manager.record_turn({"reply": "some text"})
        self.manager.advance_chapter()
        self.assertEqual(self.manager.get_state().recent_turns, [])

    def test_advance_chapter_preserves_trust_level(self):
        self.manager.record_turn({"reply": "a", "trust_level": 2})
        self.manager.advance_chapter()
        self.assertEqual(self.manager.get_state().trust_level, 2)

    def test_advance_chapter_preserves_active_props(self):
        self.manager.record_turn({"reply": "a", "active_props": ["пищов"]})
        self.manager.advance_chapter()
        self.assertIn("пищов", self.manager.get_state().active_props)

    # --- build_context_injection labels ---

    def test_context_contains_trust_label(self):
        self.manager.record_turn({"reply": "a", "trust_level": -3})
        ctx = self.manager.build_context_injection()
        self.assertIn("Trust toward", ctx)
        self.assertIn("hostile", ctx)

    def test_context_trust_neutral(self):
        ctx = self.manager.build_context_injection()
        self.assertIn("neutral", ctx)

    def test_context_trust_devoted(self):
        self.manager.record_turn({"reply": "a", "trust_level": 3})
        ctx = self.manager.build_context_injection()
        self.assertIn("devoted", ctx)

    def test_context_contains_tension(self):
        self.manager.record_turn({"reply": "a", "tension": "armed standoff"})
        ctx = self.manager.build_context_injection()
        self.assertIn("Tension:", ctx)
        self.assertIn("armed standoff", ctx)

    def test_context_contains_characters_present(self):
        self.manager.record_turn({"reply": "a", "characters_present": ["Марко"]})
        ctx = self.manager.build_context_injection()
        self.assertIn("Characters present:", ctx)
        self.assertIn("Марко", ctx)

    def test_context_contains_active_props(self):
        self.manager.record_turn({"reply": "a", "active_props": ["пищов"]})
        ctx = self.manager.build_context_injection()
        self.assertIn("Active props:", ctx)
        self.assertIn("пищов", ctx)

    def test_context_contains_recent_turns(self):
        self.manager.record_turn({"reply": "some text here"})
        ctx = self.manager.build_context_injection()
        self.assertIn("Recent turns:", ctx)
        self.assertIn("some text here", ctx)

    def test_context_contains_knowledge_boundaries(self):
        ctx = self.manager.build_context_injection()
        self.assertIn("KNOWLEDGE BOUNDARIES:", ctx)


# Re-export StoryState so the import at the top is used (avoids F401 from ruff)
_STATE_CLASS = StoryState


if __name__ == "__main__":
    unittest.main()
