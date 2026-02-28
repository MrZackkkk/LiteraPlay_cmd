import unittest

from literaplay.story_state import ChapterDef, StoryStateManager

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


class TestValidateStoryResponse(unittest.TestCase):
    def test_empty_reply_gets_fallback(self):
        from literaplay.response_parser import validate_story_response

        result = validate_story_response({"reply": "", "options": [], "ended": False})
        self.assertEqual(result["reply"], "...")

    def test_ended_on_non_last_chapter_becomes_chapter_ended(self):
        from literaplay.response_parser import validate_story_response

        result = validate_story_response(
            {"reply": "bye", "options": [], "ended": True},
            is_last_chapter=False,
        )
        self.assertFalse(result["ended"])
        self.assertTrue(result["_chapter_ended"])

    def test_ended_on_last_chapter_stays_ended(self):
        from literaplay.response_parser import validate_story_response

        result = validate_story_response(
            {"reply": "final", "options": [], "ended": True},
            is_last_chapter=True,
        )
        self.assertTrue(result["ended"])
        self.assertFalse(result["_chapter_ended"])

    def test_missing_options_get_fallback(self):
        from literaplay.response_parser import validate_story_response

        result = validate_story_response(
            {"reply": "hello", "options": None, "ended": False},
            is_last_chapter=True,
        )
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)

    def test_long_reply_truncated(self):
        from literaplay.response_parser import validate_story_response

        long_text = "word " * 500
        result = validate_story_response(
            {"reply": long_text, "options": ["ok"], "ended": False},
        )
        self.assertLessEqual(len(result["reply"]), 1010)  # ~1000 + "..."


if __name__ == "__main__":
    unittest.main()
